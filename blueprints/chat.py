import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort

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
            data = request.get_json()
            if not data:
                abort(400, message="Request body is required")
            if "content" not in data:
                abort(400, message="content is required")

            user_content = str(data["content"])

            # TODO: delegate to core service: append user message, call LLM,
            # persist assistant reply, return assistant Message.to_dict()
            _ = (conversation_id, user_content)

            return jsonify({
                "message": "Not yet implemented — core LLM orchestration pending",
            }), 501
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error handling chat turn: {e}")
            abort(500, message="Internal server error")
