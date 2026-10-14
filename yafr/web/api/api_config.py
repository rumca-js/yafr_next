"""
RESTful JSON API endpoints for Application Configuration.

Implements small, focused server endpoints returning JSON responses for updating
display styles, display types, alphas, presets, and general configuration settings.
"""

import logging
from flask import Blueprint, jsonify, request
from yafr.db import get_session
from yafr.services import ConfigService
from yafr.web.shared import api_response

logger = logging.getLogger(__name__)

api_config_bp = Blueprint("api_config", __name__, url_prefix="/api/config")


@api_config_bp.route("", methods=["GET"])
def get_config():
    """
    Retrieves the current application configuration as JSON.
    """
    try:
        session = get_session()
        config_data = ConfigService.get_config_dict(session=session)
        return jsonify({"success": True, "config": config_data})
    except Exception as err:
        logger.error("Failed to fetch configuration: %s", err)
        return api_response(success=False, error=str(err), status_code=500)


@api_config_bp.route("/style", methods=["POST"])
def update_style():
    """
    Quickly switches display style theme ('style-light' or 'style-dark').
    """
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        display_style = payload.get("display_style", "").strip()

        if not display_style:
            return api_response(
                success=False,
                error="Field 'display_style' is required.",
                status_code=400,
            )

        session = get_session()
        config = ConfigService.set_display_style(display_style, session=session)
        return jsonify({"success": True, "display_style": config.display_style})
    except ValueError as val_err:
        return api_response(success=False, error=str(val_err), status_code=400)
    except Exception as err:
        logger.error("Failed to update display style: %s", err)
        return api_response(success=False, error=str(err), status_code=500)


@api_config_bp.route("/display-type", methods=["POST"])
def update_display_type():
    """
    Switches entry layout card type ('gallery', 'standard', 'search-engine', etc.).
    """
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        display_type = payload.get("display_type", "").strip()

        if not display_type:
            return api_response(
                success=False,
                error="Field 'display_type' is required.",
                status_code=400,
            )

        session = get_session()
        config = ConfigService.set_display_type(display_type, session=session)
        return jsonify({"success": True, "display_type": config.display_type})
    except ValueError as val_err:
        return api_response(success=False, error=str(val_err), status_code=400)
    except Exception as err:
        logger.error("Failed to update display type: %s", err)
        return api_response(success=False, error=str(err), status_code=500)


@api_config_bp.route("/preset", methods=["POST"])
def apply_preset():
    """
    Applies a predefined UI display preset ('search-engine', 'gallery', or 'news').
    """
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        preset_name = payload.get("preset", "").strip()

        if not preset_name:
            return api_response(
                success=False,
                error="Field 'preset' is required.",
                status_code=400,
            )

        session = get_session()
        config = ConfigService.apply_preset(preset_name, session=session)
        return jsonify(
            {
                "success": True,
                "preset": preset_name,
                "display_type": config.display_type,
                "message": f"Applied '{preset_name}' preset successfully.",
            }
        )
    except ValueError as val_err:
        return api_response(success=False, error=str(val_err), status_code=400)
    except Exception as err:
        logger.error("Failed to apply preset: %s", err)
        return api_response(success=False, error=str(err), status_code=500)


@api_config_bp.route("/update", methods=["POST"])
def update_config():
    """
    Updates arbitrary configuration settings via JSON payload.
    """
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        if not payload:
            return api_response(
                success=False,
                error="No configuration payload provided.",
                status_code=400,
            )

        session = get_session()
        config = ConfigService.update_config(payload, session=session)
        return jsonify(
            {
                "success": True,
                "message": "Configuration updated successfully.",
                "display_style": config.display_style,
                "display_type": config.display_type,
            }
        )
    except Exception as err:
        logger.error("Failed to update configuration: %s", err)
        return api_response(success=False, error=str(err), status_code=500)


@api_config_bp.route("/reset", methods=["POST"])
def reset_config():
    """
    Resets all configuration values to system defaults.
    """
    try:
        session = get_session()
        ConfigService.reset_defaults(session=session)
        return jsonify(
            {
                "success": True,
                "message": "Configuration successfully reset to defaults.",
            }
        )
    except Exception as err:
        logger.error("Failed to reset configuration: %s", err)
        return api_response(success=False, error=str(err), status_code=500)
