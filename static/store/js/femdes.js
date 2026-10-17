// FemDes progressive storefront enhancements.
// Everything here is additive: forms, links and navigation work without it.
// UI state for the mega menu, sort/density toolbar and live search uses
// Alpine.js (loaded deferred); motion uses GSAP/ScrollTrigger, Lenis, Swiper.
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  var root = document.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasGsap = typeof window.gsap !== 'undefined';
  var lenis = null;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  // ---- Quantity steppers (event delegation on data-* hooks) ----
  function readBound(input, attr, fallback) {
    var raw = input.getAttribute(attr);
    if (raw === null || raw === '') return fallback;
    var n = Number(raw);
    return isNaN(n) ? fallback : n;
  }

  function clamp(val, min, max) {
    var n = Number(val);
    if (val === '' || val === null || isNaN(n)) return min;
    n = Math.round(n);
    if (n < min) return min;
    if (n > max) return max;
    return n;
  }

  function markDirty(input) {
    var form = input.closest('form[data-qty-form]');
    if (!form) return;
    form.classList.add('is-dirty');
    // Cart drawer: no Update button, so submit shortly after the last change.
    if (form.closest('.offcanvas')) {
      clearTimeout(form._fdTimer);
      form._fdTimer = setTimeout(function () { form.submit(); }, 450);
    }
  }

  function handleStep(e) {
    var btn = e.target.closest('[data-quantity-stepper] [data-action]');
    if (!btn) return;
    e.preventDefault();
    var wrapper = btn.closest('[data-quantity-stepper]');
    var input = wrapper && wrapper.querySelector('input[type="number"]');
    if (!input) return;
    var min = readBound(input, 'min', 1);
    var max = readBound(input, 'max', 99);
    var delta = btn.getAttribute('data-action') === 'inc' ? 1 : -1;
    var next = clamp(clamp(input.value, min, max) + delta, min, max);
    if (String(next) !== String(input.value)) { input.value = next; markDirty(input); }
  }

  function handleQtyChange(e) {
    var input = e.target;
    if (!input.matches || !input.matches('.qty-input')) return;
    input.value = clamp(input.value, readBound(input, 'min', 1), readBound(input, 'max', 99));
    markDirty(input);
  }

  // ---- Search popup: focus ownership + live results ----
  var activeSearchTrigger = null;

  function searchPopup() { return document.querySelector('.search-popup'); }
  function searchVisible() {
    var p = searchPopup();
    return !!(p && p.classList.contains('is-visible'));
  }

  function openSearchFocus() {
    if (!searchVisible()) return;
    if (lenis) lenis.stop();
    var q = document.querySelector('.search-popup input[name="q"]');
    if (q) q.focus();
  }

  function closeSearch() {
    var p = searchPopup();
    if (p) p.classList.remove('is-visible');
    if (lenis) lenis.start();
    var t = activeSearchTrigger;
    activeSearchTrigger = null;
    if (t) t.focus();
  }

  function setupSearch() {
    document.querySelectorAll('.search-button').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        activeSearchTrigger = btn;
        // Kaira script.min.js only toggles .is-visible for triggers inside
        // .navbar; the header utility row is outside it, so open it here.
        var p = searchPopup();
        if (p && !btn.closest('.navbar')) p.classList.add('is-visible');
        setTimeout(openSearchFocus, 60);
      });
    });
    document.querySelectorAll('.btn-close-search').forEach(function (btn) {
      btn.addEventListener('click', function (e) { e.preventDefault(); closeSearch(); });
    });
    var popup = searchPopup();
    if (popup) {
      popup.addEventListener('click', function (e) { if (e.target === popup) closeSearch(); });
    }
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && searchVisible()) closeSearch();
    });
    setupLiveSearch();
  }

  // Live results reuse the server-rendered shop page: fetch /shop/?q=…,
  // parse it, and lift the first few product cards into the popup.
  function setupLiveSearch() {
    var form = document.querySelector('[data-live-search]');
    var results = document.querySelector('[data-search-results]');
    var status = document.querySelector('[data-search-status]');
    if (!form || !results || typeof window.fetch === 'undefined') return;
    var input = form.querySelector('input[name="q"]');
    var url = form.getAttribute('data-live-search');
    var timer = null;
    var seq = 0;

    function render(doc, q, mine) {
      if (mine !== seq) return;
      var cards = Array.prototype.slice.call(doc.querySelectorAll('.product-item')).slice(0, 4);
      results.innerHTML = '';
      cards.forEach(function (card) { results.appendChild(card.cloneNode(true)); });
      if (status) {
        status.textContent = cards.length
          ? 'Top matches for “' + q + '” — press Enter for all'
          : 'No matches for “' + q + '”';
      }
    }

    input.addEventListener('input', function () {
      var q = input.value.trim();
      clearTimeout(timer);
      if (q.length < 2) { results.innerHTML = ''; if (status) status.textContent = ''; return; }
      timer = setTimeout(function () {
        var mine = ++seq;
        if (status) status.textContent = 'Searching…';
        fetch(url + '?q=' + encodeURIComponent(q), { headers: { 'X-Requested-With': 'fetch' } })
          .then(function (r) { return r.text(); })
          .then(function (html) { render(new DOMParser().parseFromString(html, 'text/html'), q, mine); })
          .catch(function () { if (status && mine === seq) status.textContent = ''; });
      }, 220);
    });
  }

  // ---- Toasts for Django messages ----
  function dismissToast(toast) {
    if (!toast || toast.classList.contains('is-leaving')) return;
    toast.classList.add('is-leaving');
    setTimeout(function () { toast.remove(); }, 400);
  }

  function setupToasts() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-toast-close]');
      if (btn) dismissToast(btn.closest('[data-toast]'));
    });
    document.querySelectorAll('[data-toast]').forEach(function (toast, i) {
      setTimeout(function () { dismissToast(toast); }, 5500 + i * 600);
    });
  }

  // ---- Header state, progress bar, back-to-top ----
  function setupChrome() {
    var header = document.querySelector('[data-header]');
    var bar = document.querySelector('.fd-progress');
    var top = document.querySelector('[data-to-top]');
    var ticking = false;

    if (header) {
      root.style.setProperty('--fd-header-h', header.offsetHeight + 'px');
    }

    function update() {
      ticking = false;
      var y = window.scrollY || window.pageYOffset;
      var h = document.documentElement.scrollHeight - window.innerHeight;
      if (header) header.classList.toggle('is-scrolled', y > 24);
      if (bar) bar.style.transform = 'scaleX(' + (h > 0 ? Math.min(y / h, 1) : 0) + ')';
      if (top) top.classList.toggle('is-visible', y > window.innerHeight);
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();

    if (top) {
      top.addEventListener('click', function () {
        if (lenis) lenis.scrollTo(0, { duration: 1.4 });
        else window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
      });
    }
    ['show.bs.offcanvas', 'show.bs.modal'].forEach(function (ev) {
      document.addEventListener(ev, function () { if (lenis) lenis.stop(); });
    });
    ['hidden.bs.offcanvas', 'hidden.bs.modal'].forEach(function (ev) {
      document.addEventListener(ev, function () { if (lenis) lenis.start(); });
    });
  }

  // ---- Smooth scrolling (Lenis) ----
  function setupLenis() {
    if (reduceMotion || typeof window.Lenis === 'undefined') return;
    lenis = new window.Lenis({ duration: 1.1, smoothWheel: true, anchors: false });
    document.querySelectorAll('.offcanvas, .search-popup, .dropdown-menu, .fd-mega').forEach(function (el) {
      el.setAttribute('data-lenis-prevent', '');
    });
    if (hasGsap && window.ScrollTrigger) {
      lenis.on('scroll', window.ScrollTrigger.update);
      window.gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
      window.gsap.ticker.lagSmoothing(0);
    } else {
      var raf = function (t) { lenis.raf(t); requestAnimationFrame(raf); };
      requestAnimationFrame(raf);
    }
  }

  // ---- Hero carousel ----
  function splitWords(el) {
    if (!el || el.dataset.splitDone) return;
    el.dataset.splitDone = '1';
    el.setAttribute('aria-label', el.textContent.trim());
    var html = '';
    el.childNodes.forEach(function (node) {
      var isEm = node.nodeType === 1 && node.tagName === 'EM';
      node.textContent.split(/\s+/).filter(Boolean).forEach(function (w) {
        var word = w.replace(/&/g, '&amp;').replace(/</g, '&lt;');
        html += '<span class="fd-split-line" aria-hidden="true"><span>' +
          (isEm ? '<em>' + word + '</em>' : word) + '</span></span> ';
      });
    });
    el.innerHTML = html;
  }

  function animateHeroSlide(slide) {
    if (!hasGsap || reduceMotion || !slide) return;
    var text = slide.querySelector('[data-hero-text]');
    if (!text) return;
    var tl = window.gsap.timeline({ defaults: { ease: 'expo.out' } });
    tl.fromTo(text.querySelectorAll('.fd-split-line > span'), { yPercent: 110 }, { yPercent: 0, duration: 1.1, stagger: 0.05 }, 0);
    tl.fromTo(text.querySelectorAll('.fd-eyebrow, p, .btn, .fd-hero-trust, .d-flex'),
      { y: 18, opacity: 0 }, { y: 0, opacity: 1, duration: 0.9, stagger: 0.07 }, 0.3);
  }

  function setupHero() {
    var el = document.getElementById('hero-carousel');
    if (!el) return;
    el.querySelectorAll('[data-split]').forEach(splitWords);
    var slides = el.querySelectorAll('.swiper-slide');
    if (typeof window.Swiper === 'undefined' || slides.length < 2) {
      animateHeroSlide(slides[0]);
      return;
    }
    new window.Swiper(el, {
      effect: 'fade',
      fadeEffect: { crossFade: true },
      speed: 1000,
      loop: true,
      autoplay: reduceMotion ? false : { delay: 6000, disableOnInteraction: false, pauseOnMouseEnter: true },
      pagination: { el: el.querySelector('.fd-hero-pagination'), clickable: true },
      a11y: { enabled: true },
      on: {
        init: function (s) { animateHeroSlide(s.slides[s.activeIndex]); },
        slideChangeTransitionStart: function (s) { animateHeroSlide(s.slides[s.activeIndex]); }
      }
    });
  }

  // ---- Scroll reveals, parallax ----
  function setupReveals() {
    if (!hasGsap || reduceMotion || !window.ScrollTrigger) {
      root.classList.remove('fd-js');
      return;
    }
    var gsap = window.gsap;
    var ST = window.ScrollTrigger;
    gsap.registerPlugin(ST);

    var items = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
    var clips = items.filter(function (el) { return el.getAttribute('data-reveal') === 'clip'; });
    var rest = items.filter(function (el) { return el.getAttribute('data-reveal') !== 'clip'; });

    ST.batch(rest, {
      start: 'top 90%',
      once: true,
      onEnter: function (batch) {
        gsap.to(batch, { opacity: 1, y: 0, scale: 1, duration: 1, ease: 'expo.out', stagger: 0.08, overwrite: true });
      }
    });
    clips.forEach(function (el) {
      gsap.to(el, { clipPath: 'inset(0% 0 0 0)', duration: 1.4, ease: 'expo.inOut', scrollTrigger: { trigger: el, start: 'top 85%', once: true } });
    });
    document.querySelectorAll('[data-parallax]').forEach(function (el) {
      var amount = Number(el.getAttribute('data-parallax')) || 4;
      gsap.fromTo(el, { yPercent: -amount, scale: 1 + amount / 50 }, {
        yPercent: amount, scale: 1 + amount / 50, ease: 'none',
        scrollTrigger: { trigger: el.parentNode, start: 'top bottom', end: 'bottom top', scrub: true }
      });
    });
    window.addEventListener('load', function () { ST.refresh(); });
  }

  // ---- Product gallery: whole-photo frame, full-screen viewer, thumbnail sync ----
  var pswpLoading = null;
  function loadPhotoSwipe(base) {
    if (pswpLoading) return pswpLoading;
    pswpLoading = new Promise(function (resolve, reject) {
      var css = document.createElement('link');
      css.rel = 'stylesheet'; css.href = base + 'photoswipe.css';
      document.head.appendChild(css);
      var files = ['photoswipe.umd.min.js', 'photoswipe-lightbox.umd.min.js'], done = 0;
      files.forEach(function (f) {
        var s = document.createElement('script');
        s.src = base + f;
        s.onload = function () { if (++done === files.length) resolve(); };
        s.onerror = function () { pswpLoading = null; reject(); };
        document.head.appendChild(s);
      });
    });
    return pswpLoading;
  }
  function photoSize(img) {
    return new Promise(function (resolve) {
      if (img.complete && img.naturalWidth) return resolve({ w: img.naturalWidth, h: img.naturalHeight });
      var probe = new Image();
      probe.onload = function () { resolve({ w: probe.naturalWidth, h: probe.naturalHeight }); };
      probe.onerror = function () { resolve(null); };
      probe.src = img.currentSrc || img.src;
    });
  }
  function setupGallery() {
    document.querySelectorAll('.product-gallery').forEach(function (gallery) {
      var inner = gallery.querySelector('.carousel-inner');
      var imgs = [].slice.call(gallery.querySelectorAll('.carousel-item img'));
      // Frame follows the photos' shape (square to 3:4) so nothing is cropped.
      if (inner && imgs[0]) {
        var fit = function () {
          if (!imgs[0].naturalWidth) return;
          var r = Math.min(1, Math.max(0.75, imgs[0].naturalWidth / imgs[0].naturalHeight));
          inner.style.setProperty('aspect-ratio', String(r), 'important');
        };
        if (imgs[0].complete) fit(); else imgs[0].addEventListener('load', fit);
      }
      var base = gallery.getAttribute('data-pswp');
      if (base && inner && imgs.length) {
        var opening = false;
        var open = function () {
          if (opening) return;
          opening = true;
          var items = [].slice.call(gallery.querySelectorAll('.carousel-item'));
          var start = Math.max(0, items.findIndex(function (it) { return it.classList.contains('active'); }));
          Promise.all([loadPhotoSwipe(base)].concat(imgs.map(photoSize))).then(function (res) {
            var sizes = res.slice(1);
            var lightbox = new window.PhotoSwipeLightbox({
              dataSource: imgs.map(function (img, i) {
                var s = sizes[i] || { w: 1200, h: 1500 };
                return { src: img.currentSrc || img.src, width: s.w, height: s.h, alt: img.alt };
              }),
              pswpModule: window.PhotoSwipe,
              showHideAnimationType: 'fade',
              bgOpacity: 1,
              wheelToZoom: true,
              secondaryZoomLevel: 2,
              maxZoomLevel: 4,
              padding: { top: 56, bottom: imgs.length > 1 ? 104 : 56, left: 12, right: 12 },
              closeTitle: 'Close', zoomTitle: 'Zoom in or out',
              arrowPrevTitle: 'Previous photo', arrowNextTitle: 'Next photo',
              errorMsg: 'This photo could not be loaded.'
            });
            if (imgs.length > 1) {
              // Thumbnail strip along the bottom of the viewer.
              lightbox.on('uiRegister', function () {
                lightbox.pswp.ui.registerElement({
                  name: 'fd-thumbs', appendTo: 'root', order: 20,
                  onInit: function (el, pswp) {
                    el.className = 'pswp__fd-thumbs';
                    el.setAttribute('role', 'group'); el.setAttribute('aria-label', 'Photos');
                    var buttons = imgs.map(function (img, i) {
                      var b = document.createElement('button');
                      b.type = 'button'; b.className = 'pswp__fd-thumb';
                      b.setAttribute('aria-label', 'Photo ' + (i + 1));
                      var t = document.createElement('img'); t.src = img.currentSrc || img.src; t.alt = ''; t.loading = 'lazy';
                      b.appendChild(t);
                      b.addEventListener('click', function () { pswp.goTo(i); });
                      el.appendChild(b);
                      return b;
                    });
                    function mark() {
                      buttons.forEach(function (b, i) {
                        var on = i === pswp.currIndex;
                        b.classList.toggle('is-active', on);
                        if (on) { b.setAttribute('aria-current', 'true'); b.scrollIntoView({ block: 'nearest', inline: 'center' }); } else b.removeAttribute('aria-current');
                      });
                    }
                    pswp.on('change', mark); mark();
                  }
                });
              });
            }
            lightbox.on('close', function () {
              var idx = lightbox.pswp ? lightbox.pswp.currIndex : start;
              if (window.bootstrap && idx !== start) window.bootstrap.Carousel.getOrCreateInstance(gallery).to(idx);
            });
            lightbox.on('destroy', function () { opening = false; });
            lightbox.init();
            lightbox.loadAndOpen(start);
          }).catch(function () { opening = false; });
        };
        inner.addEventListener('click', open);
        var btn = gallery.querySelector('[data-gallery-open]');
        if (btn) btn.addEventListener('click', open);
      }
      gallery.addEventListener('slid.bs.carousel', function (e) {
        gallery.parentNode.querySelectorAll('[data-bs-slide-to]').forEach(function (t, i) {
          var on = i === e.to;
          t.classList.toggle('active', on);
          if (on) t.setAttribute('aria-current', 'true'); else t.removeAttribute('aria-current');
        });
      });
    });
  }

  // ---- PIN code → city + state (India Post data via /api/pincode/) ----
  function setupPinLookup() {
    document.querySelectorAll('input[data-pin-lookup]').forEach(function (pin) {
      var form = pin.form; if (!form) return;
      var city = form.querySelector('[name=city]'), state = form.querySelector('[name=state]');
      var hint = pin.parentNode.querySelector('[data-pin-hint]');
      var last = '', autoCity = '';
      function check() {
        var v = pin.value.replace(/\D/g, '');
        if (v.length !== 6 || v === last || !/^[1-9]/.test(v)) { if (v.length < 6 && hint) hint.textContent = ''; return; }
        last = v;
        if (hint) hint.textContent = 'Looking up…';
        fetch(pin.getAttribute('data-pin-lookup').replace('000000', v), { headers: { Accept: 'application/json' } })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d || !d.found) { if (hint) hint.textContent = 'We could not find this PIN code. Please check it.'; return; }
            if (city && d.city && (!city.value || city.value === autoCity)) { city.value = d.city; autoCity = d.city; city.dispatchEvent(new Event('input', { bubbles: true })); }
            if (state && d.state && state.value !== d.state) { state.value = d.state; state.dispatchEvent(new Event('change', { bubbles: true })); }
            if (hint) hint.textContent = 'Delivering to ' + [d.city, d.state].filter(Boolean).join(', ');
          })
          .catch(function () { if (hint) hint.textContent = ''; });
      }
      pin.addEventListener('input', check);
      pin.addEventListener('change', check);
      if (pin.value) check();
    });
  }

  // ---- Sticky mobile buy bar ----
  function setupStickyBuy() {
    var bar = document.querySelector('[data-sticky-buy]');
    var panel = document.querySelector('[data-buy-panel]');
    if (!bar || !panel || typeof window.IntersectionObserver === 'undefined') return;
    var cartForm = document.getElementById('pdp-cart-form');
    var watch = (cartForm && cartForm.querySelector('.fd-pdp-cart')) || panel;
    var io = new window.IntersectionObserver(function (entries) {
      var passed = !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0;
      bar.classList.toggle('is-visible', passed);
      bar.setAttribute('aria-hidden', passed ? 'false' : 'true');
      bar.querySelector('button').tabIndex = passed ? 0 : -1;
      document.body.classList.toggle('has-sticky-buy', passed);
    }, { threshold: 0 });
    io.observe(watch);
  }

  // ---- Sort select: submit on change (server GET; <noscript> keeps a button) ----
  function setupAutoSubmit() {
    document.querySelectorAll('form[data-auto-submit] select').forEach(function (sel) {
      sel.addEventListener('change', function () { sel.form.submit(); });
    });
  }

  // ---- GET filter forms: drop empty fields so URLs stay clean ----
  function setupStripEmpty() {
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (!form.matches || !form.matches('form[data-strip-empty]')) return;
      form.querySelectorAll('input[name], select[name]').forEach(function (el) {
        if ((el.type === 'number' || el.type === 'text' || el.tagName === 'SELECT') && el.value === '') el.disabled = true;
      });
    });
  }

  // ---- Submit feedback ----
  function setupSubmitFeedback() {
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (e.defaultPrevented || !form.matches || !form.matches('.add-to-cart-form, [data-fd-busy]')) return;
      var btn = form.querySelector('button[type="submit"]');
      if (btn) { btn.setAttribute('aria-busy', 'true'); btn.style.opacity = '0.7'; }
    });
  }

  // ---- Wishlist hearts: toggle without reload (form still works without JS) ----
  function setupWishlist() {
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (!form.matches || !form.matches('[data-wishlist]') || typeof window.fetch === 'undefined') return;
      e.preventDefault();
      var btn = form.querySelector('button');
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) {
          var action = form.getAttribute('action');
          document.querySelectorAll('form[data-wishlist][action="' + action + '"] button').forEach(function (b) {
            b.classList.toggle('is-saved', data.saved);
            b.setAttribute('aria-pressed', data.saved ? 'true' : 'false');
            var name = b.getAttribute('aria-label').replace(/^(Remove|Save) /, '').replace(/ (from|to) wishlist$/, '');
            b.setAttribute('aria-label', (data.saved ? 'Remove ' : 'Save ') + name + (data.saved ? ' from wishlist' : ' to wishlist'));
            var label = b.querySelector('span');
            if (label) label.textContent = data.saved ? 'Saved' : 'Add to Wishlist';
          });
          if (btn) { btn.classList.add('is-popping'); setTimeout(function () { btn.classList.remove('is-popping'); }, 250); }
          document.querySelectorAll('[data-wishlist-count]').forEach(function (el) {
            el.textContent = data.count;
            el.classList.toggle('d-none', !data.count);
          });
        })
        .catch(function () { form.submit(); });
    });
  }

  // ---- Shop "Load more": fetch the next page and append its cards ----
  function setupLoadMore() {
    document.addEventListener('click', function (e) {
      var link = e.target.closest('[data-load-more]');
      if (!link || typeof window.fetch === 'undefined') return;
      var grid = document.querySelector('[data-product-grid]');
      var pager = document.querySelector('[data-pager]');
      if (!grid || !pager) return;
      e.preventDefault();
      link.setAttribute('aria-busy', 'true');
      link.textContent = 'Loading\u2026';
      fetch(link.href, { headers: { 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.text(); })
        .then(function (html) {
          var doc = new DOMParser().parseFromString(html, 'text/html');
          var newGrid = doc.querySelector('[data-product-grid]');
          var newPager = doc.querySelector('[data-pager]');
          if (newGrid) {
            Array.prototype.slice.call(newGrid.children).forEach(function (col) {
              col.removeAttribute('data-reveal');
              grid.appendChild(col);
            });
          }
          if (newPager) {
            var prev = newPager.querySelector('[rel="prev"]');
            if (prev) prev.remove();
            pager.replaceWith(newPager);
          } else {
            pager.remove();
          }
          if (window.history && window.history.replaceState) window.history.replaceState(null, '', link.href);
        })
        .catch(function () { window.location.href = link.href; });
    });
  }

  // ---- Dialogs (size guide) + share ----
  function setupDialogs() {
    document.addEventListener('click', function (e) {
      var opener = e.target.closest('[data-open-dialog]');
      if (opener) {
        var dlg = document.getElementById(opener.getAttribute('data-open-dialog'));
        if (dlg && typeof dlg.showModal === 'function') {
          e.preventDefault();
          if (lenis) lenis.stop();
          dlg.showModal();
        }
        return;
      }
      var closer = e.target.closest('[data-close-dialog]');
      if (closer) {
        var d = closer.closest('dialog');
        if (d) d.close();
      }
    });
    document.querySelectorAll('dialog.fd-dialog').forEach(function (d) {
      d.addEventListener('close', function () { if (lenis) lenis.start(); });
      d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
    });
  }

  function setupShare() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-share]');
      if (btn) {
        var data = { title: btn.getAttribute('data-share-title'), url: btn.getAttribute('data-share-url') };
        if (navigator.share) {
          navigator.share(data).catch(function () {});
        } else {
          var fb = document.querySelector('[data-share-fallback]');
          if (fb) fb.hidden = !fb.hidden;
        }
        return;
      }
      var copy = e.target.closest('[data-copy-link]');
      if (copy && navigator.clipboard) {
        navigator.clipboard.writeText(copy.getAttribute('data-copy-link')).then(function () {
          copy.textContent = 'Link copied';
        });
      }
    });
  }

  // ---- OTP resend countdown ----
  function setupResendCountdown() {
    var form = document.querySelector('[data-resend]');
    if (!form) return;
    var wait = Number(form.getAttribute('data-wait')) || 0;
    var btn = form.querySelector('button');
    var label = form.querySelector('[data-resend-count]');
    if (!wait || !btn) return;
    var timer = setInterval(function () {
      wait -= 1;
      if (wait <= 0) {
        clearInterval(timer);
        btn.disabled = false;
        if (label) label.remove();
      } else if (label) {
        label.textContent = 'in ' + wait + 's';
      }
    }, 1000);
  }

  ready(function () {
    setupResendCountdown();
    setupWishlist();
    setupLoadMore();
    setupDialogs();
    setupShare();
    document.addEventListener('click', handleStep);
    document.addEventListener('change', handleQtyChange);
    setupSearch();
    setupToasts();
    setupLenis();
    setupChrome();
    setupHero();
    setupReveals();
    setupGallery();
    setupPinLookup();
    setupStickyBuy();
    setupAutoSubmit();
    setupSubmitFeedback();
    setupStripEmpty();
    window.__fdReady = true;
  });
})();
