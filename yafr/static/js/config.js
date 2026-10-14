/**
 * YAFR Configuration View Client-Side Script.
 *
 * Handles alpha slider live previews, preset application via AJAX,
 * and reset-to-defaults confirmation.
 */
document.addEventListener("DOMContentLoaded", function () {

  // --- Alpha Slider Live Preview ---
  const visitAlphaSlider = document.getElementById("entries_visit_alpha");
  const visitAlphaBadge = document.getElementById("visit_alpha_badge");
  const visitPreviewText = document.getElementById("visit-preview-text");

  if (visitAlphaSlider) {
    visitAlphaSlider.addEventListener("input", function () {
      const val = parseFloat(this.value).toFixed(2);
      if (visitAlphaBadge) visitAlphaBadge.textContent = val;
      if (visitPreviewText) visitPreviewText.style.opacity = val;
    });
  }

  const deadAlphaSlider = document.getElementById("entries_dead_alpha");
  const deadAlphaBadge = document.getElementById("dead_alpha_badge");
  const deadPreviewText = document.getElementById("dead-preview-text");

  if (deadAlphaSlider) {
    deadAlphaSlider.addEventListener("input", function () {
      const val = parseFloat(this.value).toFixed(2);
      if (deadAlphaBadge) deadAlphaBadge.textContent = val;
      if (deadPreviewText) deadPreviewText.style.opacity = val;
    });
  }

  // --- Quick Preset Buttons (AJAX) ---
  document.querySelectorAll(".btn-apply-preset").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const preset = this.dataset.preset;
      const originalHtml = this.innerHTML;
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Applying...';

      $.ajax({
        url: "/api/config/preset",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ preset: preset }),
        success: function (data) {
          if (data.success) {
            showToast("Preset '" + preset + "' applied. Reloading...", "success");
            setTimeout(function () { location.reload(); }, 600);
          } else {
            showToast(data.error || "Failed to apply preset.", "danger");
            btn.disabled = false;
            btn.innerHTML = originalHtml;
          }
        },
        error: function () {
          showToast("Network error while applying preset.", "danger");
          btn.disabled = false;
          btn.innerHTML = originalHtml;
        }
      });
    });
  });

  // --- Reset to Defaults (AJAX) ---
  const confirmResetBtn = document.getElementById("confirm-reset-btn");
  if (confirmResetBtn) {
    confirmResetBtn.addEventListener("click", function () {
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Resetting...';

      $.ajax({
        url: "/api/config/reset",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({}),
        success: function (data) {
          if (data.success) {
            showToast("Defaults restored. Reloading...", "success");
            setTimeout(function () { location.reload(); }, 600);
          } else {
            showToast(data.error || "Failed to reset.", "danger");
            confirmResetBtn.disabled = false;
            confirmResetBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise me-1"></i>Confirm Reset';
          }
        },
        error: function () {
          showToast("Network error while resetting.", "danger");
          confirmResetBtn.disabled = false;
          confirmResetBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise me-1"></i>Confirm Reset';
        }
      });
    });
  }

  // --- Toast Helper ---
  function showToast(message, type) {
    const toastEl = document.getElementById("config-toast");
    const toastBody = document.getElementById("config-toast-body");
    if (!toastEl || !toastBody) return;

    toastBody.textContent = message;
    toastEl.className = "toast align-items-center text-white border-0 shadow bg-" + (type || "success");
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
  }

});
