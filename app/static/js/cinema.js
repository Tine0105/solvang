/* Solvang Motion & Interaction Layer — ai-design-skills B7 & B11 compliant
   Base curve: cubic-bezier(0.22, 1, 0.36, 1)
   Scroll reveals & word-by-word tagline reveal via IntersectionObserver + rAF
*/
(function () {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* 1. Full-height Overlay Menu with 60ms staggered link entrance (capped at 400ms) */
  function initOverlayMenu() {
    const toggle = document.querySelector('[data-nav-toggle]');
    const overlay = document.querySelector('[data-overlay-menu]');
    const closeBtn = document.querySelector('[data-overlay-close]');
    if (!toggle || !overlay) return;

    const items = Array.from(overlay.querySelectorAll('[data-overlay-item]'));

    const setOpen = (open) => {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.classList.toggle('is-open', open);

      if (open) {
        overlay.hidden = false;
        document.body.style.overflow = 'hidden';
        items.forEach((el, idx) => {
          const delay = prefersReduced ? 0 : Math.min(idx * 60, 400);
          el.style.transitionDelay = `${delay}ms`;
        });
        requestAnimationFrame(() => {
          overlay.classList.add('is-open');
        });
      } else {
        items.forEach((el) => {
          el.style.transitionDelay = '0ms';
        });
        overlay.classList.remove('is-open');
        document.body.style.overflow = '';
        setTimeout(() => {
          overlay.hidden = true;
        }, 320);
      }
    };

    toggle.addEventListener('click', () => setOpen(overlay.hidden));
    closeBtn?.addEventListener('click', () => setOpen(false));
    overlay.addEventListener('click', (e) => {
      if (e.target.closest('a[href]')) setOpen(false);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !overlay.hidden) {
        setOpen(false);
        toggle.focus();
      }
    });
  }

  /* 2. Section Scroll Reveals via IntersectionObserver (B7: rise 32px, 700ms on base curve, once) */
  function initScrollReveals() {
    const targets = document.querySelectorAll('[data-reveal]');
    if (!targets.length || prefersReduced || !('IntersectionObserver' in window)) return;

    const vh = window.innerHeight || document.documentElement.clientHeight;
    const io = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -32px 0px' }
    );

    targets.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.top > vh * 0.92) {
        el.classList.add('will-reveal');
        io.observe(el);
      }
    });
  }

  /* 3. Mandatory Tagline Reveal (B11: word-by-word activation in reading order as words cross trigger line) */
  function initTaglineReveal() {
    const containers = document.querySelectorAll('[data-tagline-reveal]');
    if (!containers.length) return;

    containers.forEach((container) => {
      const rawText = (container.textContent || '').trim().replace(/\s+/g, ' ');
      if (!rawText) return;

      const words = rawText.split(' ');
      container.textContent = '';
      const wordEls = words.map((w, i) => {
        const span = document.createElement('span');
        span.className = 'tagline-word';
        span.textContent = w;
        if (prefersReduced) {
          span.classList.add('is-active');
        }
        container.appendChild(span);
        if (i < words.length - 1) {
          container.appendChild(document.createTextNode(' '));
        }
        return span;
      });

      if (prefersReduced) return;

      let isVisible = false;
      let rafPending = false;

      const updateWords = () => {
        rafPending = false;
        if (!isVisible) return;
        const vh = window.innerHeight || document.documentElement.clientHeight;
        const rect = container.getBoundingClientRect();
        // Map container progress across viewport [85% vh -> 30% vh] to word activation index
        const startY = vh * 0.85;
        const endY = vh * 0.25;
        const progress = Math.max(0, Math.min(1, (startY - rect.top) / Math.max(1, startY - endY)));
        const activeCount = Math.round(progress * wordEls.length);

        wordEls.forEach((span, idx) => {
          if (idx < activeCount) {
            span.classList.add('is-active');
          }
        });
      };

      const requestTick = () => {
        if (!rafPending && isVisible) {
          rafPending = true;
          requestAnimationFrame(updateWords);
        }
      };

      if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              isVisible = entry.isIntersecting;
              if (isVisible) requestTick();
            });
          },
          { rootMargin: '80px 0px 80px 0px' }
        );
        io.observe(container);
      } else {
        isVisible = true;
      }

      window.addEventListener('scroll', requestTick, { passive: true });
      window.addEventListener('resize', requestTick, { passive: true });
      requestTick();
    });
  }

  /* 4. Lenis Smooth Scroll + Scrollytelling 3D Camera Path */
  function initSmoothScrollAndScrolly() {
    if (prefersReduced) return;

    const gsap = window.gsap;
    const ScrollTrigger = window.ScrollTrigger;
    if (gsap && ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
    }

    if (window.Lenis) {
      const lenis = new window.Lenis({
        duration: 1.1,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
      });
      if (gsap && ScrollTrigger) {
        lenis.on('scroll', ScrollTrigger.update);
        gsap.ticker.add((time) => lenis.raf(time * 1000));
        gsap.ticker.lagSmoothing(0);
      } else {
        const raf = (time) => {
          lenis.raf(time);
          requestAnimationFrame(raf);
        };
        requestAnimationFrame(raf);
      }
    }

    const scrollyTrack = document.querySelector('[data-scrolly-track]');
    if (scrollyTrack && gsap && ScrollTrigger) {
      ScrollTrigger.create({
        trigger: scrollyTrack,
        start: 'top top',
        end: 'bottom bottom',
        scrub: 0.4,
        onUpdate: (self) => {
          if (window.__solvangViewer && typeof window.__solvangViewer.setCameraProgress === 'function') {
            window.__solvangViewer.setCameraProgress(self.progress);
          }
        },
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initOverlayMenu();
    initScrollReveals();
    initTaglineReveal();
    initSmoothScrollAndScrolly();
  });
})();
