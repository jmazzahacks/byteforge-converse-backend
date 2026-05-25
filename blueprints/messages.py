import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from byteforge_converse_models import Message

logger = logging.getLogger(__name__)

blp = Blueprint(
    "messages",
    __name__,
    url_prefix="/api",
    description="Conversation message history",
)


@blp.route("/conversations/<string:conversation_id>/messages")
class MessageListResource(MethodView):
    def get(self, conversation_id: str):
        try:
            limit = request.args.get("limit", 100, type=int)
            offset = request.args.get("offset", 0, type=int)

            # TODO: fetch messages for conversation via core service
            items: list[Message] = []

            return jsonify({
                "data": [item.to_dict() for item in items],
                "limit": limit,
                "offset": offset,
            })
        except ValueError as e:
            logger.warning(f"Bad request: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error fetching messages: {e}")
            abort(500, message="Internal server error")

    def post(self, conversation_id: str):
        try:
            data = request.get_json()
            if not data:
                abort(400, message="Request body is required")

            # Force the conversation id from the URL to match the path
            data["conversation_id"] = conversation_id
            item = Message.from_dict(data)

            # TODO: persist message via core service

            return jsonify(item.to_dict()), 201
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error creating message: {e}")
            abort(500, message="Internal server error")
