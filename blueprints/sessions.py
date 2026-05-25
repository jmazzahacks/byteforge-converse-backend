import logging

from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from byteforge_converse_models import Session

logger = logging.getLogger(__name__)

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

        Auth is handled by the consuming app — the verified user id is
        expected to arrive via an upstream gateway header (e.g., X-User-Id)
        or in the request body for now.
        """
        try:
            data = request.get_json() or {}

            # TODO: read user id from upstream-injected header instead of body
            # in real deployments
            item = Session.from_dict(data)

            # TODO: persist session via core service

            return jsonify(item.to_dict()), 201
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
            # TODO: fetch session by id via core service
            item = None

            if not item:
                abort(404, message=f"Session not found: {session_id}")

            return jsonify(item.to_dict())
        except Exception as e:
            logger.exception(f"Error fetching session: {e}")
            abort(500, message="Internal server error")

    def delete(self, session_id: str):
        try:
            # TODO: revoke session via core service

            return jsonify({"message": "Revoked"})
        except Exception as e:
            logger.exception(f"Error revoking session: {e}")
            abort(500, message="Internal server error")
