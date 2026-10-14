"""
Jobs routes and view controller for YAFR.

Implements JobsView for viewing, filtering, sorting, and managing
background task jobs in the backgroundjob SQLite table.
"""

import math
from flask import Blueprint, render_template, request
from yafr.db import get_session
from yafr.services import JobService

jobs_bp = Blueprint("jobs", __name__)

# Status filter options for the UI dropdown
STATUS_FILTERS = [
    {"id": "all", "name": "All Statuses"},
    {"id": "enabled", "name": "Active / Enabled"},
    {"id": "paused", "name": "Paused"},
    {"id": "errors", "name": "With Errors"},
]

# Sorting options
ORDER_OPTIONS = [
    {"id": "priority", "name": "Priority (Highest first)"},
    {"id": "date_created", "name": "Date Created (Newest first)"},
    {"id": "errors", "name": "Errors (Most failures)"},
    {"id": "enabled", "name": "Status (Active first)"},
]


@jobs_bp.route("/jobs")
def jobs_list():
    """
    Renders JobsView — a paginated, filterable, and sortable table of background jobs.

    Query parameters:
        - status: Filter by status ('all', 'enabled', 'paused', 'errors')
        - job_type: Filter by specific job type or 'all'
        - order_by: Sort column ('priority', 'date_created', 'errors', 'enabled')
        - page: Page number (1-indexed)
    """
    active_status = request.args.get("status", "all")
    active_type = request.args.get("job_type", "all")
    order_by = request.args.get("order_by", "priority")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 50

    # Parse filter criteria
    enabled_filter = None
    has_errors_filter = None

    if active_status == "enabled":
        enabled_filter = True
    elif active_status == "paused":
        enabled_filter = False
    elif active_status == "errors":
        has_errors_filter = True

    type_filter = None if active_type == "all" else active_type

    session = get_session()

    total_results = JobService.count_jobs(
        enabled=enabled_filter,
        has_errors=has_errors_filter,
        job_type=type_filter,
        session=session,
    )
    total_pages = max(1, math.ceil(total_results / per_page)) if total_results > 0 else 1

    offset = (page - 1) * per_page
    jobs = JobService.list_jobs(
        enabled=enabled_filter,
        order_by=order_by,
        limit=per_page,
        offset=offset,
        has_errors=has_errors_filter,
        job_type=type_filter,
        session=session,
    )

    distinct_job_types = JobService.get_job_types(session=session)
    error_jobs_count = JobService.count_error_jobs(session=session)

    return render_template(
        "jobs/list.html",
        jobs=jobs,
        active_status=active_status,
        active_type=active_type,
        order_by=order_by,
        status_filters=STATUS_FILTERS,
        order_options=ORDER_OPTIONS,
        job_types=distinct_job_types,
        total_results=total_results,
        error_jobs_count=error_jobs_count,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
    )
