import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.exceptions import HTTPException

from common import service_manager, get_user_id

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
            user_id = get_user_id(request)
            if not user_id:
                abort(400, message="user_id is required (X-User-Id header or ?user_id=)")

            limit = request.args.get("limit", 100, type=int)
            offset = request.args.get("offset", 0, type=int)

            db = service_manager.get_database()
            items = db.list_conversations(user_id, limit=limit, offset=offset)

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
            logger.exception(f"Error fetching conversations: {e}")
            abort(500, message="Internal server error")

    def post(self):
        try:
            data = request.get_json()
            if not data:
                abort(400, message="Request body is required")

            user_id = get_user_id(request)
            if not user_id:
                abort(400, message="user_id is required (X-User-Id header or body)")

            title = data.get("title")
            if not title:
                abort(400, message="title is required")

            db = service_manager.get_database()
            item = db.create_conversation(user_id=user_id, title=str(title))

            return jsonify(item.to_dict()), 201
        except HTTPException:
            raise
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
            db = service_manager.get_database()
            item = db.get_conversation(conversation_id)

            if not item:
                abort(404, message=f"Conversation not found: {conversation_id}")

            return jsonify(item.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error fetching conversation: {e}")
            abort(500, message="Internal server error")

    def delete(self, conversation_id: str):
        try:
            db = service_manager.get_database()
            deleted = db.delete_conversation(conversation_id)

            if not deleted:
                abort(404, message=f"Conversation not found: {conversation_id}")

            return jsonify({"message": "Deleted"})
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error deleting conversation: {e}")
            abort(500, message="Internal server error")
