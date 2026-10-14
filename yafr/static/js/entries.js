/**
 * YAFR Entries Interactive Client-Side Logic.
 * 
 * Handles AJAX interactions for voting, bookmarks, read later,
 * visit tracking, and dynamic alpha updates without page reload.
 */

$(document).ready(function () {

  // 1. Visit Tracking on Link Click
  $(document).on('click', '.entry-link', function () {
    const entryId = $(this).data('id');
    const card = $('#entry-card-' + entryId);

    // Dynamically mark as visited in UI
    if (card.length && !card.hasClass('entry-bookmarked') && !card.hasClass('entry-voted')) {
      card.addClass('entry-visited');
    }

    // Inform server of visit in background
    if (entryId) {
      $.ajax({
        url: '/api/entries/' + entryId + '/visit',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({})
      });
    }
  });

  // 2. Bookmark Toggle
  $(document).on('click', '.btn-bookmark', function (e) {
    e.preventDefault();
    e.stopPropagation();

    const btn = $(this);
    const entryId = btn.data('id');
    const card = $('#entry-card-' + entryId);

    if (!entryId) return;

    btn.prop('disabled', true);

    $.ajax({
      url: '/api/entries/' + entryId + '/bookmark',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({}),
      success: function (res) {
        if (res.success && res.data) {
          const isBookmarked = res.data.bookmarked;
          const icon = btn.find('i');

          if (isBookmarked) {
            icon.removeClass('bi-bookmark').addClass('bi-bookmark-fill');
            card.addClass('entry-bookmarked');
          } else {
            icon.removeClass('bi-bookmark-fill').addClass('bi-bookmark');
            card.removeClass('entry-bookmarked');
          }
        }
      },
      error: function (xhr) {
        console.error('Bookmark toggle failed:', xhr.responseText);
      },
      complete: function () {
        btn.prop('disabled', false);
      }
    });
  });

  // 3. Set Vote as a Number (-100 to 100)
  $(document).on('click', '.btn-set-vote', function (e) {
    e.preventDefault();
    e.stopPropagation();

    const btn = $(this);
    const entryId = btn.data('id');
    const scoreBadge = $('.score-badge[data-id="' + entryId + '"]');
    const currentVote = btn.data('current') !== undefined ? btn.data('current') : (scoreBadge.text().trim() || 0);

    if (!entryId) return;

    const userInput = prompt('Set vote rating (-100 to 100):', currentVote);
    if (userInput === null) return; // User cancelled

    const targetVote = parseInt(userInput.trim(), 10);
    if (isNaN(targetVote) || targetVote < -100 || targetVote > 100) {
      alert('Please enter a valid integer between -100 and 100.');
      return;
    }

    const card = $('#entry-card-' + entryId);
    btn.prop('disabled', true);

    $.ajax({
      url: '/api/entries/' + entryId + '/vote',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ vote: targetVote }),
      success: function (res) {
        if (res.success && res.data) {
          const newVotes = res.data.page_rating_votes;
          scoreBadge.text(newVotes);
          btn.data('current', newVotes);

          if (newVotes !== 0) {
            card.addClass('entry-voted');
          } else {
            card.removeClass('entry-voted');
          }
        }
      },
      error: function (xhr) {
        alert('Failed to set vote: ' + (xhr.responseJSON?.error || xhr.statusText));
      },
      complete: function () {
        btn.prop('disabled', false);
      }
    });
  });

  // 4. Read Later Toggle
  $(document).on('click', '.btn-read-later', function (e) {
    e.preventDefault();
    e.stopPropagation();

    const btn = $(this);
    const entryId = btn.data('id');

    if (!entryId) return;

    btn.prop('disabled', true);

    $.ajax({
      url: '/api/entries/' + entryId + '/read-later',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({}),
      success: function (res) {
        if (res.success && res.data) {
          const isSaved = res.data.read_later;
          const icon = btn.find('i');

          if (isSaved) {
            btn.addClass('active');
            icon.removeClass('bi-clock').addClass('bi-clock-fill');
          } else {
            btn.removeClass('active');
            icon.removeClass('bi-clock-fill').addClass('bi-clock');
          }
        }
      },
      error: function (xhr) {
        console.error('Read later toggle failed:', xhr.responseText);
      },
      complete: function () {
        btn.prop('disabled', false);
      }
    });
  });

});
