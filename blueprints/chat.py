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
    description="LLM turn endpoint — submit a user message, receive an assistant reply",
)


@blp.route("/conversations/<string:conversation_id>/chat")
class ChatResource(MethodView):
    def post(self, conversation_id: str):
        """
        Submit a user message to the conversation and return the assistant reply.

        Request body:
            {
                "content": "<user message>"
            }
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
                assistant_message = chat_service.send_turn(conversation_id, user_content)
            except ValueError as e:
                # send_turn raises ValueError only when the conversation is missing.
                abort(404, message=str(e))

            return jsonify(assistant_message.to_dict()), 201
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error handling chat turn: {e}")
            abort(500, message="Internal server error")
