import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

# Global SQLAlchemy instance so models can import it
db = SQLAlchemy()


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory that wires Flask and SQLAlchemy."""
    app = Flask(__name__, instance_relative_config=False)

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from . import routes

    app.register_blueprint(routes.bp)

    return app
