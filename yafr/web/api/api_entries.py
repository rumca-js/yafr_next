"""
Lightweight REST / JSON API endpoints for Entry interactions.

Provides AJAX handlers for voting, bookmarking, read-later toggling,
visit recording, status code changes, and tags updates.
"""

import logging
from flask import Blueprint, request
from yafr.db import EntryRepository, HistoryRepository, get_session
from yafr.web.shared import api_response

logger = logging.getLogger(__name__)
api_entries_bp = Blueprint("api_entries", __name__, url_prefix="/api/entries")


@api_entries_bp.route("/<int:entry_id>/vote", methods=["POST"])
def vote_entry(entry_id: int):
    """
    Sets a user rating vote for an entry to an explicit number between -100 and 100.
    The vote value is set directly without increasing or decreasing.
    """
    session = get_session()
    repo = EntryRepository(session)
    entry = repo.get_by_id(entry_id)
    if not entry:
        return api_response(success=False, error="Entry not found", status_code=404)

    payload = request.get_json(silent=True) or {}
    if "vote" not in payload:
        return api_response(
            success=False,
            error="Missing 'vote' number in request payload",
            status_code=400,
        )

    try:
        vote_value = int(payload["vote"])
    except (ValueError, TypeError):
        return api_response(
            success=False,
            error="Vote must be a valid number",
            status_code=400,
        )

    if vote_value < -100 or vote_value > 100:
        return api_response(
            success=False,
            error="Vote must be between -100 and 100",
            status_code=400,
        )

    new_votes = repo.vote_entry(entry_id, vote_value)
    return api_response(
        success=True,
        data={"entry_id": entry_id, "page_rating_votes": new_votes},
        message=f"Vote set to {new_votes}",
    )


@api_entries_bp.route("/<int:entry_id>/bookmark", methods=["POST"])
def toggle_bookmark(entry_id: int):
    """
    Toggles the bookmarked flag for an entry.
    """
    session = get_session()
    repo = EntryRepository(session)
    state = repo.toggle_bookmark(entry_id)
    if state is None:
        return api_response(success=False, error="Entry not found", status_code=404)

    return api_response(
        success=True,
        data={"entry_id": entry_id, "bookmarked": state},
        message="Bookmark toggled",
    )


@api_entries_bp.route("/<int:entry_id>/read-later", methods=["POST"])
def toggle_read_later(entry_id: int):
    """
    Toggles the Read Later state for an entry.
    """
    session = get_session()
    entry_repo = EntryRepository(session)
    if not entry_repo.get_by_id(entry_id):
        return api_response(success=False, error="Entry not found", status_code=404)

    history_repo = HistoryRepository(session)
    is_saved = history_repo.toggle_read_later(entry_id)

    return api_response(
        success=True,
        data={"entry_id": entry_id, "read_later": is_saved},
        message="Read later updated",
    )


@api_entries_bp.route("/<int:entry_id>/visit", methods=["POST"])
def record_visit(entry_id: int):
    """
    Records a visit when a user navigates to an entry link.
    Optionally records navigation transition if 'from_entry_id' is supplied.
    """
    session = get_session()
    entry_repo = EntryRepository(session)
    if not entry_repo.get_by_id(entry_id):
        return api_response(success=False, error="Entry not found", status_code=404)

    history_repo = HistoryRepository(session)
    visit = history_repo.record_visit(entry_id)

    payload = request.get_json(silent=True) or {}
    from_entry_id = payload.get("from_entry_id")
    if from_entry_id is not None:
        try:
            from_id = int(from_entry_id)
            if from_id != entry_id and entry_repo.get_by_id(from_id):
                history_repo.record_transition(from_id, entry_id)
        except (ValueError, TypeError) as err:
            logger.debug("Ignored invalid from_entry_id: %s", err)

    return api_response(
        success=True,
        data={"entry_id": entry_id, "visits": visit.visits},
        message="Visit recorded",
    )


@api_entries_bp.route("/<int:entry_id>/status", methods=["POST"])
def set_status(entry_id: int):
    """
    Sets manual status code: 200 = active, 400 = dead.
    """
    session = get_session()
    repo = EntryRepository(session)

    payload = request.get_json(silent=True) or {}
    status_code = payload.get("status_code", 200)

    try:
        status_code = int(status_code)
    except (ValueError, TypeError):
        return api_response(success=False, error="Invalid status code", status_code=400)

    success = repo.set_manual_status(entry_id, status_code)
    if not success:
        return api_response(success=False, error="Entry not found", status_code=404)

    return api_response(
        success=True,
        data={"entry_id": entry_id, "manual_status_code": status_code},
        message="Status updated",
    )


