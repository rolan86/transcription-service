"""
WebSocket endpoint for real-time streaming transcription.
"""

import json
import base64
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.streaming_transcriber import StreamingTranscriber

router = APIRouter()


async def finalize_with_keepalive(websocket: WebSocket, transcriber: StreamingTranscriber):
    """
    Run finalize() while sending periodic keep-alive messages.
    This prevents the WebSocket from timing out during long transcription.
    """
    # Create a task for finalization
    finalize_task = asyncio.create_task(transcriber.finalize())

    # Send keep-alive while waiting
    while not finalize_task.done():
        try:
            await asyncio.wait_for(asyncio.shield(finalize_task), timeout=1.0)
        except asyncio.TimeoutError:
            # Send keep-alive ping
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                pass  # Connection might be closing

    return finalize_task.result()


@router.websocket("/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription.

    Protocol:
    1. Client connects
    2. Client sends 'start' message with config: {"type": "start", "model": "base", "language": null}
    3. Server responds with 'ready' message
    4. Client sends 'audio' messages: {"type": "audio", "data": "<base64-encoded-pcm>"}
    5. Server sends 'transcript' messages as transcription becomes available
    6. Client sends 'stop' message to finalize
    7. Server sends 'complete' message with final transcript
    """
    await websocket.accept()

    transcriber: Optional[StreamingTranscriber] = None

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON message",
                })
                continue

            msg_type = message.get("type")

            if msg_type == "start":
                # Initialize transcriber with config
                model = message.get("model", "base")
                language = message.get("language")
                sample_rate = message.get("sample_rate", 16000)
                chunk_duration = message.get("chunk_duration", 5.0)

                transcriber = StreamingTranscriber(
                    model_size=model,
                    language=language,
                    sample_rate=sample_rate,
                    chunk_duration=chunk_duration,
                )

                await websocket.send_json({
                    "type": "ready",
                    "message": f"Transcriber initialized with model '{model}'",
                })

            elif msg_type == "audio" and transcriber:
                # Decode base64 audio data
                audio_base64 = message.get("data", "")
                try:
                    audio_bytes = base64.b64decode(audio_base64)
                except Exception:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid base64 audio data",
                    })
                    continue

                # Process audio chunk
                result = await transcriber.process_audio_chunk(audio_bytes)

                if result and result.get("text"):
                    await websocket.send_json({
                        "type": "transcript",
                        "text": result["text"],
                        "is_final": result.get("is_final", False),
                        "timestamp": result.get("timestamp", 0),
                        "confidence": result.get("confidence", 0),
                    })

            elif msg_type == "stop":
                # Finalize transcription
                if transcriber:
                    # Send immediate acknowledgment
                    await websocket.send_json({
                        "type": "status",
                        "status": "processing",
                        "message": "Finalizing transcription, please wait...",
                    })

                    # Process final transcription with keep-alive pings
                    final_result = await finalize_with_keepalive(websocket, transcriber)

                    await websocket.send_json({
                        "type": "complete",
                        "text": final_result.get("text", ""),
                        "is_final": True,
                        "segments": final_result.get("segments", []),
                    })

                    # Cleanup
                    transcriber.cleanup()
                    transcriber = None
                else:
                    # No transcriber, send empty result
                    await websocket.send_json({
                        "type": "complete",
                        "text": "",
                        "is_final": True,
                        "segments": [],
                    })

                break

            elif msg_type == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
            })
        except Exception:
            pass
    finally:
        if transcriber:
            transcriber.cleanup()
