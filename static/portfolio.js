(() => {
  const root = document.querySelector('.public-site');
  if (!root) return;
  const fonts = ['modern', 'rounded', 'editorial', 'mono', 'studio'];
  const activeFont = () => { for (const font of fonts) { if (root.classList.contains('font-' + font)) return font; } return root.dataset.defaultFont; };
  const syncFontButtons = () => {
    const active = activeFont();
    document.querySelectorAll('.font-option').forEach(btn => {
      const mark = btn.getAttribute('data-font') !== 'default' && btn.getAttribute('data-font') === active;
      btn.classList.toggle('selected', mark);
      let tick = btn.querySelector('.font-check');
      if (mark && !tick) { tick = document.createElement('span'); tick.className = 'font-check'; tick.textContent = '\u2713'; btn.appendChild(tick); }
      if (!mark && tick) tick.remove();
    });
  };
  try {
    const saved = localStorage.getItem('hana-font');
    if (fonts.includes(saved)) { fonts.forEach(font => root.classList.remove('font-' + font)); root.classList.add('font-' + saved); }
  } catch {}
  syncFontButtons();
  document.querySelectorAll('[data-font]').forEach(button => button.addEventListener('click', () => {
    const value = button.getAttribute('data-font');
    if (value !== 'default' && !fonts.includes(value)) return;
    fonts.forEach(font => root.classList.remove('font-' + font));
    root.classList.add('font-' + (value === 'default' ? root.dataset.defaultFont : value));
    try { value === 'default' ? localStorage.removeItem('hana-font') : localStorage.setItem('hana-font', value); } catch {}
    syncFontButtons();
    document.querySelectorAll('.font-options').forEach(panel => panel.hidden = true);
  }));
  document.querySelectorAll('[data-toggle]').forEach(button => button.addEventListener('click', () => {
    const panel = document.querySelector('[data-panel="' + button.dataset.toggle + '"]');
    if (!panel) return;
    const opening = panel.hidden;
    document.querySelectorAll('[data-panel]').forEach(other => other.hidden = true);
    document.querySelectorAll('[data-toggle]').forEach(other => other.setAttribute('aria-expanded', 'false'));
    panel.hidden = !opening;
    button.setAttribute('aria-expanded', String(opening));
  }));
  const drawer = document.querySelector('.site-sidebar');
  const scrim = document.querySelector('.mobile-scrim');
  const mobileButton = document.querySelector('[data-menu]');
  const closeMenu = () => { drawer?.classList.remove('sidebar-open'); if (scrim) scrim.hidden = true; mobileButton?.setAttribute('aria-expanded', 'false'); };
  mobileButton?.addEventListener('click', () => { const open = !drawer?.classList.contains('sidebar-open'); drawer?.classList.toggle('sidebar-open', open); if (scrim) scrim.hidden = !open; mobileButton.setAttribute('aria-expanded', String(open)); });
  scrim?.addEventListener('click', closeMenu);
  document.querySelectorAll('.sidebar-navigation a').forEach(link => link.addEventListener('click', closeMenu));
  const cookie = document.querySelector('.cookie-card');
  if (cookie) {
    try { cookie.hidden = !!localStorage.getItem('hana-cookie-choice'); } catch { cookie.hidden = false; }
    document.querySelectorAll('[data-cookie]').forEach(button => button.addEventListener('click', () => {
      cookie.hidden = true;
      try { localStorage.setItem('hana-cookie-choice', button.dataset.cookie); } catch {}
    }));
  }
  // Galleries: open a tile full size, walk through the set, close again.
  const tiles = Array.from(document.querySelectorAll('[data-gallery-open]'));
  if (tiles.length) {
    let overlay = null;
    let index = 0;
    const groupOf = tile => Array.from(tile.closest('[data-gallery]').querySelectorAll('[data-gallery-open]'));
    let group = [];
    const show = () => {
      if (!overlay) return;
      const tile = group[index];
      overlay.querySelector('img').src = tile.dataset.gallerySrc;
      overlay.querySelector('img').alt = tile.querySelector('img')?.alt || '';
      const caption = overlay.querySelector('.lightbox-caption');
      caption.textContent = tile.dataset.galleryCaption || '';
      caption.hidden = !tile.dataset.galleryCaption;
      overlay.querySelectorAll('.lightbox-step').forEach(button => { button.hidden = group.length < 2; });
    };
    const close = () => {
      if (!overlay) return;
      const opener = group[index];
      overlay.remove();
      overlay = null;
      document.body.style.removeProperty('overflow');
      opener?.focus();
    };
    const step = direction => { index = (index + direction + group.length) % group.length; show(); };
    const open = tile => {
      group = groupOf(tile);
      index = group.indexOf(tile);
      overlay = document.createElement('div');
      overlay.className = 'lightbox';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-label', 'Image viewer');
      overlay.innerHTML =
        '<button type="button" class="lightbox-close" aria-label="Close image">\u00d7</button>' +
        '<button type="button" class="lightbox-step prev" aria-label="Previous image">\u2039</button>' +
        '<img alt=""><p class="lightbox-caption"></p>' +
        '<button type="button" class="lightbox-step next" aria-label="Next image">\u203a</button>';
      overlay.addEventListener('click', event => {
        if (event.target === overlay) close();
        else if (event.target.closest('.lightbox-close')) close();
        else if (event.target.closest('.prev')) step(-1);
        else if (event.target.closest('.next')) step(1);
      });
      document.body.appendChild(overlay);
      document.body.style.overflow = 'hidden';
      show();
      overlay.querySelector('.lightbox-close').focus();
    };
    tiles.forEach(tile => tile.addEventListener('click', () => open(tile)));
    document.addEventListener('keydown', event => {
      if (!overlay) return;
      if (event.key === 'Escape') { event.preventDefault(); close(); }
      else if (event.key === 'ArrowLeft') step(-1);
      else if (event.key === 'ArrowRight') step(1);
    });
  }
  // Embeds stay as a local poster until the visitor asks to play.
  document.querySelectorAll('[data-embed-frame]').forEach(figure => {
    const poster = figure.querySelector('.embed-poster');
    poster?.addEventListener('click', () => {
      const frame = document.createElement('iframe');
      frame.src = figure.dataset.embedFrame;
      frame.title = figure.dataset.embedTitle || 'Video';
      frame.loading = 'lazy';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen';
      frame.setAttribute('allowfullscreen', '');
      poster.replaceWith(frame);
    });
  });
  const contact = document.querySelector('[data-contact]');
  if (contact) {
    const nameInput = contact.querySelector('[data-contact-name]');
    const bodyInput = contact.querySelector('[data-contact-body]');
    const sendButton = contact.querySelector('[data-contact-send]');
    const statusLine = contact.querySelector('[data-contact-status]');
    const setStatus = (text, isError) => {
      if (!statusLine) return;
      statusLine.textContent = text || '';
      statusLine.classList.toggle('error', !!isError);
      statusLine.hidden = !text;
    };
    contact.addEventListener('submit', async event => {
      event.preventDefault();
      const body = (bodyInput?.value || '').trim();
      if (body.length < 2) { setStatus('Please write at least 2 characters.', true); bodyInput?.focus(); return; }
      if (sendButton) sendButton.disabled = true;
      setStatus('');
      try {
        const response = await fetch('/api/messages', {
          method: 'POST',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: (nameInput?.value || '').trim(), body }),
        });
        let data = {};
        try { data = await response.json(); } catch {}
        if (!response.ok) throw new Error(typeof data.error === 'string' ? data.error : 'Your message could not be sent.');
        if (nameInput) nameInput.value = '';
        if (bodyInput) bodyInput.value = '';
        setStatus('Sent!', false);
      } catch (issue) {
        setStatus(issue instanceof Error ? issue.message : 'Your message could not be sent.', true);
      } finally {
        if (sendButton) sendButton.disabled = false;
      }
    });
  }
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && 'IntersectionObserver' in window && !root.classList.contains('motion-off')) {
    root.classList.add('reveal-enabled');
    const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); } }), { threshold: .08, rootMargin: '0px 0px -28px 0px' });
    root.querySelectorAll('.reveal').forEach(element => observer.observe(element));
  }
})();
