(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* ---------- 1. Appearance follows the device. Clear the old toggle's saved choice. ---------- */
  try {
    localStorage.removeItem("color-scheme");
  } catch {}

  /* ---------- 2. Mobile navigation drawer and current page ---------- */
  function initMobileNav() {
    const header = document.querySelector(".site-header");
    const btn = document.getElementById("mobile-menu-btn");
    const drawer = document.getElementById("mobile-drawer");
    if (!header || !btn || !drawer) return;

    let isOpen = false;
    const setOpen = (next) => {
      isOpen = next;
      btn.classList.toggle("open", isOpen);
      btn.setAttribute("aria-expanded", String(isOpen));
      drawer.hidden = !isOpen;
    };

    btn.addEventListener("click", () => setOpen(!isOpen));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isOpen) setOpen(false);
    });
    document.addEventListener("pointerdown", (e) => {
      if (isOpen && !header.contains(e.target)) setOpen(false);
    });
    drawer.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => setOpen(false));
    });
  }

  function markCurrentPage() {
    const path = location.pathname.replace(/\.html$/, "").replace(/\/index$/, "/");
    document.querySelectorAll(".nav-links a").forEach((link) => {
      const href = link.getAttribute("href");
      if (href.includes("#")) return;
      const match = href === "/guides/" ? path.startsWith("/guides/") : path === href;
      if (match) link.setAttribute("aria-current", "page");
    });
  }

  initMobileNav();
  markCurrentPage();

  /* ---------- 3. Hero bolt pad: draw six or more bolts and the lock lifts ---------- */
  const DEMO_PATTERN = [20, 16, 11, 7, 8, 4];
  let lastPattern = null; // this page view only, never stored

  const centre = (i) => [10 + 20 * (i % 5), 10 + 20 * Math.floor(i / 5)];
  const points = (seq) => seq.map((i) => centre(i).join(",")).join(" ");

  function initHero() {
    const pad = document.getElementById("hero-pad");
    const lock = document.getElementById("lock");
    const vault = document.getElementById("vault");
    if (!pad || !lock || !vault) return;

    const trail = document.getElementById("pad-trail");
    const live = document.getElementById("pad-live");
    const prompt = document.getElementById("pad-prompt");
    const status = document.getElementById("hero-status");
    const announce = document.getElementById("hero-announce");
    const demoBtn = document.getElementById("demo-btn");
    const vaultTitle = document.getElementById("vault-title");
    const bolts = Array.from(pad.querySelectorAll(".b"));

    let state = "idle"; // idle | drawing | wrong | success | unlocked
    let path = [];
    let drawing = false;
    let demoRunning = false;
    let timers = [];
    let raf = 0;
    let pending = null;

    const later = (fn, ms) => timers.push(window.setTimeout(fn, ms));
    const clearTimers = () => {
      timers.forEach(clearTimeout);
      timers = [];
    };

    function setPrompt(kind) {
      if (kind === "wrong") {
        prompt.innerHTML = '<p class="prompt-error">Too short. Use at least six bolts.</p>';
      } else if (kind === "success") {
        prompt.innerHTML = '<p class="prompt-title">Unlocking…</p>';
      } else {
        const sub = kind === "drawing" ? `${path.length} ${path.length === 1 ? "bolt" : "bolts"}` : "Through six or more bolts";
        prompt.innerHTML = `<p class="prompt-title">Try it. Draw any shape.</p><p class="prompt-sub">${sub}</p>`;
      }
    }

    function setStatus(text, dotClass) {
      status.innerHTML = `<span class="dot ${dotClass}" aria-hidden="true"></span><span>${text}</span>`;
    }

    function light(i) {
      bolts[i].classList.add("on");
      trail.setAttribute("points", points(path));
      if (state === "drawing") setPrompt("drawing");
    }

    function reset() {
      path = [];
      bolts.forEach((b) => b.classList.remove("on"));
      trail.setAttribute("points", "");
      live.classList.remove("on");
      pad.classList.remove("err", "ok");
      state = "idle";
      setPrompt("idle");
      setStatus("Locked", "dot-locked");
    }

    function toPercent(e) {
      const r = pad.getBoundingClientRect();
      return { x: ((e.clientX - r.left) / r.width) * 100, y: ((e.clientY - r.top) / r.height) * 100 };
    }

    // Same rule as the app: hit radius = pitch (20%) × 0.46.
    function hit(p) {
      const c = Math.round((p.x - 10) / 20);
      const r = Math.round((p.y - 10) / 20);
      if (c < 0 || c > 4 || r < 0 || r > 4) return -1;
      const dx = p.x - (10 + 20 * c);
      const dy = p.y - (10 + 20 * r);
      return dx * dx + dy * dy <= 9.2 * 9.2 ? r * 5 + c : -1;
    }

    function updateLive(p) {
      if (!path.length) return;
      const [x1, y1] = centre(path[path.length - 1]);
      live.setAttribute("x1", x1);
      live.setAttribute("y1", y1);
      live.setAttribute("x2", p.x);
      live.setAttribute("y2", p.y);
      live.classList.add("on");
    }

    function finish() {
      live.classList.remove("on");
      if (path.length >= 6) success();
      else if (path.length > 0) wrong();
      else reset();
    }

    function wrong() {
      state = "wrong";
      pad.classList.add("err");
      setPrompt("wrong");
      later(reset, 700);
    }

    function success() {
      state = "success";
      lastPattern = path.slice();
      pad.classList.add("ok");
      setPrompt("success");
      setStatus("Unlocking", "dot-ink");
      updateFinalPad();
      later(unlock, 420);
    }

    function unlock() {
      state = "unlocked";
      loadWall();
      lock.style.willChange = vault.style.willChange = "transform, opacity";
      lock.classList.add("lifted");
      vault.classList.add("open");
      vault.inert = false;
      vault.removeAttribute("aria-hidden");
      announce.textContent = "Unlocked. This is a demo of Noxium's lock screen.";
      vaultTitle.focus({ preventScroll: true });
      later(() => {
        lock.inert = true;
        lock.style.willChange = vault.style.willChange = "";
      }, 900);
    }

    function relock(focusDemo = true) {
      if (state !== "unlocked") return;
      clearTimers();
      lock.inert = false;
      lock.classList.remove("lifted");
      vault.classList.remove("open");
      vault.inert = true;
      vault.setAttribute("aria-hidden", "true");
      drawing = false;
      demoRunning = false;
      reset();
      announce.textContent = "Locked again.";
      if (focusDemo) demoBtn.focus({ preventScroll: true });
    }

    function demo() {
      if (state !== "idle" || demoRunning) return;
      loadWall();
      clearTimers();
      demoRunning = true;
      reset();
      state = "drawing";
      DEMO_PATTERN.forEach((b, i) => {
        later(() => {
          path.push(b);
          light(b);
        }, 260 + i * 170);
      });
      later(() => {
        demoRunning = false;
        finish();
      }, 260 + DEMO_PATTERN.length * 170 + 220);
    }

    pad.addEventListener("pointerdown", (e) => {
      if (state !== "idle" || demoRunning) return;
      loadWall();
      try {
        pad.setPointerCapture(e.pointerId);
      } catch {}
      e.preventDefault();
      drawing = true;
      state = "drawing";
      path = [];
      const p = toPercent(e);
      const h = hit(p);
      if (h >= 0) {
        path.push(h);
        light(h);
      }
      setPrompt("drawing");
      lock.style.willChange = vault.style.willChange = "transform, opacity";
    });

    pad.addEventListener("pointermove", (e) => {
      if (!drawing) return;
      // Hit-test every sample (coalesced too) so a fast swipe can't skip a bolt between frames.
      const samples = e.getCoalescedEvents ? e.getCoalescedEvents() : [];
      (samples.length ? samples : [e]).forEach((s) => {
        const h = hit(toPercent(s));
        if (h >= 0 && !path.includes(h)) {
          path.push(h);
          light(h);
        }
      });
      pending = toPercent(e);
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        if (drawing && pending) updateLive(pending);
      });
    });

    const end = () => {
      if (!drawing) return;
      drawing = false;
      if (state !== "success") lock.style.willChange = vault.style.willChange = "";
      finish();
    };
    pad.addEventListener("pointerup", end);
    pad.addEventListener("pointercancel", end);
    pad.addEventListener("lostpointercapture", end);

    demoBtn.hidden = false;
    demoBtn.addEventListener("click", demo);
    document.querySelectorAll("[data-relock]").forEach((btn) => btn.addEventListener("click", () => relock()));

    // The vault's install button points at the form under the lock: close the vault first.
    vault.querySelectorAll('a[href="#waitlist"]').forEach((a) => {
      a.addEventListener("click", () => relock(false), { capture: true });
    });

    // Cursor light (desktop only), paused while the hero is off screen.
    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches && !reduceMotion.matches) {
      let heroVisible = true;
      let glowRaf = 0;
      new IntersectionObserver(([entry]) => {
        heroVisible = entry.isIntersecting;
      }).observe(lock);
      lock.addEventListener("pointermove", (e) => {
        if (!heroVisible || glowRaf || document.hidden) return;
        glowRaf = requestAnimationFrame(() => {
          glowRaf = 0;
          const r = lock.getBoundingClientRect();
          lock.style.setProperty("--mx", `${e.clientX - r.left}px`);
          lock.style.setProperty("--my", `${e.clientY - r.top}px`);
        });
      });
    }

    // Load the photo wall after the page has loaded, so it never competes with the headline.
    const idle = window.requestIdleCallback || ((fn) => window.setTimeout(fn, 1200));
    window.addEventListener("load", () => idle(loadWall));
  }

  let wallLoaded = false;
  function loadWall() {
    if (wallLoaded) return;
    wallLoaded = true;
    document.querySelectorAll("#vault-wall [data-srcset], #vault-wall [data-src]").forEach((el) => {
      if (el.dataset.srcset) el.srcset = el.dataset.srcset;
      if (el.dataset.src) el.src = el.dataset.src;
    });
  }

  // The final CTA shows the pattern the visitor drew in the hero.
  function updateFinalPad() {
    const pad = document.getElementById("final-pad");
    if (!pad || !lastPattern) return;
    const lit = new Set(lastPattern);
    pad.querySelectorAll(".mb").forEach((b, i) => b.classList.toggle("on", lit.has(i)));
    pad.querySelector(".trail").setAttribute("points", points(lastPattern));
  }

  initHero();

  /* ---------- 4. Scroll reveals (fallback where scroll-driven animations aren't supported) ---------- */
  function initReveals() {
    if (reduceMotion.matches || !("IntersectionObserver" in window)) return;
    if (window.CSS && CSS.supports("animation-timeline: view()")) return;
    document.documentElement.classList.add("reveal-js");

    const groups = new Map();
    document.querySelectorAll(".rv, .ct").forEach((el) => {
      const key = el.parentElement;
      const n = groups.get(key) || 0;
      groups.set(key, n + 1);
      if (!el.style.getPropertyValue("--stagger")) {
        el.style.setProperty("--stagger", `${n * (el.classList.contains("ct") ? 0.08 : 0.12)}s`);
      }
    });

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
    );
    document.querySelectorAll(".rv, .ct").forEach((el) => io.observe(el));
  }

  initReveals();

  /* ---------- 5. Sticky install bar (phones) ---------- */
  function initStickyBar() {
    const bar = document.getElementById("sticky-bar");
    const heroCta = document.querySelector(".hero-copy .waitlist:not([hidden]), .hero-copy .store-row:not([hidden])");
    if (!bar || !heroCta || !("IntersectionObserver" in window)) return;
    document.body.classList.add("has-sticky");

    const blockers = [document.getElementById("waitlist"), document.querySelector(".final-cta"), document.querySelector(".site-footer")].filter(Boolean);
    let heroCtaVisible = true;
    const blocking = new Set();
    const update = () => {
      document.body.classList.toggle("sticky-on", !heroCtaVisible && blocking.size === 0);
    };

    new IntersectionObserver(([entry]) => {
      heroCtaVisible = entry.isIntersecting || entry.boundingClientRect.top > 0;
      update();
    }).observe(heroCta);

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) blocking.add(entry.target);
        else blocking.delete(entry.target);
      });
      update();
    });
    blockers.forEach((el) => io.observe(el));
  }

  initStickyBar();

  /* ---------- 6. Competitor comparison table category filter ---------- */
  function initComparisonFilters() {
    const filterBtns = Array.from(document.querySelectorAll(".compare-filter-btn[data-compare-filter]"));
    const rows = Array.from(document.querySelectorAll(".compare-table tbody tr[data-cat]"));
    if (filterBtns.length === 0 || rows.length === 0) return;

    filterBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const cat = btn.dataset.compareFilter || "all";
        filterBtns.forEach((b) => {
          const active = b === btn;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-pressed", String(active));
        });
        rows.forEach((row) => {
          const match = cat === "all" || row.dataset.cat === cat;
          row.hidden = !match;
        });
      });
    });
  }

  initComparisonFilters();

  /* ---------- 7. Native <dialog> install modal and copy link ---------- */
  const INSTALL_URL = "https://getnoxium.app/";
  const installDialog = document.getElementById("install-dialog");
  const installTitle = document.getElementById("install-dialog-title");
  const installBadge = document.getElementById("install-dialog-badge");
  const closeInstallBtn = document.getElementById("install-close-btn");
  const openInstallBtns = Array.from(document.querySelectorAll("[data-open-install-modal]"));

  if (installDialog) {
    openInstallBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const ctx = btn.getAttribute("data-open-install-modal");
        if (installTitle) {
          installTitle.textContent = ctx === "pro" ? "Install Noxium Pro" : "Install Noxium";
        }
        if (installBadge) {
          installBadge.textContent = ctx === "pro" ? "Noxium Pro · Family Sharing Included" : "For iPhone and iPad · Free plan";
        }
        if (typeof installDialog.showModal === "function") {
          installDialog.showModal();
        }
      });
    });

    if (closeInstallBtn) {
      closeInstallBtn.addEventListener("click", () => installDialog.close());
    }

    installDialog.addEventListener("click", (e) => {
      if (e.target === installDialog) {
        installDialog.close();
      }
    });
  }

  function wireCopyButton(btnId, copiedText) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    const defaultLabel = btn.textContent;
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(INSTALL_URL);
      } catch {}
      btn.textContent = copiedText;
      window.setTimeout(() => {
        btn.textContent = defaultLabel;
      }, 2200);
    });
  }

  wireCopyButton("modal-copy-link-btn", "Link copied");

  /* ---------- 8. Beta waitlist (Google Sheets webhook) ---------- */
  function initEarlyTesterWaitlist() {
    const form = document.getElementById("waitlist-form");
    const input = document.getElementById("waitlist-email");
    const submitBtn = document.getElementById("waitlist-submit-btn");
    const successCard = document.getElementById("waitlist-success");
    const emailPill = document.getElementById("registered-email-pill");
    const changeBtn = document.getElementById("waitlist-change-email");
    const storageKey = "darkroom_early_tester_roster";
    const GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/AKfycbx-G1s-YefuipSRcmtC40tX_UBV45CNvM_gRZ93Xh-hv2e89fh6nKLZN9NzOHwwhDvW/exec";

    if (!form || !input || !successCard) return;

    function renderConfirmed(email) {
      if (emailPill) emailPill.textContent = email;
      form.hidden = true;
      successCard.hidden = false;
    }

    function renderForm() {
      form.hidden = false;
      successCard.hidden = true;
      form.classList.remove("show-error");
      input.value = "";
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Get the beta";
      }
    }

    // Check existing registration in browser
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const data = JSON.parse(saved);
        if (data && data.email) {
          renderConfirmed(data.email);
        }
      }
    } catch {}

    input.addEventListener("input", () => {
      form.classList.remove("show-error");
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const raw = input.value.trim().toLowerCase();
      const isValid = input.checkValidity() && raw.length > 3 && raw.includes("@");

      if (!isValid) {
        form.classList.add("show-error");
        input.focus();
        return;
      }

      form.classList.remove("show-error");

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending…";
      }

      // Submit to Google Sheets (text/plain mode bypasses browser CORS preflight).
      // Apps Script can take many seconds to answer, and no-cors hides the reply anyway,
      // so wait at most a moment; keepalive lets the request finish even if the page is left.
      const submit = fetch(GOOGLE_SHEETS_URL, {
        method: "POST",
        mode: "no-cors",
        keepalive: true,
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify({ email: raw, timestamp: new Date().toISOString() }),
      }).catch((err) => {
        console.warn("Google Sheet submit notice:", err);
      });
      await Promise.race([submit, new Promise((resolve) => setTimeout(resolve, 1500))]);

      try {
        localStorage.setItem(storageKey, JSON.stringify({ email: raw, createdAt: new Date().toISOString() }));
      } catch {}

      renderConfirmed(raw);
    });

    if (changeBtn) {
      changeBtn.addEventListener("click", () => {
        try {
          localStorage.removeItem(storageKey);
        } catch {}
        renderForm();
        input.focus();
      });
    }

    // Links to the beta scroll to the hero form and focus the email field.
    document.querySelectorAll('a[href="#waitlist"]').forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        const target = document.getElementById("waitlist");
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "center" });
        if (!form.hidden) {
          setTimeout(() => input.focus({ preventScroll: true }), 400);
        }
      });
    });
  }

  initEarlyTesterWaitlist();
})();
