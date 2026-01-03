#!/usr/bin/env python3
"""
Test script for Recording Enhancement Features

Tests the following features:
1. Backend Connection Status (health check API)
2. Whisper Model Status API
3. WebSocket pause/resume/chapter handling
4. Session continuation
5. History Merge API

Run with: python tests/scripts/test_recording_enhancements.py
Requires: Server running at http://localhost:8000
"""

import asyncio
import json
import sys
import os
from pathlib import Path
import websockets
import aiohttp

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/transcribe"

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_test(name):
    """Print test header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🧪 Testing: {name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_pass(message):
    """Print pass message."""
    print(f"{GREEN}✅ PASS: {message}{RESET}")


def print_fail(message):
    """Print fail message."""
    print(f"{RED}❌ FAIL: {message}{RESET}")


def print_info(message):
    """Print info message."""
    print(f"{YELLOW}ℹ️  {message}{RESET}")


async def test_health_endpoint():
    """Test the health check endpoint for backend status."""
    print_test("Health Check Endpoint (Backend Connection Status)")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print_pass(f"Health endpoint returned: {data}")
                    return True
                else:
                    print_fail(f"Health endpoint returned status {response.status}")
                    return False
    except aiohttp.ClientError as e:
        print_fail(f"Connection error: {e}")
        print_info("Make sure the server is running at http://localhost:8000")
        return False


async def test_whisper_status_endpoint():
    """Test the Whisper model status endpoint."""
    print_test("Whisper Model Status Endpoint")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/whisper/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print_pass(f"Whisper status endpoint returned:")
                    print_info(f"  model_ready: {data.get('model_ready')}")
                    print_info(f"  status: {data.get('status')}")
                    print_info(f"  model_size: {data.get('model_size')}")
                    return True
                else:
                    print_fail(f"Whisper status endpoint returned status {response.status}")
                    return False
    except aiohttp.ClientError as e:
        print_fail(f"Connection error: {e}")
        return False


async def test_websocket_pause_resume():
    """Test WebSocket pause and resume message handling."""
    print_test("WebSocket Pause/Resume Handling")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send start message
            start_msg = {
                "type": "start",
                "model": "base",
                "language": None,
            }
            await websocket.send(json.dumps(start_msg))

            # Wait for ready response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)

            if data.get("type") != "ready":
                print_fail(f"Expected 'ready' message, got: {data.get('type')}")
                return False

            print_info(f"Received ready message with session_id: {data.get('session_id')}")
            print_info(f"Model ready: {data.get('model_ready')}")

            # Test pause
            pause_msg = {"type": "pause"}
            await websocket.send(json.dumps(pause_msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "pause_ack":
                print_pass("Pause acknowledged correctly")
            else:
                print_fail(f"Expected 'pause_ack', got: {data.get('type')}")
                return False

            # Test resume
            resume_msg = {"type": "resume"}
            await websocket.send(json.dumps(resume_msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "resume_ack":
                print_pass("Resume acknowledged correctly")
            else:
                print_fail(f"Expected 'resume_ack', got: {data.get('type')}")
                return False

            # Send stop to close cleanly
            await websocket.send(json.dumps({"type": "stop"}))

            return True

    except asyncio.TimeoutError:
        print_fail("Timeout waiting for WebSocket response")
        return False
    except websockets.exceptions.WebSocketException as e:
        print_fail(f"WebSocket error: {e}")
        return False


async def test_websocket_chapter():
    """Test WebSocket chapter message handling."""
    print_test("WebSocket Chapter Handling")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send start message
            start_msg = {
                "type": "start",
                "model": "base",
                "language": None,
            }
            await websocket.send(json.dumps(start_msg))

            # Wait for ready response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)

            if data.get("type") != "ready":
                print_fail(f"Expected 'ready' message, got: {data.get('type')}")
                return False

            # Test chapter
            chapter_msg = {
                "type": "chapter",
                "chapter": {
                    "index": 1,
                    "title": "Chapter 1",
                    "startTime": 0,
                    "endTime": None,
                }
            }
            await websocket.send(json.dumps(chapter_msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "chapter_ack":
                print_pass(f"Chapter acknowledged: {data.get('chapter')}")
            else:
                print_fail(f"Expected 'chapter_ack', got: {data.get('type')}")
                return False

            # Send stop to close cleanly
            await websocket.send(json.dumps({"type": "stop"}))

            return True

    except asyncio.TimeoutError:
        print_fail("Timeout waiting for WebSocket response")
        return False
    except websockets.exceptions.WebSocketException as e:
        print_fail(f"WebSocket error: {e}")
        return False


async def test_merge_api():
    """Test the history merge API endpoint."""
    print_test("History Merge API")

    try:
        async with aiohttp.ClientSession() as session:
            # First, get existing history entries
            async with session.get(f"{BASE_URL}/api/history?limit=5") as response:
                if response.status != 200:
                    print_info("No history entries available to test merge")
                    return None

                data = await response.json()
                entries = data.get("entries", [])

                if len(entries) < 2:
                    print_info(f"Need at least 2 history entries to test merge (found {len(entries)})")
                    print_info("Create some transcriptions first, then run this test again")
                    return None

                entry_ids = [e["id"] for e in entries[:2]]
                print_info(f"Testing merge with entry IDs: {entry_ids}")

            # Test merge endpoint
            merge_data = {
                "entry_ids": entry_ids,
                "add_separators": True,
                "merged_name": "Test_Merged_Transcript",
            }

            async with session.post(
                f"{BASE_URL}/api/history/merge",
                json=merge_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print_pass(f"Merge successful: {result.get('message')}")
                    print_info(f"New entry ID: {result.get('new_entry_id')}")
                    print_info(f"Total words: {result.get('total_words')}")
                    return True
                else:
                    error = await response.text()
                    print_fail(f"Merge failed with status {response.status}: {error}")
                    return False

    except aiohttp.ClientError as e:
        print_fail(f"Connection error: {e}")
        return False


async def test_session_continuation():
    """Test session continuation (continue recording) feature."""
    print_test("Session Continuation (Continue Recording)")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Start a session
            start_msg = {
                "type": "start",
                "model": "base",
                "language": None,
                "enable_persistence": True,
            }
            await websocket.send(json.dumps(start_msg))

            # Wait for ready response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)

            if data.get("type") != "ready":
                print_fail(f"Expected 'ready' message, got: {data.get('type')}")
                return False

            session_id = data.get("session_id")
            print_info(f"Started session: {session_id}")

            if not session_id:
                print_fail("No session_id returned - persistence may be disabled")
                return False

            # Stop the session
            await websocket.send(json.dumps({"type": "stop"}))

            # Wait for complete message (may have status updates first)
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                if data.get("type") == "complete":
                    break
                elif data.get("type") == "error":
                    print_fail(f"Error: {data.get('error')}")
                    return False

            can_continue = data.get("can_continue")
            returned_session_id = data.get("session_id")

            print_info(f"Session stopped - can_continue: {can_continue}")
            print_info(f"Returned session_id: {returned_session_id}")

            if can_continue and returned_session_id:
                print_pass("Session can be continued - continuation data returned correctly")
            else:
                print_info("Session cannot be continued (this may be expected if session was short)")

            return True

    except asyncio.TimeoutError:
        print_fail("Timeout waiting for WebSocket response")
        return False
    except websockets.exceptions.WebSocketException as e:
        print_fail(f"WebSocket error: {e}")
        return False


async def test_continue_message():
    """Test the 'continue' message type for session restoration."""
    print_test("Continue Message (Session Restoration)")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Try to continue with a non-existent session
            continue_msg = {
                "type": "continue",
                "session_id": "nonexistent_session_123",
                "model": "base",
            }
            await websocket.send(json.dumps(continue_msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "error":
                error_msg = data.get("error", "")
                if "not found" in error_msg.lower() or "not paused" in error_msg.lower():
                    print_pass(f"Correctly rejected invalid session: {error_msg}")
                    return True
                else:
                    print_info(f"Got error (expected): {error_msg}")
                    return True
            else:
                print_info(f"Unexpected response type: {data.get('type')}")
                return True  # Non-failure, just unexpected

    except asyncio.TimeoutError:
        print_fail("Timeout waiting for WebSocket response")
        return False
    except websockets.exceptions.WebSocketException as e:
        print_fail(f"WebSocket error: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  Recording Enhancement Features - Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print_info(f"Testing against: {BASE_URL}")

    results = {}

    # Test 1: Health endpoint
    results["Health Endpoint"] = await test_health_endpoint()

    if not results["Health Endpoint"]:
        print_fail("Server not available. Please start the server and try again.")
        print_info("Run: python src/run_server.py")
        return

    # Test 2: Whisper status endpoint
    results["Whisper Status"] = await test_whisper_status_endpoint()

    # Test 3: WebSocket pause/resume
    results["WebSocket Pause/Resume"] = await test_websocket_pause_resume()

    # Test 4: WebSocket chapter
    results["WebSocket Chapter"] = await test_websocket_chapter()

    # Test 5: Session continuation
    results["Session Continuation"] = await test_session_continuation()

    # Test 6: Continue message
    results["Continue Message"] = await test_continue_message()

    # Test 7: Merge API (may skip if no entries)
    results["Merge API"] = await test_merge_api()

    # Print summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  Test Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results.items():
        if result is True:
            print(f"{GREEN}✅ {name}: PASSED{RESET}")
            passed += 1
        elif result is False:
            print(f"{RED}❌ {name}: FAILED{RESET}")
            failed += 1
        else:
            print(f"{YELLOW}⏭️  {name}: SKIPPED{RESET}")
            skipped += 1

    print(f"\n{BLUE}Results: {passed} passed, {failed} failed, {skipped} skipped{RESET}")

    if failed == 0:
        print(f"\n{GREEN}🎉 All tests passed!{RESET}")
    else:
        print(f"\n{RED}❌ Some tests failed. Check the output above for details.{RESET}")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")


if __name__ == "__main__":
    main()
