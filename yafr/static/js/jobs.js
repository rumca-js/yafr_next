/**
 * YAFR Background Jobs View Client-Side Script
 *
 * Handles job creation, individual pause/resume/delete,
 * and batch operations (pause, resume, delete) with AJAX.
 */
document.addEventListener("DOMContentLoaded", function () {
  var pendingDeleteId = null;
  var isBatchDelete = false;

  // Helper: get array of selected job IDs
  function getSelectedJobIds() {
    var ids = [];
    $(".job-checkbox:checked").each(function () {
      var val = parseInt($(this).val(), 10);
      if (!isNaN(val)) {
        ids.push(val);
      }
    });
    return ids;
  }

  // Helper: update batch action toolbar visibility and counter
  function updateBatchBar() {
    var count = $(".job-checkbox:checked").length;
    var total = $(".job-checkbox").length;
    $("#selected-jobs-count").text(count);

    if (count > 0) {
      $("#batch-action-bar").removeClass("d-none");
    } else {
      $("#batch-action-bar").addClass("d-none");
    }

    // Update select-all master checkbox state
    $("#select-all-jobs").prop("checked", total > 0 && count === total);
  }

  // 1. Select All Checkbox Handler
  $("#select-all-jobs").on("change", function () {
    var isChecked = $(this).is(":checked");
    $(".job-checkbox").prop("checked", isChecked);
    updateBatchBar();
  });

  // 2. Individual Checkbox Change
  $(document).on("change", ".job-checkbox", function () {
    updateBatchBar();
  });

  // 3. Toggle Job (Pause / Resume)
  $(document).on("click", ".toggle-job-btn", function () {
    var btn = $(this);
    var jobId = btn.data("job-id");
    var action = btn.data("action"); // "pause" or "resume"
    if (!jobId || !action) return;

    btn.prop("disabled", true);
    var url = "/api/jobs/" + jobId + "/" + action;

    $.ajax({
      url: url,
      type: "POST",
      dataType: "json",
      success: function (resp) {
        btn.prop("disabled", false);
        if (resp.success) {
          var statusCol = $("#job-status-col-" + jobId);
          if (action === "pause") {
            statusCol.html(
              '<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle">' +
                '<i class="bi bi-pause-fill me-1"></i>Paused</span>'
            );
            btn
              .data("action", "resume")
              .attr("title", "Resume job")
              .removeClass("btn-outline-secondary")
              .addClass("btn-outline-success")
              .html('<i class="bi bi-play-fill"></i>');
          } else {
            statusCol.html(
              '<span class="badge bg-success-subtle text-success border border-success-subtle">' +
                '<i class="bi bi-play-fill me-1"></i>Active</span>'
            );
            btn
              .data("action", "pause")
              .attr("title", "Pause job")
              .removeClass("btn-outline-success")
              .addClass("btn-outline-secondary")
              .html('<i class="bi bi-pause-fill"></i>');
          }
        } else {
          alert("Failed to " + action + " job: " + (resp.error || "Unknown error"));
        }
      },
      error: function () {
        btn.prop("disabled", false);
        alert("Network error while trying to " + action + " job.");
      },
    });
  });

  // 4. Single Delete Button (opens confirmation modal)
  $(document).on("click", ".delete-single-job-btn", function () {
    var jobId = $(this).data("job-id");
    if (!jobId) return;

    pendingDeleteId = jobId;
    isBatchDelete = false;

    $("#delete-job-modal-text").html(
      "Are you sure you want to permanently delete background job <strong>#" +
        jobId +
        "</strong>?"
    );

    var modal = new bootstrap.Modal(document.getElementById("deleteJobModal"));
    modal.show();
  });

  // 5. Batch Delete Button (opens confirmation modal)
  $("#batch-delete-btn").on("click", function () {
    var ids = getSelectedJobIds();
    if (ids.length === 0) return;

    pendingDeleteId = null;
    isBatchDelete = true;

    $("#delete-job-modal-text").html(
      "Are you sure you want to permanently delete <strong>" +
        ids.length +
        "</strong> selected background jobs?"
    );

    var modal = new bootstrap.Modal(document.getElementById("deleteJobModal"));
    modal.show();
  });

  // 6. Confirm Delete in Modal
  $("#confirm-delete-job-btn").on("click", function () {
    var btn = $(this);
    btn.prop("disabled", true).html(
      '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Deleting...'
    );

    if (isBatchDelete) {
      var ids = getSelectedJobIds();
      $.ajax({
        url: "/api/jobs/batch-action",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ job_ids: ids, action: "delete" }),
        dataType: "json",
        success: function (resp) {
          var modalEl = document.getElementById("deleteJobModal");
          var modalInstance = bootstrap.Modal.getInstance(modalEl);
          if (modalInstance) modalInstance.hide();
          window.location.reload();
        },
        error: function () {
          btn.prop("disabled", false).html('<i class="bi bi-trash me-1"></i>Delete');
          alert("Network error during batch deletion.");
        },
      });
    } else if (pendingDeleteId) {
      var targetId = pendingDeleteId;
      $.ajax({
        url: "/api/jobs/" + targetId,
        type: "DELETE",
        dataType: "json",
        success: function (resp) {
          var modalEl = document.getElementById("deleteJobModal");
          var modalInstance = bootstrap.Modal.getInstance(modalEl);
          if (modalInstance) modalInstance.hide();

          btn.prop("disabled", false).html('<i class="bi bi-trash me-1"></i>Delete');
          $("#job-row-" + targetId).fadeOut(300, function () {
            $(this).remove();
            updateBatchBar();
            if ($("#jobs-table-body tr").length === 0) {
              window.location.reload();
            }
          });
        },
        error: function () {
          btn.prop("disabled", false).html('<i class="bi bi-trash me-1"></i>Delete');
          alert("Network error deleting job.");
        },
      });
    }
  });

  // 7. Batch Pause
  $("#batch-pause-btn").on("click", function () {
    var ids = getSelectedJobIds();
    if (ids.length === 0) return;

    var btn = $(this);
    btn.prop("disabled", true);

    $.ajax({
      url: "/api/jobs/batch-action",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify({ job_ids: ids, action: "pause" }),
      dataType: "json",
      success: function (resp) {
        if (resp.success) {
          window.location.reload();
        } else {
          btn.prop("disabled", false);
          alert("Batch pause failed: " + (resp.error || "Unknown error"));
        }
      },
      error: function () {
        btn.prop("disabled", false);
        alert("Network error during batch pause.");
      },
    });
  });

  // 8. Batch Resume
  $("#batch-resume-btn").on("click", function () {
    var ids = getSelectedJobIds();
    if (ids.length === 0) return;

    var btn = $(this);
    btn.prop("disabled", true);

    $.ajax({
      url: "/api/jobs/batch-action",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify({ job_ids: ids, action: "resume" }),
      dataType: "json",
      success: function (resp) {
        if (resp.success) {
          window.location.reload();
        } else {
          btn.prop("disabled", false);
          alert("Batch resume failed: " + (resp.error || "Unknown error"));
        }
      },
      error: function () {
        btn.prop("disabled", false);
        alert("Network error during batch resume.");
      },
    });
  });

  // 9. Create Job Form Submission
  $("#create-job-form").on("submit", function (e) {
    e.preventDefault();
    var submitBtn = $("#submit-create-job-btn");

    var payload = {
      job: $("#create-job-name").val().trim(),
      subject: $("#create-job-subject").val().trim(),
      priority: parseInt($("#create-job-priority").val(), 10) || 1,
      task: $("#create-job-task").val().trim() || null,
      args: $("#create-job-args").val().trim() || null,
      enabled: $("#create-job-enabled").is(":checked"),
    };

    if (!payload.job || !payload.subject) {
      alert("Job type and Subject are required.");
      return;
    }

    submitBtn.prop("disabled", true).html(
      '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Creating...'
    );

    $.ajax({
      url: "/api/jobs/create",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify(payload),
      dataType: "json",
      success: function (resp) {
        if (resp.success) {
          var modalEl = document.getElementById("createJobModal");
          var modalInstance = bootstrap.Modal.getInstance(modalEl);
          if (modalInstance) modalInstance.hide();
          window.location.reload();
        } else {
          submitBtn
            .prop("disabled", false)
            .html('<i class="bi bi-check-lg me-1"></i>Create Job');
          alert("Failed to create job: " + (resp.error || "Unknown error"));
        }
      },
      error: function () {
        submitBtn
          .prop("disabled", false)
          .html('<i class="bi bi-check-lg me-1"></i>Create Job');
        alert("Network error creating job.");
      },
    });
  });
});
