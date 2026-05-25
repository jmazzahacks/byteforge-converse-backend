import time
import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.exceptions import HTTPException

from common import service_manager, get_user_id, require_uuid

logger = logging.getLogger(__name__)

# Default lifetime for a handshake session when the caller does not supply one.
SESSION_TTL_SECONDS = 3600

blp = Blueprint(
    "sessions",
    __name__,
    url_prefix="/api",
    description="Frontend handshake sessions",
)


@blp.route("/sessions")
class SessionListResource(MethodView):
    def post(self):
        """
        Issue a new handshake session for the frontend.

        Auth is handled by the consuming app — the verified user id is expected
        via an upstream gateway header (`X-User-Id`), with a body `user_id`
        accepted as a development fallback.
        """
        try:
            data = request.get_json(silent=True) or {}

            user_id = get_user_id(request)
            if not user_id:
                abort(400, message="user_id is required (X-User-Id header or body)")

            expires_at = data.get("expires_at")
            if expires_at is None:
                expires_at = int(time.time()) + SESSION_TTL_SECONDS
            else:
                expires_at = int(expires_at)

            conversation_id = data.get("conversation_id")
            db = service_manager.get_database()
            if conversation_id and not db.get_conversation(str(conversation_id)):
                abort(400, message=f"conversation_id does not exist: {conversation_id}")

            item = db.create_session(
                user_id=user_id,
                expires_at=expires_at,
                conversation_id=str(conversation_id) if conversation_id else None,
            )

            return jsonify(item.to_dict()), 201
        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            abort(400, message=str(e))
        except Exception as e:
            logger.exception(f"Error creating session: {e}")
            abort(500, message="Internal server error")


@blp.route("/sessions/<string:session_id>")
class SessionResource(MethodView):
    def get(self, session_id: str):
        try:
            require_uuid(session_id, "Session")
            db = service_manager.get_database()
            item = db.get_session(session_id)

            if not item:
                abort(404, message=f"Session not found: {session_id}")

            return jsonify(item.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error fetching session: {e}")
            abort(500, message="Internal server error")

    def delete(self, session_id: str):
        try:
            require_uuid(session_id, "Session")
            db = service_manager.get_database()
            revoked = db.delete_session(session_id)

            if not revoked:
                abort(404, message=f"Session not found: {session_id}")

            return jsonify({"message": "Revoked"})
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error revoking session: {e}")
            abort(500, message="Internal server error")
