/**
 * rules.js - Entry Rules screen interactions for YAFR.
 *
 * Handles:
 *  - AJAX toggle (enable/disable) for individual rules
 *  - Delete confirmation modal wiring
 */

$(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Toggle Rule Enabled / Disabled                                       */
  /* ------------------------------------------------------------------ */

  $(document).on("click", ".toggle-rule-btn", function () {
    const btn = $(this);
    const ruleId = btn.data("rule-id");

    btn.prop("disabled", true);

    $.ajax({
      url: `/rules/${ruleId}/toggle`,
      method: "POST",
      dataType: "json",
      success: function (data) {
        if (!data.success) {
          showToast("danger", data.error || "Failed to toggle rule.");
          return;
        }

        const enabled = data.enabled;
        const row = $(`#rule-row-${ruleId}`);
        const statusCol = $(`#rule-status-col-${ruleId}`);

        /* Update row opacity */
        row.toggleClass("opacity-50", !enabled);

        /* Update status badge */
        if (enabled) {
          statusCol.html(
            `<span class="badge bg-success-subtle text-success border border-success-subtle">
              <i class="bi bi-check-circle me-1"></i>Enabled
            </span>`
          );
          btn.attr("title", "Disable rule")
             .removeClass("btn-outline-success")
             .addClass("btn-outline-secondary")
             .html('<i class="bi bi-pause-fill"></i>');
        } else {
          statusCol.html(
            `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle">
              <i class="bi bi-pause-circle me-1"></i>Disabled
            </span>`
          );
          btn.attr("title", "Enable rule")
             .removeClass("btn-outline-secondary")
             .addClass("btn-outline-success")
             .html('<i class="bi bi-play-fill"></i>');
        }

        btn.data("enabled", enabled ? "true" : "false");
      },
      error: function () {
        showToast("danger", "Network error — could not toggle rule.");
      },
      complete: function () {
        btn.prop("disabled", false);
      },
    });
  });

  /* ------------------------------------------------------------------ */
  /* Delete Rule — Confirmation Modal                                     */
  /* ------------------------------------------------------------------ */

  let pendingDeleteRuleId = null;

  $(document).on("click", ".delete-rule-btn", function () {
    const btn = $(this);
    pendingDeleteRuleId = btn.data("rule-id");
    const ruleName = btn.data("rule-name") || `Rule #${pendingDeleteRuleId}`;

    $("#delete-rule-modal-text").text(
      `Are you sure you want to permanently delete "${ruleName}"?`
    );
    $("#delete-rule-form").attr("action", `/rules/${pendingDeleteRuleId}/delete`);

    const modal = new bootstrap.Modal(document.getElementById("deleteRuleModal"));
    modal.show();
  });

  /* ------------------------------------------------------------------ */
  /* Auto-dismiss Bootstrap toasts rendered server-side via flash()      */
  /* ------------------------------------------------------------------ */

  $(".toast").each(function () {
    const toast = new bootstrap.Toast(this, { delay: 4000 });
    toast.show();
  });

  /* ------------------------------------------------------------------ */
  /* Helper: show a temporary toast notification                          */
  /* ------------------------------------------------------------------ */

  /**
   * Displays a Bootstrap toast message.
   *
   * @param {string} type  - Bootstrap colour variant ('success', 'danger', etc.)
   * @param {string} text  - Message body text
   */
  function showToast(type, text) {
    const id = `toast-${Date.now()}`;
    const icon = type === "success" ? "check-circle" : "exclamation-triangle";
    const html = `
      <div id="${id}" class="toast align-items-center text-bg-${type} border-0"
           role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body">
            <i class="bi bi-${icon} me-2"></i>${text}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto"
                  data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>`;

    let container = $("#toast-container");
    if (!container.length) {
      container = $(
        '<div id="toast-container" class="position-fixed bottom-0 end-0 p-3" style="z-index:1100;"></div>'
      ).appendTo("body");
    }
    const el = $(html).appendTo(container);
    const toast = new bootstrap.Toast(el[0], { delay: 4000 });
    toast.show();
    el[0].addEventListener("hidden.bs.toast", () => el.remove());
  }
});
