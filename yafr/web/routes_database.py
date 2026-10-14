"""
Database routes and view controller for YAFR.

Implements DatabaseView for displaying database statistics, table row counts,
storage usage, table clearing actions, and remote database replacement.
"""

from flask import Blueprint, render_template
from yafr.db import get_session
from yafr.services import DatabaseService

database_bp = Blueprint("database", __name__)


@database_bp.route("/database", methods=["GET"])
def database_view():
    """
    Renders DatabaseView displaying active SQLite storage metrics, table row counts,
    and administrative tools (clear caches, download & replace database).
    """
    session = get_session()
    db_info = DatabaseService.get_database_info(session=session)
    return render_template(
        "database/view.html",
        db_info=db_info,
    )
