"""
WebSocket endpoint for real-time streaming transcription.
Supports long-duration recordings with server-side chunk persistence.
"""

import json
import base64
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.streaming_transcriber import StreamingTranscriber
from ..services.recording_session import SessionManager, RecordingSession
from ..services.history_manager import HistoryManager

router = APIRouter()

# Session manager for long recordings
session_manager = SessionManager()


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
    3. Server responds with 'ready' message (includes session_id for long recordings)
    4. Client sends 'audio' messages: {"type": "audio", "data": "<base64-encoded-pcm>"}
    5. Server sends 'transcript' messages as transcription becomes available
    6. Client can send 'flush' messages to persist audio on server: {"type": "flush", "data": "<base64>"}
    7. Client sends 'stop' message to finalize
    8. Server sends 'complete' message with final transcript
    """
    await websocket.accept()

    transcriber: Optional[StreamingTranscriber] = None
    session: Optional[RecordingSession] = None
    current_model: str = "base"
    current_language: Optional[str] = None

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
                current_model = message.get("model", "base")
                current_language = message.get("language")
                sample_rate = message.get("sample_rate", 16000)
                chunk_duration = message.get("chunk_duration", 5.0)
                enable_persistence = message.get("enable_persistence", True)

                transcriber = StreamingTranscriber(
                    model_size=current_model,
                    language=current_language,
                    sample_rate=sample_rate,
                    chunk_duration=chunk_duration,
                )

                # Create session for long recording support
                if enable_persistence:
                    session = session_manager.create_session(sample_rate=sample_rate)
                    session_id = session.session_id
                else:
                    session_id = None

                await websocket.send_json({
                    "type": "ready",
                    "message": f"Transcriber initialized with model '{current_model}'",
                    "session_id": session_id,
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

            elif msg_type == "flush" and session:
                # Persist audio chunk to server-side storage
                audio_base64 = message.get("data", "")
                try:
                    audio_bytes = base64.b64decode(audio_base64)
                    chunk = session.add_chunk(audio_bytes)

                    await websocket.send_json({
                        "type": "flush_ack",
                        "success": True,
                        "chunk_duration": chunk.duration,
                        "total_duration": session.total_duration,
                        "chunk_count": len(session.chunks),
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "flush_ack",
                        "success": False,
                        "error": str(e),
                    })

            elif msg_type == "session_stats" and session:
                # Return session statistics
                stats = session.get_stats()
                await websocket.send_json({
                    "type": "session_stats",
                    **stats,
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

                    # If we have persisted chunks, add them to transcriber for final processing
                    if session and len(session.chunks) > 0:
                        # Save session audio to temp file for complete re-transcription
                        await websocket.send_json({
                            "type": "status",
                            "status": "processing",
                            "message": f"Processing {session.total_duration:.0f}s of recorded audio...",
                        })

                    # Process final transcription with keep-alive pings
                    final_result = await finalize_with_keepalive(websocket, transcriber)

                    await websocket.send_json({
                        "type": "complete",
                        "text": final_result.get("text", ""),
                        "is_final": True,
                        "segments": final_result.get("segments", []),
                        "session_duration": session.total_duration if session else 0,
                    })

                    # Save to history
                    try:
                        final_text = final_result.get("text", "")
                        if final_text.strip():
                            history_manager = HistoryManager()
                            # Create result dict matching save_transcription format
                            result_for_history = {
                                "text": final_text,
                                "language": current_language,
                                "duration": session.total_duration if session else 0,
                                "confidence": 0.9,
                                "segments": final_result.get("segments", []),
                                "metadata": {
                                    "transcription": {
                                        "model": current_model,
                                    }
                                }
                            }
                            history_manager.save_transcription(
                                result=result_for_history,
                                filename=f"Recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            )
                    except Exception as hist_err:
                        print(f"Warning: Failed to save recording to history: {hist_err}")

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
        if session:
            session_manager.remove_session(session.session_id)
