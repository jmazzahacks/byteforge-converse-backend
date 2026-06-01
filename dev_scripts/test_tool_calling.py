#!/usr/bin/env python
"""
End-to-end test of the tool-call relay loop against a deployed backend.

Drives a real OpenRouter model through:

  1. Create conversation advertising a fake `get_weather(city)` tool.
  2. Send a user message that should force a tool call.
  3. Assert the returned ChatTurn carries a parseable `get_weather` call.
  4. POST a fabricated tool result via /messages with the matching tool_call_id.
  5. Send a follow-up turn (nudge text — the empty-content path is a TBD).
  6. Assert the model's next reply references the fabricated result.

The script never executes the tool; ByteforgeConverse never executes the tool;
the relay path is what we are verifying.

Usage:
  python dev_scripts/test_tool_calling.py
  python dev_scripts/test_tool_calling.py --base-url http://localhost:5252
  python dev_scripts/test_tool_calling.py --user-id <stable-uuid> --keep
"""

import argparse
import json
import sys
import uuid
from typing import Optional, Tuple

from byteforge_converse_api import ConverseClient, ConverseAPIError
from byteforge_converse_models import ChatTurn


DEFAULT_BASE_URL = "http://100.111.126.25:5252"

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Tokyo'",
                },
            },
            "required": ["city"],
        },
    },
}

SYSTEM_PROMPT = (
    "You are a weather assistant. When the user asks about the weather in a "
    "city, call the `get_weather` tool with the city name. After you receive "
    "the tool result, summarize it for the user in one short sentence."
)

USER_QUESTION = "What's the weather in Tokyo?"
FAKE_TOOL_RESULT = "Sunny, 28C with light winds."
FOLLOW_UP_PROMPT = "What did the tool tell you?"

# Substrings we expect to see (lower-cased) in the model's follow-up reply
# to prove it actually consumed the fabricated tool result.
EXPECTED_REPLY_MARKERS = ["sunny", "28"]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def step_create_conversation(client: ConverseClient) -> str:
    print("Step 1 - create conversation with `get_weather` tool")
    conv = client.create_conversation({
        "title": "tool-call relay test",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [WEATHER_TOOL],
    })
    print(f"  OK conversation {conv.id}")
    return conv.id


def step_send_user_message(client: ConverseClient, conversation_id: str) -> ChatTurn:
    print(f"Step 2 - user: {USER_QUESTION!r}")
    turn = client.chat(conversation_id, USER_QUESTION)
    content = turn.message.content or ""
    print(f"  OK assistant message persisted (id={turn.message.id})")
    if content:
        print(f"     narration: {content!r}")
    return turn


def step_assert_tool_call(turn: ChatTurn) -> Tuple[str, dict]:
    print("Step 3 - assert ChatTurn carries a `get_weather` tool call")
    if not turn.tool_calls:
        fail("turn.tool_calls is empty - the model did not request the tool")

    if len(turn.tool_calls) != 1:
        print(f"  WARN: expected 1 tool call, got {len(turn.tool_calls)}; using the first")

    tc = turn.tool_calls[0]
    if tc.name != "get_weather":
        fail(f"expected tool name 'get_weather', got {tc.name!r}")

    try:
        parsed_args = json.loads(tc.arguments)
    except json.JSONDecodeError as e:
        fail(f"arguments is not valid JSON: {e}\n    raw: {tc.arguments!r}")

    if not isinstance(parsed_args, dict):
        fail(f"arguments did not parse to an object: {parsed_args!r}")
    if "city" not in parsed_args:
        fail(f"arguments missing 'city' key: {parsed_args}")
    if "tokyo" not in str(parsed_args["city"]).lower():
        print(f"  WARN: city != 'Tokyo' (got {parsed_args['city']!r}) - continuing")

    print(f"  OK tool_call id={tc.id} args={parsed_args}")
    return tc.id, parsed_args


def step_post_tool_result(
    client: ConverseClient,
    conversation_id: str,
    tool_call_id: str,
) -> None:
    print(f"Step 4 - POST fake tool result for tool_call_id={tool_call_id}")
    msg = client.post_message(conversation_id, {
        "role": "tool",
        "content": FAKE_TOOL_RESULT,
        "tool_call_id": tool_call_id,
    })
    print(f"  OK tool message persisted (id={msg.id})")


def step_follow_up_turn(client: ConverseClient, conversation_id: str) -> ChatTurn:
    print(f"Step 5 - user: {FOLLOW_UP_PROMPT!r}")
    turn = client.chat(conversation_id, FOLLOW_UP_PROMPT)
    content = turn.message.content or ""
    print(f"  OK assistant reply: {content!r}")
    return turn


def step_assert_summary(turn: ChatTurn) -> None:
    print("Step 6 - assert reply references the fabricated tool result")
    content = (turn.message.content or "").lower()
    matched = [m for m in EXPECTED_REPLY_MARKERS if m in content]
    if not matched:
        fail(
            "follow-up reply does not reference the fabricated result.\n"
            f"    expected one of: {EXPECTED_REPLY_MARKERS}\n"
            f"    got: {turn.message.content!r}"
        )
    print(f"  OK reply contains: {matched}")


def cleanup(client: ConverseClient, conversation_id: str) -> None:
    try:
        client.delete_conversation(conversation_id)
        print(f"  cleaned up conversation {conversation_id}")
    except ConverseAPIError as e:
        print(f"  WARN: cleanup failed for {conversation_id}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tool-call relay end-to-end test against a deployed converse backend",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Backend base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="X-User-Id header value (default: a fresh UUID per run)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Skip deleting the conversation at the end (useful for post-mortem inspection)",
    )
    args = parser.parse_args()

    user_id = args.user_id or str(uuid.uuid4())
    print(f"Target:  {args.base_url}")
    print(f"User id: {user_id}")
    print()

    client = ConverseClient(
        base_url=args.base_url,
        extra_headers={"X-User-Id": user_id},
    )

    conversation_id: Optional[str] = None
    try:
        conversation_id = step_create_conversation(client)
        turn1 = step_send_user_message(client, conversation_id)
        tool_call_id, _ = step_assert_tool_call(turn1)
        step_post_tool_result(client, conversation_id, tool_call_id)
        turn2 = step_follow_up_turn(client, conversation_id)
        step_assert_summary(turn2)
        print()
        print("PASS: tool-call relay verified end-to-end.")
    except ConverseAPIError as e:
        fail(f"API error: {e}")
    finally:
        if conversation_id and not args.keep:
            cleanup(client, conversation_id)
        client.close()


if __name__ == "__main__":
    main()
