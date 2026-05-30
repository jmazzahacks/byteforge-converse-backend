import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.exceptions import HTTPException

from common import service_manager, require_uuid

logger = logging.getLogger(__name__)

blp = Blueprint(
    "chat",
    __name__,
    url_prefix="/api",
    description="LLM turn endpoint — submit a user message, receive a ChatTurn (assistant message plus any tool calls the model wants the caller to execute)",
)


@blp.route("/conversations/<string:conversation_id>/chat")
class ChatResource(MethodView):
    def post(self, conversation_id: str):
        """
        Submit a user message to the conversation and return a ChatTurn.

        Request body:
            {
                "content": "<user message>"
            }

        Response shape (200):
            {
                "message":    {... persisted assistant message ...},
                "tool_calls": [ {id, name, arguments}, ... ] or null
            }

        The assistant message is always persisted (its `content` may be empty
        for a pure tool-call turn, or carry narration that accompanied a
        tool call). When the model requested tool calls, `tool_calls` is
        populated and the caller is expected to execute each one out-of-band
        and feed the results back as `tool`-role messages (matching
        `tool_call_id`) before the next chat turn.
        """
        try:
            require_uuid(conversation_id, "Conversation")

            data = request.get_json()
            if not data:
                abort(400, message="Request body is required")
            if "content" not in data:
                abort(400, message="content is required")

            user_content = str(data["content"])

            chat_service = service_manager.get_chat_service()
            try:
                turn = chat_service.send_turn(conversation_id, user_content)
            except ValueError as e:
                # send_turn raises ValueError only when the conversation is missing.
                abort(404, message=str(e))

            return jsonify(turn.to_dict()), 200
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error handling chat turn: {e}")
            abort(500, message="Internal server error")
