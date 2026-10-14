/**
 * YAFR Logs View Client-Side Script
 *
 * Handles individual log deletion and bulk clear operations
 * via AJAX calls to the JSON API.
 */
document.addEventListener("DOMContentLoaded", function () {

  // 1. Delete Individual Log Entry
  $(document).on("click", ".delete-log-btn", function () {
    var btn = $(this);
    var logId = btn.data("log-id");
    if (!logId) return;

    $.ajax({
      url: "/api/logs/" + logId,
      type: "DELETE",
      dataType: "json",
      success: function (resp) {
        if (resp.success) {
          $("#log-row-" + logId).fadeOut(300, function () {
            $(this).remove();
            // If table is now empty, reload to show empty state
            if ($("#logs-table-body tr").length === 0) {
              window.location.reload();
            }
          });
        } else {
          alert("Failed to delete log entry: " + (resp.error || "Unknown error"));
        }
      },
      error: function () {
        alert("Network error while deleting log entry.");
      }
    });
  });

  // 2. Clear All Logs (Confirm Modal)
  $("#confirm-clear-logs-btn").on("click", function () {
    var btn = $(this);
    btn.prop("disabled", true).html(
      '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Clearing...'
    );

    $.ajax({
      url: "/api/logs/clear",
      type: "POST",
      dataType: "json",
      success: function (resp) {
        if (resp.success) {
          window.location.href = window.location.pathname;
        } else {
          btn.prop("disabled", false).html(
            '<i class="bi bi-trash me-1"></i>Clear All Logs'
          );
          alert("Failed to clear logs: " + (resp.error || "Unknown error"));
        }
      },
      error: function () {
        btn.prop("disabled", false).html(
          '<i class="bi bi-trash me-1"></i>Clear All Logs'
        );
        alert("Network error while clearing logs.");
      }
    });
  });
});
