import os
import logging

from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
from dotenv import load_dotenv
from byteforge_loki_logging import configure_logging

load_dotenv()

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    # configure_logging() must run INSIDE create_app() so it executes in the
    # gunicorn WORKER process (post-fork). At module level it runs in the
    # master process and the Loki handler's SSL session does not survive fork.
    debug_mode = os.environ.get("DEBUG_LOCAL", "true").lower() == "true"
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    configure_logging(
        application_tag="byteforge-converse-backend",
        debug_local=debug_mode,
        local_level=log_level,
    )

    app = Flask(__name__)
    app.config["API_TITLE"] = "ByteforgeConverse Backend API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.2"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    CORS(app)
    api = Api(app)

    from blueprints.conversations import blp as conversations_blp
    from blueprints.messages import blp as messages_blp
    from blueprints.chat import blp as chat_blp
    from blueprints.sessions import blp as sessions_blp

    api.register_blueprint(conversations_blp)
    api.register_blueprint(messages_blp)
    api.register_blueprint(chat_blp)
    api.register_blueprint(sessions_blp)

    # Force Flask/werkzeug/gunicorn loggers to propagate to root so unhandled
    # exceptions and access logs reach Loki via byteforge-loki-logging's
    # root handler. Must run AFTER Flask + Api init so their handlers are
    # already attached and we are overriding them — not the other way around.
    app.logger.handlers.clear()
    app.logger.propagate = True
    app.logger.setLevel(logging.DEBUG)

    for name in ("werkzeug", "gunicorn", "gunicorn.error", "gunicorn.access"):
        dep_logger = logging.getLogger(name)
        dep_logger.handlers.clear()
        dep_logger.propagate = True

    logger.info("Flask app initialized")
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5252))
    app = create_app()
    logger.info(f"Swagger UI: http://localhost:{port}/swagger")
    app.run(host="0.0.0.0", port=port)
