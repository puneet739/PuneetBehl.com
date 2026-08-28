(function () {
  document.documentElement.classList.add('js');

  // Scroll progress bar
  var bar = document.getElementById('progress');
  if (bar) {
    var onScroll = function () {
      var h = document.documentElement;
      var d = h.scrollHeight - h.clientHeight;
      bar.style.width = (d > 0 ? (h.scrollTop / d) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Reveal on scroll
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealables = document.querySelectorAll('main > section, main > div, main figure');
  if (reduce || !('IntersectionObserver' in window)) {
    revealables.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.04 });
    revealables.forEach(function (el, i) {
      el.classList.add('reveal');
      el.style.animationDelay = Math.min(i, 5) * 70 + 'ms';
      io.observe(el);
    });
  }

  // Work filter
  var filterBtns = document.querySelectorAll('.filter-btn');
  var cards = document.querySelectorAll('.work-card');
  if (filterBtns.length && cards.length) {
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-filter');
        filterBtns.forEach(function (b) {
          b.classList.toggle('is-active', b === btn);
          b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
        });
        cards.forEach(function (c) {
          var show = f === 'All' || c.getAttribute('data-type') === f;
          c.classList.toggle('hide', !show);
        });
      });
    });
  }

  // Inline form submit. Falls back to a normal navigation on any failure, so a
  // broken fetch can never swallow a submission.
  document.querySelectorAll('form[data-ajax]').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var fd = new FormData(form);
      fetch(form.action, { method: 'POST', body: fd, redirect: 'follow' })
        .then(function (r) { window.location.href = r.url || form.action; })
        .catch(function () { form.submit(); });
    });
  });
})();
