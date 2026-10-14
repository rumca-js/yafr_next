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

  // 3. Remote WebTools Server Status Monitor
  const webtoolsBadge = document.getElementById("webtools-badge");

  function updateWebToolsStatus() {
    if (!webtoolsBadge) return;

    if (!navigator.onLine) {
      if (!webtoolsBadge.classList.contains("d-none")) {
        webtoolsBadge.className = "badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1 rounded-pill";
        webtoolsBadge.innerHTML = '<i class="bi bi-hdd-network me-1"></i>WebTools (Offline)';
        webtoolsBadge.title = "Client network is offline";
      }
      return;
    }

    fetch("/api/config/webtools-status")
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.configured) {
          webtoolsBadge.classList.add("d-none");
          return;
        }

        webtoolsBadge.classList.remove("d-none");
        if (data.online) {
          webtoolsBadge.className = "badge bg-success-subtle text-success border border-success-subtle px-2 py-1 rounded-pill";
          webtoolsBadge.innerHTML = '<i class="bi bi-hdd-network me-1"></i>WebTools';
          webtoolsBadge.title = "Remote WebTools server is online (" + data.url + ")";
        } else {
          webtoolsBadge.className = "badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1 rounded-pill";
          webtoolsBadge.innerHTML = '<i class="bi bi-hdd-network me-1"></i>WebTools Offline';
          webtoolsBadge.title = "Remote WebTools server is unreachable (" + data.url + "). Falling back to local BaseUrl.";
        }
      })
      .catch(function () {
        // Silently catch to avoid noisy console errors on transient network issues
      });
  }

  updateWebToolsStatus();
  window.addEventListener("online", updateWebToolsStatus);
});
