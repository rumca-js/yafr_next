"""
Configuration routes and view controller for YAFR.

Implements ConfigurationView for managing display themes, card layouts,
alpha transparencies, quotas, limits, crawler rules, and quick UI presets.
"""

import logging
from flask import Blueprint, flash, redirect, render_template, request, url_for
from yafr.db import get_session
from yafr.services import ConfigService
from yafr.web.shared import (
    CONFIGURATION_GALLERY,
    CONFIGURATION_NEWS,
    CONFIGURATION_SEARCH_ENGINE,
    DISPLAY_STYLES,
    DISPLAY_TYPES,
)

logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__)

# Known boolean fields in the configuration form that should be False if missing
BOOLEAN_CONFIG_FIELDS = [
    "show_icons",
    "thumbnails_as_icons",
    "small_icons",
    "local_icons",
    "highlight_bookmarks",
    "click_behavior_modal_window",
    "track_user_searches",
    "track_user_navigation",
    "prefer_https_links",
    "prefer_non_www_links",
    "accept_dead_links",
    "accept_domain_links",
    "accept_ip_links",
    "accept_onion_links",
    "accept_same_hashes",
    "auto_store_thumbnails",
    "enable_social_data",
    "debug_mode",
]


@config_bp.route("/configuration", methods=["GET"])
def configuration_view():
    """
    Renders ConfigurationView displaying all user-customizable application settings,
    appearance options, limits, alphas, and presets.
    """
    session = get_session()
    config = ConfigService.get_config_model(session=session)

    presets = [
        {
            "id": "gallery",
            "name": CONFIGURATION_GALLERY,
            "icon": "bi-grid-3x3-gap",
            "description": "Visual grid with large media thumbnails, ideal for video feeds and rich bookmarks.",
        },
        {
            "id": "search-engine",
            "name": CONFIGURATION_SEARCH_ENGINE,
            "icon": "bi-search",
            "description": "Textual search layout with minimal distractions and direct external links.",
        },
        {
            "id": "news",
            "name": CONFIGURATION_NEWS,
            "icon": "bi-newspaper",
            "description": "Content-centric card list with expanded descriptions and article metadata.",
        },
    ]

    return render_template(
        "configuration/view.html",
        config=config,
        display_types=DISPLAY_TYPES,
        display_styles=DISPLAY_STYLES,
        presets=presets,
    )


@config_bp.route("/configuration", methods=["POST"])
def update_configuration():
    """
    Processes form submissions to update application settings and redirects back to view.
    """
    session = get_session()
    form_data = request.form.to_dict()

    # Form checkboxes only send values when checked; set unchecked ones to False
    update_payload = {}
    for bool_field in BOOLEAN_CONFIG_FIELDS:
        update_payload[bool_field] = bool_field in form_data

    # Add other non-boolean fields present in the form
    for key, value in form_data.items():
        if key not in BOOLEAN_CONFIG_FIELDS and key != "csrf_token":
            update_payload[key] = value

    try:
        ConfigService.update_config(update_payload, session=session)
        flash("Configuration updated successfully.", "success")
    except Exception as err:
        logger.error("Failed to save configuration from form: %s", err)
        flash(f"Error saving configuration: {err}", "danger")

    return redirect(url_for("config.configuration_view"))
