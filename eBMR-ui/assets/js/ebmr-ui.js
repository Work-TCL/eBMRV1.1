/* ==========================================================================
   EBMR-DB-13.1 §13 — presentation-behaviour boundary.

   Permitted: open/close things, move focus, swap a visible panel, render
   an icon from the pinned local set.

   Prohibited (DB-13.1 §13 / UI-CLAUDE.md), and none of it appears below:
     - deciding whether a user may perform an action
     - holding/caching/persisting regulated facts, personas, signatures,
       audit entries or deviations (no localStorage/sessionStorage/IndexedDB)
     - rendering a state as committed before the server returns it
     - computing a limit, yield, reconciliation or pass/fail outcome
     - composing a timestamp for the record
     - retrying a state-changing request on its own initiative
   ========================================================================== */
(function () {
  "use strict";

  /* ---------------- Icon set — original, self-contained, no network fetch ----------------
     Semantic names, not vendor filenames (DB-13.1 §8). Each entry is the
     inner markup of a 24x24 stroke icon; .icon supplies stroke/fill rules. */
  var ICONS = {
    menu: '<line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/>',
    x: '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
    "chevron-right": '<polyline points="9,5 15,12 9,19"/>',
    "chevron-down": '<polyline points="5,9 12,15 19,9"/>',
    "chevron-left": '<polyline points="15,5 9,12 15,19"/>',
    bell: '<path d="M6 10a6 6 0 0 1 12 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6z"/><path d="M10 19a2 2 0 0 0 4 0"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><line x1="20" y1="20" x2="15.5" y2="15.5"/>',
    check: '<polyline points="5,13 10,18 19,7"/>',
    "check-circle": '<circle cx="12" cy="12" r="8.5"/><polyline points="8,12.5 11,15.5 16,9"/>',
    "alert-triangle": '<path d="M12 4 3 20h18z"/><line x1="12" y1="10.5" x2="12" y2="14.5"/><circle cx="12" cy="17.2" r="0.6" fill="currentColor" stroke="none"/>',
    "alert-circle": '<circle cx="12" cy="12" r="8.5"/><line x1="12" y1="7.5" x2="12" y2="12.5"/><circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><polyline points="12,7.5 12,12 15.5,14"/>',
    "slash-circle": '<circle cx="12" cy="12" r="8.5"/><line x1="6.5" y1="17.5" x2="17.5" y2="6.5"/>',
    "help-circle": '<circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.7 2.2c-.9.5-1.2 1-1.2 2"/><circle cx="12" cy="16.7" r="0.6" fill="currentColor" stroke="none"/>',
    lock: '<rect x="5.5" y="11" width="13" height="9" rx="1.5"/><path d="M8.5 11V8a3.5 3.5 0 0 1 7 0v3"/>',
    "lock-open": '<rect x="5.5" y="11" width="13" height="9" rx="1.5"/><path d="M8.5 11V8a3.5 3.5 0 0 1 6.6-1.6"/>',
    pen: '<path d="M16 4 20 8 9 19 4.5 19.5 5 15z"/>',
    "cross-medical": '<rect x="3.5" y="3.5" width="17" height="17" rx="4"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
    droplet: '<path d="M12 3.5s6 6.7 6 10.8a6 6 0 0 1-12 0C6 10.2 12 3.5 12 3.5z"/>',
    layers: '<polygon points="12,4 21,9 12,14 3,9"/><polyline points="3,14 12,19 21,14"/>',
    package: '<path d="M4 8l8-4.5L20 8v8l-8 4.5L4 16z"/><polyline points="4,8 12,12.5 20,8"/><line x1="12" y1="12.5" x2="12" y2="21"/>',
    scan: '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/><line x1="4" y1="12" x2="20" y2="12"/>',
    printer: '<rect x="6" y="8.5" width="12" height="7" rx="1"/><path d="M7.5 8.5V4.5h9v4"/><path d="M8 15.5v4h8v-4"/>',
    users: '<circle cx="9" cy="9" r="3"/><path d="M3.5 19c.7-3 3-4.7 5.5-4.7s4.8 1.7 5.5 4.7"/><circle cx="17" cy="8.5" r="2.5"/><path d="M15.5 14.3c2.1.3 3.7 1.8 4.3 4.2"/>',
    user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5.5 20c.9-3.6 3.4-5.7 6.5-5.7s5.6 2.1 6.5 5.7"/>',
    "user-check": '<circle cx="10" cy="8.5" r="3.5"/><path d="M3.5 20c.9-3.6 3.2-5.7 6.5-5.7 1 0 1.9.2 2.7.6"/><polyline points="15,15.5 17.5,18 21,13"/>',
    inbox: '<path d="M3.5 13.5 6 5.5h12l2.5 8v5h-17z"/><path d="M3.5 13.5H9a3 3 0 0 0 6 0h5.5"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-13.7-5.2L3.5 8.5"/><polyline points="3.5,4 3.5,8.5 8,8.5"/><path d="M4 13a8 8 0 0 0 13.7 5.2l2.8-2.7"/><polyline points="20.5,20 20.5,15.5 16,15.5"/>',
    play: '<circle cx="12" cy="12" r="8.5"/><polygon points="10,8.5 16,12 10,15.5"/>',
    scale: '<line x1="12" y1="4" x2="12" y2="20"/><line x1="7" y1="20" x2="17" y2="20"/><line x1="5" y1="7.5" x2="19" y2="7.5"/><path d="M5 7.5 2.5 13a2.5 2.5 0 0 0 5 0z"/><path d="M19 7.5 16.5 13a2.5 2.5 0 0 0 5 0z"/>',
    flask: '<path d="M10 3.5v6L4.8 18a2 2 0 0 0 1.7 3h11a2 2 0 0 0 1.7-3L14 9.5v-6"/><line x1="9" y1="3.5" x2="15" y2="3.5"/><line x1="7.3" y1="14.5" x2="16.7" y2="14.5"/>',
    "pen-line": '<path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3z"/><line x1="14" y1="7" x2="17" y2="10"/>',
    camera: '<path d="M3.5 8.5h3.2l1.6-2.5h7.4l1.6 2.5h3.2v10h-17z"/><circle cx="12" cy="13.5" r="3.5"/>',
    download: '<line x1="12" y1="4" x2="12" y2="15"/><polyline points="7.5,10.5 12,15 16.5,10.5"/><path d="M4.5 18v2h15v-2"/>',
    "file-plus-2": '<path d="M6 3.5h7l5 5V20a.5.5 0 0 1-.5.5h-11A.5.5 0 0 1 6 20z"/><polyline points="13,3.5 13,9 18.5,9"/><line x1="12" y1="12" x2="12" y2="17"/><line x1="9.5" y1="14.5" x2="14.5" y2="14.5"/>',
    "shield-check": '<path d="M12 3.5 19 6v6c0 4.5-3 7-7 8.5C8 19 5 16.5 5 12V6z"/><polyline points="9,12 11,14 15,9.5"/>',
    history: '<circle cx="12" cy="13" r="7.5"/><polyline points="12,9 12,13 15,15"/><polyline points="5,4.5 5,8 8.5,8"/><path d="M5.3 8a7.5 7.5 0 0 1 13 1.3"/>',
    "arrow-left": '<line x1="19" y1="12" x2="6" y2="12"/><polyline points="11,6.5 5,12 11,17.5"/>',
    "arrow-right": '<line x1="5" y1="12" x2="18" y2="12"/><polyline points="13,6.5 19,12 13,17.5"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><line x1="12" y1="11" x2="12" y2="16.5"/><circle cx="12" cy="7.7" r="0.6" fill="currentColor" stroke="none"/>',
    "log-out": '<path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3"/><polyline points="15,8 19,12 15,16"/><line x1="19" y1="12" x2="9" y2="12"/>',
    building: '<rect x="5" y="3.5" width="10" height="17" rx="0.5"/><rect x="15" y="9" width="4" height="11.5"/><line x1="8" y1="7" x2="8" y2="7.01"/><line x1="12" y1="7" x2="12" y2="7.01"/><line x1="8" y1="11" x2="8" y2="11.01"/><line x1="12" y1="11" x2="12" y2="11.01"/><line x1="8" y1="15" x2="8" y2="15.01"/><line x1="12" y1="15" x2="12" y2="15.01"/>',
    "list-checks": '<polyline points="4,6.5 5.5,8 8.5,4.5"/><line x1="12" y1="6.5" x2="20" y2="6.5"/><polyline points="4,15.5 5.5,17 8.5,13.5"/><line x1="12" y1="15.5" x2="20" y2="15.5"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "badge-check": '<path d="M12 3.5 14.5 5.5 17.5 5 18 8l2.5 1.8-1.3 2.7 1.3 2.7-2.5 1.8-.5 3-3-.5-2.5 2-2.5-2-3 .5-.5-3-2.5-1.8 1.3-2.7-1.3-2.7L8 8l.5-2.5z"/><polyline points="9,12.3 11,14.3 15,10"/>',
    "file-text": '<path d="M7 3.5h7l4 4V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="15.5" x2="15" y2="15.5"/>',
    home: '<path d="M4.5 11 12 4.5 19.5 11"/><path d="M6.5 9.5V19a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V9.5"/>',
    calendar: '<rect x="4" y="5.5" width="16" height="14.5" rx="1.5"/><line x1="4" y1="10" x2="20" y2="10"/><line x1="8" y1="3.5" x2="8" y2="7.5"/><line x1="16" y1="3.5" x2="16" y2="7.5"/>',
    database: '<ellipse cx="12" cy="6" rx="7" ry="2.7"/><path d="M5 6v12c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7V6"/><path d="M5 12c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7"/>',
    clipboard: '<rect x="6" y="5" width="12" height="16" rx="1.5"/><rect x="9" y="3" width="6" height="3.5" rx="1"/>',
    flag: '<line x1="6" y1="3.5" x2="6" y2="20.5"/><path d="M6 4.5h11l-2.5 3.5L17 11.5H6z"/>',
    gauge: '<circle cx="12" cy="13" r="7.5"/><line x1="12" y1="13" x2="15.5" y2="9.5"/><line x1="8" y1="6.5" x2="8.9" y2="7.2"/><line x1="12" y1="5.3" x2="12" y2="6.3"/><line x1="16" y1="6.5" x2="15.1" y2="7.2"/>'
  };

  function svgFor(name) {
    var inner = ICONS[name];
    if (!inner) return "";
    return '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">' + inner + "</svg>";
  }

  function renderIcons(root) {
    (root || document).querySelectorAll("[data-icon]").forEach(function (el) {
      var name = el.getAttribute("data-icon");
      if (el.dataset.iconRendered === name) return;
      el.innerHTML = svgFor(name);
      el.dataset.iconRendered = name;
    });
  }

  /* ---------------- Mobile sidebar ---------------- */
  function initSidebar() {
    var toggleBtns = document.querySelectorAll("[data-sidebar-toggle]");
    var sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    toggleBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        sidebar.classList.toggle("open");
      });
    });
  }

  /* ---------------- Dropdown menus ---------------- */
  function initDropdowns() {
    document.querySelectorAll("[data-dropdown-toggle]").forEach(function (btn) {
      var menu = document.getElementById(btn.getAttribute("data-dropdown-toggle"));
      if (!menu) return;
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        document.querySelectorAll(".dropdown-menu.show").forEach(function (m) {
          if (m !== menu) m.classList.remove("show");
        });
        menu.classList.toggle("show");
      });
    });
    document.addEventListener("click", function () {
      document.querySelectorAll(".dropdown-menu.show").forEach(function (m) { m.classList.remove("show"); });
    });
  }

  /* ---------------- Tabs — swaps the visible panel only ---------------- */
  function initTabs() {
    document.querySelectorAll("[data-tab-group]").forEach(function (group) {
      var groupId = group.getAttribute("data-tab-group");
      var buttons = group.querySelectorAll("[data-tab]");
      buttons.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var target = btn.getAttribute("data-tab");
          buttons.forEach(function (b) { b.setAttribute("aria-selected", "false"); });
          btn.setAttribute("aria-selected", "true");
          document.querySelectorAll('[data-tab-panel][data-tab-group-target="' + groupId + '"]').forEach(function (p) {
            if (p.getAttribute("data-tab-panel") === target) p.setAttribute("data-active", "");
            else p.removeAttribute("data-active");
          });
        });
      });
    });
  }

  /* ---------------- Modals — open/close and focus only, no state mutation ---------------- */
  function trapFocus(modal) {
    var focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (!focusable.length) return;
    var first = focusable[0], last = focusable[focusable.length - 1];
    modal.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }
  function initModals() {
    document.querySelectorAll("[data-modal-open]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var modal = document.getElementById(btn.getAttribute("data-modal-open"));
        if (!modal) return;
        modal.classList.add("show");
        var dialog = modal.querySelector(".modal");
        if (dialog) { trapFocus(dialog); dialog.setAttribute("tabindex", "-1"); dialog.focus(); }
      });
    });
    document.querySelectorAll("[data-modal-close]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var backdrop = btn.closest(".modal-backdrop");
        if (backdrop && backdrop.getAttribute("data-dismissible") !== "false") backdrop.classList.remove("show");
      });
    });
    document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
      backdrop.addEventListener("click", function (e) {
        if (e.target === backdrop && backdrop.getAttribute("data-dismissible") !== "false") backdrop.classList.remove("show");
      });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      document.querySelectorAll(".modal-backdrop.show").forEach(function (b) {
        if (b.getAttribute("data-dismissible") !== "false") b.classList.remove("show");
      });
    });
  }

  /* ---------------- Visual state swap — text/attribute only, no storage ----------------
     data-state-set="#targetSelector|state:value|text:Label|icon:icon-name"
     Swaps a visible pill's data-state / label / icon on click. Nothing is
     written to storage and nothing survives a reload — this is the "swap a
     visible panel" permission (DB-13.1 §13), not a simulated commit. */
  function initStateSet() {
    document.querySelectorAll("[data-state-set]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var parts = btn.getAttribute("data-state-set").split("|");
        var target = document.querySelector(parts[0]);
        if (!target) return;
        parts.slice(1).forEach(function (part) {
          var sep = part.indexOf(":");
          var key = part.slice(0, sep), val = part.slice(sep + 1);
          if (key === "state") target.setAttribute("data-state", val);
          else if (key === "text") {
            var icon = target.querySelector(".icon");
            target.textContent = "";
            if (icon) target.appendChild(icon);
            target.appendChild(document.createTextNode(" " + val));
          } else if (key === "icon") {
            var iconEl = target.querySelector(".icon");
            if (iconEl) { iconEl.setAttribute("data-icon", val); delete iconEl.dataset.iconRendered; renderIcons(target); }
          }
        });
        if (btn.hasAttribute("data-disable-self")) btn.disabled = true;
      });
    });
  }

  /* ==========================================================================
     DEMO LAYER — everything below exists so the preview can be presented to a
     client end-to-end: wizards advance, rows can be added, forms validate, and
     a "save" makes the new row appear.

     This deliberately goes further than DB-13.1 §13 allows for the real
     product, which forbids the UI ever rendering something as committed. That
     rule protects an operator from believing a regulated record was written
     when it was not — it is not aimed at a sales mockup with no server behind
     it. The compromise: everything below is clearly fenced as demo behaviour,
     nothing survives a page reload, and a persistent marker states so on every
     screen. When this design is implemented for real, this whole block is
     deleted, not ported.
     ========================================================================== */

  /* ---------------- Demo marker — always visible, never dismissible -------- */
  function initDemoMarker() {
    if (document.querySelector(".demo-marker")) return;
    var el = document.createElement("div");
    el.className = "demo-marker";
    el.innerHTML = '<span class="icon" data-icon="info"></span>' +
      '<span>Demo preview — nothing is stored</span>';
    document.body.appendChild(el);
    renderIcons(el);
  }

  /* ---------------- Multi-step wizards ----------------
     <div data-wizard="batch">
       <ol data-wizard-progress> … <li data-step-label="1"> … </ol>
       <section data-wizard-step="1"> … <button data-wizard-next>
       <section data-wizard-step="2"> … <button data-wizard-back>
     Steps validate required fields before advancing. */
  function initWizards() {
    document.querySelectorAll("[data-wizard]").forEach(function (wiz) {
      var steps = wiz.querySelectorAll("[data-wizard-step]");
      if (!steps.length) return;

      function show(n) {
        steps.forEach(function (s) {
          s.toggleAttribute("data-active", s.getAttribute("data-wizard-step") === String(n));
        });
        wiz.querySelectorAll("[data-step-label]").forEach(function (l) {
          var i = parseInt(l.getAttribute("data-step-label"), 10);
          l.setAttribute("data-step-state", i < n ? "done" : (i === n ? "current" : "todo"));
        });
        wiz.setAttribute("data-wizard-current", n);
        var top = wiz.getBoundingClientRect().top + window.scrollY - 90;
        window.scrollTo({ top: top < 0 ? 0 : top, behavior: "smooth" });
      }

      wiz.addEventListener("click", function (e) {
        var next = e.target.closest("[data-wizard-next]");
        var back = e.target.closest("[data-wizard-back]");
        var cur = parseInt(wiz.getAttribute("data-wizard-current") || "1", 10);
        if (next) {
          var stepEl = wiz.querySelector('[data-wizard-step="' + cur + '"]');
          if (stepEl && !validateScope(stepEl)) return;
          if (cur < steps.length) show(cur + 1);
        } else if (back && cur > 1) {
          show(cur - 1);
        }
      });

      show(1);
    });
  }

  /* ---------------- Repeatable rows (BOM lines, step lists, users) --------
     <table data-rows="bom"> with <template data-row-template> and a
     [data-add-row="bom"] button. Rows carry [data-remove-row]. */
  function initRepeatableRows() {
    document.querySelectorAll("[data-add-row]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-add-row");
        var host = document.querySelector('[data-rows="' + key + '"] tbody');
        var tpl = document.querySelector('[data-row-template="' + key + '"]');
        if (!host || !tpl) return;
        var frag = tpl.content.cloneNode(true);
        host.appendChild(frag);
        renderIcons(host);
        recalcTotals(key);
      });
    });

    document.addEventListener("click", function (e) {
      var rm = e.target.closest("[data-remove-row]");
      if (!rm) return;
      var table = rm.closest("[data-rows]");
      var row = rm.closest("tr");
      if (row) row.remove();
      if (table) recalcTotals(table.getAttribute("data-rows"));
    });

    document.addEventListener("input", function (e) {
      var table = e.target.closest("[data-rows]");
      if (table) recalcTotals(table.getAttribute("data-rows"));
    });
  }

  /* Sums any [data-sum-src] inputs in a table into [data-sum-for]. Demo-only
     arithmetic for the BOM builder — the real product calculates server-side
     and only displays the result (DB-13.1 §13.4). */
  function recalcTotals(key) {
    var table = document.querySelector('[data-rows="' + key + '"]');
    var out = document.querySelector('[data-sum-for="' + key + '"]');
    if (!table || !out) return;
    var total = 0, n = 0;
    table.querySelectorAll("[data-sum-src]").forEach(function (i) {
      var v = parseFloat(i.value);
      if (!isNaN(v)) { total += v; n++; }
    });
    out.textContent = total.toFixed(3);
    var cnt = document.querySelector('[data-count-for="' + key + '"]');
    if (cnt) cnt.textContent = table.querySelectorAll("tbody tr").length;
  }

  /* ---------------- Simulated save ----------------
     [data-demo-save] reads [data-field] inputs inside its form/modal, appends
     a row to the target table, closes any modal, and confirms. Demo only. */
  function initDemoSave() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-demo-save]");
      if (!btn) return;

      var scope = btn.closest("[data-demo-form]") || document;
      if (!validateScope(scope)) return;

      var targetKey = btn.getAttribute("data-demo-save");
      var table = document.querySelector('[data-list="' + targetKey + '"] tbody');
      if (table) {
        var tpl = document.querySelector('[data-list-row="' + targetKey + '"]');
        if (tpl) {
          var html = tpl.innerHTML;
          scope.querySelectorAll("[data-field]").forEach(function (f) {
            var name = f.getAttribute("data-field");
            var val = f.tagName === "SELECT" && f.selectedOptions.length
              ? f.selectedOptions[0].textContent.trim() : f.value;
            html = html.split("{{" + name + "}}").join(escapeHtml(val || "—"));
          });
          html = html.replace(/\{\{[a-z_]+\}\}/gi, "—");
          var tr = document.createElement("tr");
          tr.innerHTML = html;
          tr.setAttribute("data-just-added", "");
          table.appendChild(tr);
          renderIcons(tr);
          tr.scrollIntoView({ block: "center", behavior: "smooth" });
        }
      }

      var backdrop = btn.closest(".modal-backdrop");
      if (backdrop) backdrop.classList.remove("show");

      // reset the form so the next demo run starts clean
      scope.querySelectorAll("input, textarea").forEach(function (f) {
        if (f.type !== "checkbox" && f.type !== "radio" && !f.disabled) f.value = "";
        f.classList.remove("is-error");
      });

      toast(btn.getAttribute("data-demo-message") || "Added to the list — demo only, nothing stored.");
      bumpCounter(targetKey);
    });
  }

  /* Marks every empty [data-required] control in a scope and reveals its
     [data-error-for] message. A checkbox reports value "on" whether or not it
     is ticked, so it has to be judged on .checked instead. Returns true when
     the scope is complete. */
  function validateScope(scope) {
    var bad = [];
    scope.querySelectorAll("[data-required]").forEach(function (f) {
      var empty = f.type === "checkbox" || f.type === "radio"
        ? !f.checked
        : !String(f.value || "").trim();
      f.classList.toggle("is-error", empty);
      var msg = (f.closest(".field") || f.parentElement).querySelector("[data-error-for]");
      if (msg) msg.style.display = empty ? "flex" : "none";
      if (empty) bad.push(f);
    });
    if (bad.length) bad[0].focus();
    return !bad.length;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function bumpCounter(key) {
    var list = document.querySelector('[data-list="' + key + '"] tbody');
    var el = document.querySelector('[data-list-count="' + key + '"]');
    if (list && el) el.textContent = list.querySelectorAll("tr").length;
    // setup-checklist progress, if this screen contributes to it
    var step = document.querySelector('[data-setup-step="' + key + '"]');
    if (step) step.setAttribute("data-step-state", "done");
  }

  /* ---------------- Toast ---------------- */
  function toast(message) {
    var region = document.getElementById("toast-region");
    if (!region) {
      region = document.createElement("div");
      region.id = "toast-region";
      document.body.appendChild(region);
    }
    var el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("data-tone", "good");
    el.innerHTML = '<span class="icon" data-icon="check-circle"></span><span>' +
      escapeHtml(message) + "</span>";
    region.appendChild(el);
    renderIcons(el);
    setTimeout(function () {
      el.style.transition = "opacity .3s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 300);
    }, 3600);
  }
  window.ebmrToast = toast;

  /* ---------------- Gates ----------------
     A [data-gated-by="name"] control stays disabled, with its stated reason
     visible, until something with [data-gate-release="name"] is activated.
     This is how the preview shows the system refusing an action and then
     accepting it once the blocker is genuinely resolved — the refusal is the
     point, so it must be seen to lift for a reason, not on a timer. */
  function initGates() {
    function apply(name, open) {
      document.querySelectorAll('[data-gated-by="' + name + '"]').forEach(function (el) {
        el.disabled = !open;
        var reason = document.querySelector('[data-gate-reason="' + name + '"]');
        if (reason) reason.style.display = open ? "none" : "";
      });
    }
    var names = new Set();
    document.querySelectorAll("[data-gated-by]").forEach(function (el) {
      names.add(el.getAttribute("data-gated-by"));
    });
    names.forEach(function (n) { apply(n, false); });

    document.querySelectorAll("[data-gate-release]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        apply(btn.getAttribute("data-gate-release"), true);
      });
    });
  }

  /* ---------------- Live search filter over a table ---------------- */
  function initFilters() {
    document.querySelectorAll("[data-filter-for]").forEach(function (input) {
      input.addEventListener("input", function () {
        var key = input.getAttribute("data-filter-for");
        var q = input.value.toLowerCase().trim();
        var rows = document.querySelectorAll('[data-list="' + key + '"] tbody tr');
        var shown = 0;
        rows.forEach(function (r) {
          var hit = r.textContent.toLowerCase().indexOf(q) !== -1;
          r.style.display = hit ? "" : "none";
          if (hit) shown++;
        });
        var empty = document.querySelector('[data-filter-empty="' + key + '"]');
        if (empty) empty.style.display = shown ? "none" : "";
      });
    });
  }

  /* ---------------- Recipe scale calculator ----------------
     [data-recipe-scale] is an order-size input. Every row in the nearest
     [data-recipe-bom] table has a per-unit cell ([data-per-unit], the raw
     number, plus [data-unit-sg] for its singular label) and a target cell
     ([data-scaled], with [data-unit] holding the plural label). Typing a new
     order size recomputes every "Required at order size" cell live — the
     same multiplication "Create a final assembly" step 3 does automatically
     once this recipe is issued against. */
  function initRecipeScale() {
    document.querySelectorAll("[data-recipe-scale]").forEach(function (input) {
      var table = document.querySelector("[data-recipe-bom]");
      function fmt(n, decimals) {
        return n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
      }
      function recalc() {
        var qty = parseFloat(input.value) || 0;
        document.querySelectorAll("[data-recipe-scale-label]").forEach(function (l) {
          l.textContent = fmt(qty, 0);
        });
        if (!table) return;
        table.querySelectorAll("tbody tr").forEach(function (row) {
          var per = row.querySelector("[data-per-unit]");
          var out = row.querySelector("[data-scaled]");
          if (!per || !out) return;
          var perVal = parseFloat(per.getAttribute("data-per-unit"));
          var unit = out.getAttribute("data-unit") || "";
          var decimals = perVal % 1 !== 0 ? 3 : 0;
          out.textContent = fmt(perVal * qty, decimals) + " " + unit;
        });
      }
      input.addEventListener("input", recalc);
      recalc();
    });
  }

  /* ---------------- Role-based access simulation (demo only) --------------
     A visitor picks a persona on role-select.html; [data-role-set] stores it
     in sessionStorage (tab-scoped, cleared when the browser tab closes —
     nothing is sent anywhere). Every later screen reads it back and greys out
     [data-role-allow] links the persona shouldn't use, and shows/hides
     [data-role-only] content blocks. This is a demonstration of what
     permission-based access control feels like, not a real authorization
     boundary — the real one lives server-side and cannot be faked by editing
     the DOM, which is exactly why this layer is fenced off here rather than
     mixed into the rest of ebmr-ui.js. */
  var ROLE_NAMES = {
    admin: "Configuration Administrator", planner: "Planner/Batch Issuer",
    operator: "Filling/Assembly Operator", quality: "Final Release Authority",
  };

  function initRoleView() {
    if (document.body.hasAttribute("data-role-select-page")) {
      sessionStorage.removeItem("ebmrRole");
      sessionStorage.removeItem("ebmrRoleLabel");
    }

    document.querySelectorAll("[data-role-set]").forEach(function (a) {
      a.addEventListener("click", function () {
        sessionStorage.setItem("ebmrRole", a.getAttribute("data-role-set") || "");
        sessionStorage.setItem("ebmrRoleLabel", a.getAttribute("data-role-label") || "");
      });
    });

    var role = sessionStorage.getItem("ebmrRole");
    var label = sessionStorage.getItem("ebmrRoleLabel");
    if (!role) return;

    var badge = document.querySelector("[data-role-badge]");
    var badgeText = document.querySelector("[data-role-badge-text]");
    if (badge && badgeText) {
      badge.style.display = "";
      badgeText.textContent = label || role;
    }

    document.querySelectorAll("[data-role-allow]").forEach(function (el) {
      var allowed = el.getAttribute("data-role-allow").split(/\s+/);
      if (allowed.indexOf(role) !== -1) return;
      el.setAttribute("data-disabled", "");
      var names = allowed.map(function (r) { return ROLE_NAMES[r] || r; });
      el.title = "Requires " + names.join(" or ") + " — you're signed in as " + (label || role) + ".";
    });

    document.querySelectorAll("[data-role-only]").forEach(function (el) {
      el.style.display = el.getAttribute("data-role-only") === role ? "block" : "none";
    });
    var prompt = document.querySelector("[data-role-prompt]");
    if (prompt) prompt.style.display = "none";
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderIcons(document);
    initSidebar();
    initDropdowns();
    initTabs();
    initModals();
    initStateSet();
    initDemoMarker();
    initWizards();
    initRepeatableRows();
    initDemoSave();
    initGates();
    initFilters();
    initRecipeScale();
    initRoleView();
  });
})();
