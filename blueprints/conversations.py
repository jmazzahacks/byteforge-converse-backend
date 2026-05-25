import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from byteforge_converse_models import Conversation

logger = logging.getLogger(__name__)

blp = Blueprint(
    "conversations",
    __name__,
    url_prefix="/api",
    description="Conversation CRUD",
)


@blp.route("/conversations")
class ConversationListResource(MethodView):
    def get(self):
        try:
            limit = request.args.get("limit", 100, type=int)
            offset = request.args.get("offset", 0, type=int)

            # TODO: fetch conversations for the calling user via core service
            items: list[Conversation] = []

            return jsonify({
                "data": [item.to_dict() for item in items],
                "limit": limit,
                "offset": offset,
            })
        except ValueError as e:
            logger.warning(f"Bad request: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error fetching conversations: {e}")
            abort(500, message="Internal server error")

    def post(self):
        try:
            data = request.get_json()
            if not data:
                abort(400, message="Request body is required")

            item = Conversation.from_dict(data)

            # TODO: persist conversation via core service

            return jsonify(item.to_dict()), 201
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error creating conversation: {e}")
            abort(500, message="Internal server error")


@blp.route("/conversations/<string:conversation_id>")
class ConversationResource(MethodView):
    def get(self, conversation_id: str):
        try:
            # TODO: fetch conversation by id via core service
            item = None

            if not item:
                abort(404, message=f"Conversation not found: {conversation_id}")

            return jsonify(item.to_dict())
        except Exception as e:
            logger.exception(f"Error fetching conversation: {e}")
            abort(500, message="Internal server error")

    def delete(self, conversation_id: str):
        try:
            # TODO: delete conversation via core service

            return jsonify({"message": "Deleted"})
        except Exception as e:
            logger.exception(f"Error deleting conversation: {e}")
            abort(500, message="Internal server error")
