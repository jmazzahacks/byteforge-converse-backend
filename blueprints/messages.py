import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.exceptions import HTTPException

from common import service_manager

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

            db = service_manager.get_database()
            items = db.list_messages(conversation_id, limit=limit, offset=offset)

            return jsonify({
                "data": [item.to_dict() for item in items],
                "limit": limit,
                "offset": offset,
            })
        except HTTPException:
            raise
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

            role = data.get("role")
            content = data.get("content")
            if not role:
                abort(400, message="role is required")
            if content is None:
                abort(400, message="content is required")

            token_count = data.get("token_count")

            db = service_manager.get_database()
            if not db.get_conversation(conversation_id):
                abort(404, message=f"Conversation not found: {conversation_id}")

            item = db.create_message(
                conversation_id=conversation_id,
                role=str(role),
                content=str(content),
                token_count=int(token_count) if token_count is not None else None,
            )

            return jsonify(item.to_dict()), 201
        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error creating message: {e}")
            abort(500, message="Internal server error")
