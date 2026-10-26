/**
 * YAFR Core Utility Library (utils.js)
 *
 * Lightweight, dependency-free utility functions for HTML escaping,
 * string sanitization, and common client-side helpers.
 *
 * Included in the document <head> so utilities are immediately
 * accessible to all page scripts and components without waiting
 * for full DOM parsing.
 */
(function (global) {
  'use strict';

  var YafrUtils = {
    /**
     * Safely escapes HTML special characters to prevent XSS injection.
     * @param {string|any} str - Input text to escape
     * @returns {string} Escaped HTML string
     */
    escapeHtml: function (str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    },

    /**
     * Formats an integer or float with locale thousands separators.
     * @param {number|string} val - Number to format
     * @returns {string} Formatted number string
     */
    formatNumber: function (val) {
      if (val === null || val === undefined || isNaN(val)) return '0';
      return Number(val).toLocaleString();
    },

    /**
     * Truncates text with optional ellipsis.
     * @param {string} str - Text to truncate
     * @param {number} maxLen - Maximum character length
     * @returns {string} Truncated string
     */
    truncate: function (str, maxLen) {
      if (!str) return '';
      maxLen = maxLen || 100;
      return str.length > maxLen ? str.slice(0, maxLen) + '...' : str;
    }
  };

  // Expose on YafrUtils namespace and top-level global for convenience
  global.YafrUtils = YafrUtils;
  if (!global.escapeHtml) {
    global.escapeHtml = YafrUtils.escapeHtml;
  }
})(typeof window !== 'undefined' ? window : this);
