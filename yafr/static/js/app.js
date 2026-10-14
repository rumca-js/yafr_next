/**
 * YAFR Client-Side Application Script
 */
document.addEventListener("DOMContentLoaded", function () {
  // 1. Theme Toggle (Light / Dark)
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  const themeIcon = document.getElementById("theme-icon");
  const themeText = document.getElementById("theme-text");
  const htmlElement = document.documentElement;

  // Read saved theme from localStorage or default to light
  const savedTheme = localStorage.getItem("yafr-theme") || "light";
  setTheme(savedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", function () {
      const currentTheme = htmlElement.getAttribute("data-bs-theme") || "light";
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      setTheme(newTheme);
    });
  }

  function setTheme(theme) {
    htmlElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem("yafr-theme", theme);

    if (themeIcon && themeText) {
      if (theme === "dark") {
        themeIcon.className = "bi bi-sun me-1";
        themeText.textContent = "Light";
      } else {
        themeIcon.className = "bi bi-moon-stars me-1";
        themeText.textContent = "Dark";
      }
    }
  }

  // 2. Network Status Monitor (Online / Offline)
  const networkBadge = document.getElementById("network-badge");

  function updateNetworkStatus() {
    if (!networkBadge) return;

    if (navigator.onLine) {
      networkBadge.className = "badge bg-success-subtle text-success border border-success-subtle px-2 py-1 rounded-pill";
      networkBadge.innerHTML = '<i class="bi bi-wifi me-1"></i>Online';
      networkBadge.title = "Network available";
    } else {
      networkBadge.className = "badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1 rounded-pill";
      networkBadge.innerHTML = '<i class="bi bi-wifi-off me-1"></i>Offline';
      networkBadge.title = "Running in offline mode (local search active)";
    }
  }

  window.addEventListener("online", updateNetworkStatus);
  window.addEventListener("offline", updateNetworkStatus);
  updateNetworkStatus();
});
