"""
Flask application factory.
"""

from flask import Flask, render_template
from yafr.config import Config
from yafr.web import register_blueprints


def create_app(config_object=None) -> Flask:
    """
    Constructs and configures the Flask application.

    :param config_object: Optional configuration class
    :return: Configured Flask application instance
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.config.from_object(Config)
    if config_object:
        if isinstance(config_object, dict):
            app.config.from_mapping(config_object)
        else:
            app.config.from_object(config_object)

    # Register routes and views
    register_blueprints(app)

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return (
            render_template(
                "entries/list.html",
                error_message="Page or entry not found (404).",
                query="",
                has_query=False,
                entries=[],
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return (
            render_template(
                "entries/list.html",
                error_message="Internal server error (500).",
                query="",
                has_query=False,
                entries=[],
            ),
            500,
        )

    return app