@api_entries_bp.route("/<int:entry_id>/mark-active", methods=["POST"])
def mark_active(entry_id: int):
    """
    Sets manual_status_code = 200 (marking the entry as verified active).
    """
    session = get_session()
    repo = EntryRepository(session)
    success = repo.set_manual_status(entry_id, 200)
    if not success:
        return api_response(success=False, error="Entry not found", status_code=404)

    return api_response(
        success=True,
        data={"entry_id": entry_id, "manual_status_code": 200},
        message="Entry marked active",
    )


@api_entries_bp.route("/<int:entry_id>/mark-dead", methods=["POST"])
def mark_dead(entry_id: int):
    """
    Sets manual_status_code = 400 (marking the entry as dead).
    """
    session = get_session()
    repo = EntryRepository(session)
    success = repo.set_manual_status(entry_id, 400)
    if not success:
        return api_response(success=False, error="Entry not found", status_code=404)

    return api_response(
        success=True,
        data={"entry_id": entry_id, "manual_status_code": 400},
        message="Entry marked dead",
    )


@api_entries_bp.route("/<int:entry_id>/update-data", methods=["POST"])
def update_data(entry_id: int):
    """
    Enqueues a link metadata refresh job for the entry.
    """
    session = get_session()
    entry_repo = EntryRepository(session)
    entry = entry_repo.get_by_id(entry_id)
    if not entry:
        return api_response(success=False, error="Entry not found", status_code=404)

    from yafr.services.job_service import JobService

    job = JobService.create_job(
        job="link-update-data",
        subject=str(entry_id),
        session=session,
    )
    return api_response(
        success=True,
        data={"entry_id": entry_id, "job_id": job.id},
        message="Link update queued.",
    )


@api_entries_bp.route("/<int:entry_id>/reset-data", methods=["POST"])
def reset_data(entry_id: int):
    """
    Resets extracted metadata hashes and status code back to raw state.
    """
    session = get_session()
    entry_repo = EntryRepository(session)
    entry = entry_repo.get_by_id(entry_id)
    if not entry:
        return api_response(success=False, error="Entry not found", status_code=404)

    entry.contents_hash = None
    entry.body_hash = None
    entry.meta_hash = None
    entry.status_code = 0
    session.commit()

    return api_response(
        success=True,
        data={"entry_id": entry_id},
        message="Link data reset.",
    )


@api_entries_bp.route("/<int:entry_id>/tags", methods=["POST"])
def update_tags(entry_id: int):
    """
    Replaces the tags for an entry.
    """
    session = get_session()
    repo = EntryRepository(session)
    payload = request.get_json(silent=True) or {}
    tags = payload.get("tags", [])

    if not isinstance(tags, list):
        return api_response(
            success=False, error="Tags must be a list of strings", status_code=400
        )

    updated_tags = repo.set_tags(entry_id, tags)
    return api_response(
        success=True,
        data={"entry_id": entry_id, "tags": updated_tags},
        message="Tags updated",
    )


@api_entries_bp.route("/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id: int):
    """
    Deletes an entry and cascades to all satellite tables.
    """
    session = get_session()
    repo = EntryRepository(session)
    success = repo.delete_entry(entry_id)
    if not success:
        return api_response(success=False, error="Entry not found", status_code=404)

    return api_response(
        success=True,
        data={"entry_id": entry_id},
        message="Entry deleted successfully",
    )


@api_entries_bp.route("/batch-delete", methods=["POST"])
def batch_delete():
    """
    Batch deletes multiple entries by ID list.
    """
    session = get_session()
    repo = EntryRepository(session)
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids", [])

    if not isinstance(ids, list) or not ids:
        return api_response(
            success=False, error="Invalid or empty ID list", status_code=400
        )

    deleted_count = repo.delete_entries(ids)
    return api_response(
        success=True,
        data={"deleted_count": deleted_count},
        message=f"Deleted {deleted_count} entries",
    )
