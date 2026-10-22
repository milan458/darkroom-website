(() => {
  /* ---------- 1. Theme Toggle (follows the system until the visitor picks) ---------- */
  const ICONS = {
    sun: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="12" y1="2.5" x2="12" y2="5.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="12" y1="18.8" x2="12" y2="21.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="2.5" y1="12" x2="5.2" y2="12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="18.8" y1="12" x2="21.5" y2="12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="5.3" y1="5.3" x2="7.2" y2="7.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="16.8" y1="16.8" x2="18.7" y2="18.7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="16.8" y1="7.2" x2="18.7" y2="5.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="5.3" y1="18.7" x2="7.2" y2="16.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    moon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 14.8a8.9 8.9 0 1 1-9.6-11 7.2 7.2 0 0 0 9.6 11Z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };

  const root = document.documentElement;
  const metaScheme = document.querySelector('meta[name="color-scheme"]');
  const metaThemeColor = document.getElementById("meta-theme-color");
  const themeBtn = document.getElementById("theme-toggle");
  const themeIcon = document.getElementById("theme-icon");
  const themeLabel = document.getElementById("theme-label");

  function getActiveTheme() {
    return root.dataset.theme === "light" ? "light" : "dark";
  }

  function applyTheme(theme, persist = false) {
    const resolved = theme === "light" ? "light" : "dark";
    root.dataset.theme = resolved;
    if (metaScheme) {
      metaScheme.content = resolved;
    }
    if (metaThemeColor) {
      metaThemeColor.content = resolved === "light" ? "#F3EEE7" : "#070605";
    }
    if (persist) {
      try {
        localStorage.setItem("color-scheme", resolved);
      } catch {}
    }
    const isDark = resolved === "dark";
    if (themeBtn) {
      themeBtn.setAttribute("aria-pressed", String(!isDark));
      themeBtn.setAttribute(
        "aria-label",
        isDark
          ? themeBtn.dataset.switchLight || "Switch to light mode"
          : themeBtn.dataset.switchDark || "Switch to dark mode"
      );
    }
    if (themeIcon) {
      themeIcon.innerHTML = isDark ? ICONS.sun : ICONS.moon;
    }
    if (themeLabel) {
      themeLabel.textContent = isDark
        ? themeBtn?.dataset.lightLabel || "Light"
        : themeBtn?.dataset.darkLabel || "Dark";
    }
    window.dispatchEvent(new CustomEvent("darkroom-themechange", { detail: { theme: resolved, isDark } }));
  }

  applyTheme(getActiveTheme(), false);

  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const next = getActiveTheme() === "dark" ? "light" : "dark";
      applyTheme(next, true);
    });
  }

  window.addEventListener("storage", (e) => {
    if (e.key === "color-scheme") {
      applyTheme(e.newValue === "light" ? "light" : "dark", false);
    }
  });

  /* ---------- 2. Mobile Navigation Drawer ---------- */
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
      drawer.classList.toggle("open", isOpen);
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

  initMobileNav();

  /* ---------- 3. Room Configurations & Contact Sheet Renderer ---------- */
  const ROOM_MODES = {
    main: {
      key: "main",
      pattern: [20, 16, 11, 7, 8, 4],
      verifyLabel: "Pattern recognised",
      doorStatus: "Unlocked",
      unlockTitle: "Opening…",
      unlockSub: "Unlocking your vault",
      roomTitle: "Library",
      rollMeta: "Today · 1,284 photos",
      sealMeta: "● Backed up",
      sealWarn: false,
      palettes: [
        ["#5A3A2C", "#C27A4A"],
        ["#2B3A4A", "#7A9CB8"],
        ["#3D4A2E", "#A3B36A"],
        ["#4A2B3A", "#C46A8A"],
        ["#2E2A4A", "#8B7EC2"],
        ["#4A3F2B", "#E0B36A"],
        ["#1F3A36", "#6AB3A3"],
        ["#3A2424", "#D36A5A"]
      ],
      durations: { 1: "0:18", 2: "0:11", 3: "0:35", 5: "0:13", 6: "0:45", 10: "2:15", 15: "0:08" },
      notes: new Set([7, 13]),
      prefix: ""
    },
    decoy: {
      key: "decoy",
      pattern: [0, 6, 12, 8, 4, 9],
      verifyLabel: "Pattern recognised",
      doorStatus: "Unlocked",
      unlockTitle: "Opening…",
      unlockSub: "Opening the decoy vault",
      roomTitle: "Holiday",
      rollMeta: "Today · 14 photos",
      sealMeta: "● Backed up",
      sealWarn: false,
      palettes: [
        ["#2E4A3E", "#5ED196"],
        ["#2C4454", "#7BB5D6"],
        ["#3B4C2B", "#9AC472"],
        ["#364B4A", "#72C4B8"],
        ["#46422A", "#C4B468"]
      ],
      durations: { 2: "0:09", 8: "0:14" },
      notes: new Set([5]),
      prefix: "D"
    },
    duress: {
      key: "duress",
      pattern: [24, 18, 12, 6, 0, 1, 2],
      verifyLabel: "Pattern recognised",
      doorStatus: "Unlocked",
      unlockTitle: "Opening…",
      unlockSub: "Other vaults removed from this iPhone",
      roomTitle: "Receipts",
      rollMeta: "Today · 8 photos",
      sealMeta: "● Backed up",
      sealWarn: true,
      palettes: [
        ["#443222", "#F5B759"],
        ["#3A2D24", "#C89652"],
        ["#322822", "#A87C46"],
        ["#483626", "#E0A658"]
      ],
      durations: {},
      notes: new Set([3, 6]),
      prefix: "W"
    }
  };

  function populateContactSheet(modeKey = "main") {
    const grid = document.getElementById("vault-grid");
    const roomTitleEl = document.getElementById("vault-room-title");
    const rollMetaEl = document.getElementById("vault-roll-meta");
    const sealMetaEl = document.getElementById("vault-seal-meta");
    const unlockTitleEl = document.getElementById("unlock-stage-title");
    const unlockSubEl = document.getElementById("unlock-stage-sub");
    const cfg = ROOM_MODES[modeKey] || ROOM_MODES.main;

    if (roomTitleEl) roomTitleEl.textContent = cfg.roomTitle;
    if (rollMetaEl) rollMetaEl.textContent = cfg.rollMeta;
    if (sealMetaEl) {
      sealMetaEl.textContent = cfg.sealMeta;
      sealMetaEl.style.color = cfg.sealWarn ? "var(--amber)" : "var(--ok)";
    }
    if (unlockTitleEl) unlockTitleEl.textContent = cfg.unlockTitle;
    if (unlockSubEl) unlockSubEl.textContent = cfg.unlockSub;

    if (!grid) return;
    grid.innerHTML = "";

    const frag = document.createDocumentFragment();
    for (let i = 1; i <= 18; i++) {
      const cell = document.createElement("div");
      cell.className = "vault-cell";
      const [c1, c2] = cfg.palettes[(i * 3) % cfg.palettes.length];
      const angle = (i * 47) % 360;
      const cx = 22 + ((i * 17) % 56);
      const cy = 26 + ((i * 11) % 48);

      if (cfg.notes.has(i)) {
        cell.style.background =
          "repeating-linear-gradient(180deg, rgba(245,183,89,0.28) 0 1.5px, transparent 1.5px 6px) 6px 6px / 68% 45% no-repeat, #221C18";
      } else {
        cell.style.background = `radial-gradient(circle at ${cx}% ${cy}%, ${c2}, transparent 62%), linear-gradient(${angle}deg, ${c1}, #120F0D)`;
      }

      const frameNo = "";
      const dur = cfg.durations[i] ? `<span class="vault-cell-time">${cfg.durations[i]}</span>` : "";
      cell.innerHTML = frameNo + dur;
      frag.appendChild(cell);
    }
    grid.appendChild(frag);
  }

  populateContactSheet("main");

  /* ---------- 4. Hero Background Pattern Canvas + 3-Stage Phone Simulator ---------- */
  function initHeroRuntime() {
    const canvas = document.getElementById("pattern-canvas");
    const pathEl = document.getElementById("drawing-path");
    const cursorEl = document.getElementById("drawing-cursor");
    const svgEl = document.getElementById("mockup-svg");
    const zoneEl = document.getElementById("pattern-lock-zone");
    const screenEl = document.getElementById("phone-screen");
    const dots = Array.from(document.querySelectorAll(".grid-dot"));
    const timeEl = document.getElementById("mockup-time");
    const subtitleEl = document.getElementById("lock-subtitle");
    const doorTextEl = document.getElementById("mockup-door-text");
    const doorDotEl = document.getElementById("mockup-door-dot");
    const counterEl = document.getElementById("bolt-counter");
    const lockVaultBtn = document.getElementById("lock-vault-btn");
    const quickUnlockBtn = document.getElementById("quick-unlock-btn");
    const presetBtns = Array.from(document.querySelectorAll(".room-preset-btn[data-preset-mode]"));
    const pauseBtn = document.getElementById("sim-pause-btn");
    const pauseLabel = document.getElementById("sim-pause-label");
    const liveStatus = document.getElementById("sim-live-status");

    if (!canvas || !pathEl || !cursorEl || !svgEl || !zoneEl || !screenEl || dots.length === 0) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const ctx = canvas.getContext("2d");

    const state = {
      dotColor: "#F5B759",
      trailColor: "rgba(232, 59, 46, 0.36)",
      bgDots: [],
      width: 0,
      height: 0,
      heroVisible: true,
      bgTimer: 0,
      bgClearTimer: 0,
      loopTicket: 0,
      loopRunning: false,
      userPaused: false,
      userInteracting: false,
      userPinnedMode: null,
      activeMode: "main",
      modeOrder: ["main", "decoy"],
      nodeCenters: []
    };

    function announceStatus(msg) {
      if (liveStatus) liveStatus.textContent = msg;
    }

    function syncPresetButtons(modeKey) {
      state.activeMode = modeKey;
      screenEl.setAttribute("data-room-mode", modeKey);
      populateContactSheet(modeKey);
      presetBtns.forEach((btn) => {
        const isMatch = btn.dataset.presetMode === modeKey;
        btn.classList.toggle("is-active", isMatch);
        btn.setAttribute("aria-pressed", String(isMatch));
      });
    }

    function syncPauseUI() {
      if (!pauseBtn || !pauseLabel) return;
      pauseBtn.setAttribute("aria-pressed", String(state.userPaused));
      pauseLabel.textContent = state.userPaused ? "Resume demo" : "Pause demo";
    }

    /* Live Clock */
    function updateClock() {
      if (!timeEl) return;
      const now = new Date();
      const h = ((now.getHours() + 11) % 12) + 1;
      const m = String(now.getMinutes()).padStart(2, "0");
      timeEl.textContent = `${h}:${m}`;
    }
    updateClock();
    setInterval(updateClock, 30000);

    /* Background Canvas Dots & Subtle Geometric Trails */
    function syncCanvasColors() {
      const isLight = getActiveTheme() === "light";
      state.dotColor = isLight ? "rgba(140, 79, 5, 0.42)" : "rgba(245, 183, 89, 0.46)";
      state.trailColor = isLight ? "rgba(192, 38, 27, 0.25)" : "rgba(232, 59, 46, 0.35)";
    }

    function buildBgDots() {
      state.bgDots = [];
      const spacing = 112;
      const cols = Math.ceil(state.width / spacing);
      const rows = Math.ceil(state.height / spacing);
      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          state.bgDots.push({
            x: c * spacing + Math.random() * 24,
            y: r * spacing + Math.random() * 24
          });
        }
      }
    }

    function drawBgBase() {
      if (!ctx) return;
      ctx.clearRect(0, 0, state.width, state.height);
      ctx.fillStyle = state.dotColor;
      for (const d of state.bgDots) {
        ctx.beginPath();
        ctx.arc(d.x, d.y, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function sketchRandomBgTrail() {
      if (!ctx || state.bgDots.length === 0 || !state.heroVisible || document.hidden || reducedMotion.matches || state.userPaused) return;
      drawBgBase();
      const startIdx = Math.floor(Math.random() * state.bgDots.length);
      const steps = 4 + Math.floor(Math.random() * 3);
      let current = state.bgDots[startIdx];

      ctx.strokeStyle = state.trailColor;
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(current.x, current.y);
      for (let i = 0; i < steps; i++) {
        const candidate = state.bgDots[Math.floor(Math.random() * state.bgDots.length)];
        const dist = Math.hypot(candidate.x - current.x, candidate.y - current.y);
        if (dist < 210 && dist > 36) {
          ctx.lineTo(candidate.x, candidate.y);
          current = candidate;
        }
      }
      ctx.stroke();

      clearTimeout(state.bgClearTimer);
      state.bgClearTimer = window.setTimeout(() => {
        drawBgBase();
      }, 560);
    }

    function scheduleBgTrail() {
      clearTimeout(state.bgTimer);
      if (!state.heroVisible || document.hidden || reducedMotion.matches || state.userPaused) return;
      state.bgTimer = window.setTimeout(() => {
        sketchRandomBgTrail();
        scheduleBgTrail();
      }, 950 + Math.floor(Math.random() * 1100));
    }

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      state.width = canvas.width = Math.round(entry.contentRect.width);
      state.height = canvas.height = Math.round(entry.contentRect.height);
      syncCanvasColors();
      buildBgDots();
      drawBgBase();
    });
    if (canvas.parentElement) ro.observe(canvas.parentElement);

    window.addEventListener("darkroom-themechange", () => {
      syncCanvasColors();
      drawBgBase();
    });

    /* Phone Mockup Geometry Helpers */
    function measureNodes() {
      const zoneRect = zoneEl.getBoundingClientRect();
      svgEl.setAttribute("viewBox", `0 0 ${zoneRect.width} ${zoneRect.height}`);
      svgEl.setAttribute("width", `${zoneRect.width}`);
      svgEl.setAttribute("height", `${zoneRect.height}`);
      state.nodeCenters = dots.map((dot) => {
        const r = dot.getBoundingClientRect();
        return {
          x: r.left - zoneRect.left + r.width / 2,
          y: r.top - zoneRect.top + r.height / 2
        };
      });
    }

    function renderSvgTrail(points) {
      if (points.length === 0) {
        pathEl.setAttribute("d", "");
        cursorEl.setAttribute("opacity", "0");
        return;
      }
      const d = points
        .map((pt, idx) => `${idx === 0 ? "M" : "L"} ${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`)
        .join(" ");
      pathEl.setAttribute("d", d);
      const tip = points[points.length - 1];
      cursorEl.setAttribute("cx", tip.x.toFixed(2));
      cursorEl.setAttribute("cy", tip.y.toFixed(2));
      cursorEl.setAttribute("opacity", "1");
    }

    function setDoorStatus(text, isOk) {
      if (doorTextEl) doorTextEl.textContent = text;
      if (doorDotEl) {
        doorDotEl.style.background = isOk ? "var(--ok)" : "var(--safelight)";
        doorDotEl.style.boxShadow = isOk ? "0 0 10px var(--ok)" : "0 0 10px var(--safelight)";
      }
    }

    function resetLockUI(msg = "Draw your pattern", cls = "") {
      dots.forEach((d) => d.classList.remove("active"));
      renderSvgTrail([]);
      if (counterEl) counterEl.textContent = "0";
      if (subtitleEl) {
        subtitleEl.textContent = msg;
        subtitleEl.className = "lock-subtitle" + (cls ? ` ${cls}` : "");
      }
      setDoorStatus("Locked", false);
    }

    function wait(ms, ticket) {
      return new Promise((resolve) => {
        window.setTimeout(() => {
          resolve(!document.hidden && state.heroVisible && ticket === state.loopTicket && !state.userInteracting && !state.userPaused);
        }, ms);
      });
    }

    function animateSegment(existingPts, fromPt, toPt, durationMs, ticket) {
      return new Promise((resolve) => {
        const start = performance.now();
        function frame(now) {
          if (document.hidden || !state.heroVisible || ticket !== state.loopTicket || state.userInteracting || state.userPaused) {
            resolve(false);
            return;
          }
          const t = Math.min(1, (now - start) / durationMs);
          const x = fromPt.x + (toPt.x - fromPt.x) * t;
          const y = fromPt.y + (toPt.y - fromPt.y) * t;
          renderSvgTrail([...existingPts, { x, y }]);
          if (t < 1) {
            requestAnimationFrame(frame);
          } else {
            resolve(true);
          }
        }
        requestAnimationFrame(frame);
      });
    }

    async function runRoomSequence(modeKey, ticket) {
      const cfg = ROOM_MODES[modeKey] || ROOM_MODES.main;
      syncPresetButtons(modeKey);
      screenEl.classList.remove("mockup-unlocking", "mockup-vault");
      resetLockUI();
      measureNodes();
      if (!(await wait(320, ticket))) return false;

      const seq = cfg.pattern;
      const pts = [];
      const first = seq[0];
      dots[first].classList.add("active");
      pts.push(state.nodeCenters[first]);
      renderSvgTrail(pts);
      if (counterEl) counterEl.textContent = "1";
      if (subtitleEl) subtitleEl.textContent = "Drawing…";

      for (let i = 1; i < seq.length; i++) {
        const prevPt = state.nodeCenters[seq[i - 1]];
        const nextPt = state.nodeCenters[seq[i]];
        if (!(await animateSegment(pts.slice(), prevPt, nextPt, 165, ticket))) return false;
        dots[seq[i]].classList.add("active");
        pts.push(nextPt);
        renderSvgTrail(pts);
        if (counterEl) counterEl.textContent = String(i + 1);
      }

      if (subtitleEl) {
        subtitleEl.textContent = cfg.verifyLabel;
        subtitleEl.className = "lock-subtitle is-ok";
      }
      setDoorStatus(cfg.doorStatus, true);

      if (!(await wait(260, ticket))) return false;
      screenEl.classList.add("mockup-unlocking");
      if (!(await wait(940, ticket))) return false;
      screenEl.classList.remove("mockup-unlocking");
      screenEl.classList.add("mockup-vault");

      if (!(await wait(4400, ticket))) return false;
      screenEl.classList.remove("mockup-vault");
      resetLockUI();
      return await wait(420, ticket);
    }

    async function startAutoLoop(initialMode = state.activeMode) {
      if (state.loopRunning || reducedMotion.matches || state.userInteracting || state.userPaused) return;
      state.loopRunning = true;
      state.loopTicket += 1;
      const ticket = state.loopTicket;

      let idx = Math.max(0, state.modeOrder.indexOf(initialMode));
      if (await wait(420, ticket)) {
        while (!document.hidden && state.heroVisible && ticket === state.loopTicket && !state.userInteracting && !state.userPaused) {
          const modeKey = state.modeOrder[idx % state.modeOrder.length];
          const ok = await runRoomSequence(modeKey, ticket);
          if (!ok) break;
          idx = (idx + 1) % state.modeOrder.length;
        }
      }
      if (ticket === state.loopTicket) {
        state.loopRunning = false;
      }
    }

    function stopAutoLoop() {
      state.loopTicket += 1;
      state.loopRunning = false;
    }

    /* Preset Room Buttons + Pause Toggle in Hero Console */
    presetBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const modeKey = btn.dataset.presetMode || "main";
        state.userPinnedMode = modeKey;
        stopAutoLoop();
        state.userInteracting = false;
        syncPresetButtons(modeKey);
        const cfg = ROOM_MODES[modeKey] || ROOM_MODES.main;
        announceStatus(`Simulator switched to ${cfg.roomTitle}`);
        if (reducedMotion.matches || state.userPaused) {
          screenEl.classList.remove("mockup-unlocking");
          screenEl.classList.add("mockup-vault");
        } else {
          startAutoLoop(modeKey);
        }
      });
    });

    if (pauseBtn) {
      pauseBtn.addEventListener("click", () => {
        state.userPaused = !state.userPaused;
        syncPauseUI();
        if (state.userPaused) {
          clearTimeout(state.bgTimer);
          stopAutoLoop();
          announceStatus("Simulator auto-demo paused");
        } else {
          state.userInteracting = false;
          scheduleBgTrail();
          startAutoLoop(state.activeMode);
          announceStatus("Simulator auto-demo resumed");
        }
      });
    }

    /* Interactive User Bolt Drawing on the Mockup */
    const gcd = (a, b) => (b ? gcd(b, a % b) : a);
    let userPath = [];
    let isDrawing = false;

    function arraysEqual(a, b) {
      return a.length === b.length && a.every((v, i) => v === b[i]);
    }

    function resolveDrawnMode(path) {
      if (arraysEqual(path, ROOM_MODES.decoy.pattern)) return "decoy";
      if (arraysEqual(path, ROOM_MODES.duress.pattern)) return "duress";
      if (arraysEqual(path, ROOM_MODES.main.pattern)) return "main";
      return state.userPinnedMode || "main";
    }

    function addBoltWithIntermediates(idx) {
      if (userPath.includes(idx)) return;
      const last = userPath[userPath.length - 1];
      if (last !== undefined) {
        const r1 = Math.floor(last / 5), c1 = last % 5;
        const r2 = Math.floor(idx / 5), c2 = idx % 5;
        const dr = r2 - r1, dc = c2 - c1;
        const g = gcd(Math.abs(dr), Math.abs(dc));
        for (let k = 1; k < g; k++) {
          const mid = (r1 + (dr / g) * k) * 5 + (c1 + (dc / g) * k);
          if (!userPath.includes(mid)) {
            userPath.push(mid);
            dots[mid].classList.add("active");
          }
        }
      }
      userPath.push(idx);
      dots[idx].classList.add("active");
      if (navigator.vibrate) navigator.vibrate(8);
    }

    function pointerToLocal(e) {
      const r = zoneEl.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }

    function hitBolt(pt) {
      for (let i = 0; i < state.nodeCenters.length; i++) {
        const c = state.nodeCenters[i];
        if (Math.hypot(c.x - pt.x, c.y - pt.y) < 20) return i;
      }
      return -1;
    }

    zoneEl.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      stopAutoLoop();
      state.userInteracting = true;
      isDrawing = true;
      userPath = [];
      screenEl.classList.remove("mockup-unlocking", "mockup-vault");
      resetLockUI("Drawing…");
      measureNodes();
      zoneEl.setPointerCapture(e.pointerId);

      const pt = pointerToLocal(e);
      const hit = hitBolt(pt);
      if (hit >= 0) addBoltWithIntermediates(hit);
      if (counterEl) counterEl.textContent = String(userPath.length);
      const pts = userPath.map((idx) => state.nodeCenters[idx]);
      renderSvgTrail([...pts, pt]);
    });

    zoneEl.addEventListener("pointermove", (e) => {
      if (!isDrawing) return;
      const pt = pointerToLocal(e);
      const hit = hitBolt(pt);
      if (hit >= 0) addBoltWithIntermediates(hit);
      if (counterEl) counterEl.textContent = String(userPath.length);
      const pts = userPath.map((idx) => state.nodeCenters[idx]);
      renderSvgTrail([...pts, pt]);
    });

    function finishUserDraw() {
      if (!isDrawing) return;
      isDrawing = false;
      const pts = userPath.map((idx) => state.nodeCenters[idx]);
      renderSvgTrail(pts);

      if (userPath.length < 6) {
        if (subtitleEl) {
          subtitleEl.textContent = "Connect at least 6 dots";
          subtitleEl.className = "lock-subtitle is-err";
        }
        announceStatus("Connect at least 6 dots");
        window.setTimeout(() => {
          resetLockUI();
          state.userInteracting = false;
          startAutoLoop(state.activeMode);
        }, 1200);
        return;
      }

      const targetMode = resolveDrawnMode(userPath);
      syncPresetButtons(targetMode);
      const cfg = ROOM_MODES[targetMode] || ROOM_MODES.main;
      if (subtitleEl) {
        subtitleEl.textContent = cfg.verifyLabel;
        subtitleEl.className = "lock-subtitle is-ok";
      }
      setDoorStatus(cfg.doorStatus, true);
      announceStatus(`${cfg.doorStatus}: ${cfg.roomTitle}`);
      window.setTimeout(() => {
        screenEl.classList.add("mockup-unlocking");
        window.setTimeout(() => {
          screenEl.classList.remove("mockup-unlocking");
          screenEl.classList.add("mockup-vault");
        }, 700);
      }, 220);
    }

    zoneEl.addEventListener("pointerup", finishUserDraw);
    zoneEl.addEventListener("pointercancel", finishUserDraw);

    if (lockVaultBtn) {
      lockVaultBtn.addEventListener("click", () => {
        stopAutoLoop();
        state.userInteracting = false;
        screenEl.classList.remove("mockup-unlocking", "mockup-vault");
        resetLockUI();
        announceStatus("Vault locked");
        startAutoLoop(state.activeMode);
      });
    }

    if (quickUnlockBtn) {
      quickUnlockBtn.addEventListener("click", () => {
        stopAutoLoop();
        state.userInteracting = true;
        const targetMode = state.userPinnedMode || "main";
        syncPresetButtons(targetMode);
        const cfg = ROOM_MODES[targetMode] || ROOM_MODES.main;
        announceStatus(`Recovery phrase opened ${cfg.roomTitle}`);
        screenEl.classList.add("mockup-unlocking");
        window.setTimeout(() => {
          screenEl.classList.remove("mockup-unlocking");
          screenEl.classList.add("mockup-vault");
        }, 650);
      });
    }

    /* Pause/Resume on Viewport Visibility */
    const heroEl = document.querySelector(".hero");
    if (heroEl && "IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (entries) => {
          state.heroVisible = Boolean(entries[0]?.isIntersecting);
          if (state.heroVisible && !document.hidden && !state.userPaused) {
            scheduleBgTrail();
            startAutoLoop(state.activeMode);
          } else {
            clearTimeout(state.bgTimer);
            stopAutoLoop();
          }
        },
        { threshold: 0.05 }
      );
      io.observe(heroEl);
    }

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        clearTimeout(state.bgTimer);
        stopAutoLoop();
      } else if (state.heroVisible && !state.userPaused) {
        scheduleBgTrail();
        startAutoLoop(state.activeMode);
      }
    });

    syncCanvasColors();
    if (reducedMotion.matches) {
      syncPresetButtons("main");
      screenEl.classList.add("mockup-vault");
    } else {
      scheduleBgTrail();
      startAutoLoop("main");
    }
  }

  initHeroRuntime();

  /* ---------- 5. Competitor Comparison Table Category Filter ---------- */
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

  /* ---------- 6. Native <dialog> Install Modal & Copy Link Actions ---------- */
  const INSTALL_URL = "https://darkroom.buzz/";
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
          installTitle.textContent = ctx === "pro" ? "Install Darkroom Pro" : "Install Darkroom";
        }
        if (installBadge) {
          installBadge.textContent =
            ctx === "pro"
              ? "Darkroom Pro · Family Sharing Included"
              : "For iPhone and iPad · Free plan";
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

  wireCopyButton("copy-app-link", "✓ Link copied");
  wireCopyButton("modal-copy-link-btn", "✓ Link copied");

  /* ---------- 13. Early Tester Beta Waitlist (Google Sheets Webhook) ---------- */
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
      const titleDesc = document.querySelector(".waitlist-success-desc");
      if (titleDesc) {
        titleDesc.innerHTML = `Tap below to install the Darkroom beta with Apple&rsquo;s TestFlight app. We&rsquo;ll send beta news to <code id="registered-email-pill" class="email-pill">${email}</code>.`;
      }
    }

    function renderForm() {
      form.hidden = false;
      successCard.hidden = true;
      form.classList.remove("show-error");
      input.value = "";
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Get the beta</span><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 10h12M11 5l5 5-5 5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
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

      // Loading state on button
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Sending…</span>`;
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

      const record = {
        email: raw,
        createdAt: new Date().toISOString(),
      };

      try {
        localStorage.setItem(storageKey, JSON.stringify(record));
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

    // Smooth scroll and focus for early access links
    document.querySelectorAll('a[href="#waitlist"]').forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        const target = document.getElementById("waitlist");
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          if (!form.hidden) {
            setTimeout(() => input.focus(), 400);
          }
        }
      });
    });
  }

  initEarlyTesterWaitlist();
})();
