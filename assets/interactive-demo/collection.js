"use strict";

// Each checked entry owns a player. Unchecking hides its view, preserving the
// navigation stack and scroll position for the next time it is shown.
function createCollectionWorkspace(config, main, createPlayer) {
  const directory = createPageDirectory(config, showPage);
  const chooser = document.getElementById("entry-chooser");
  const summary = chooser.querySelector("summary");
  const options = chooser.querySelector("fieldset");
  const items = new Map();
  const selected = new Set();
  const maxEntries = 3;
  let active;

  function activate(item) {
    if (!selected.has(item.id)) return;
    if (active !== item) {
      active?.section.removeAttribute("data-active");
      active = item;
      item.section.dataset.active = "";
    }
    if (item.row) directory.activate(item.row, item.actions);
  }

  function updateSelection() {
    main.style.setProperty("--entry-count", selected.size);
    main.classList.toggle("multiple-entries", selected.size > 1);
    for (const item of items.values()) {
      item.input.checked = selected.has(item.id);
      item.input.disabled = item.input.checked ? selected.size === 1 : selected.size >= maxEntries;
      item.section.hidden = !item.input.checked;
    }
    const names = [...items.values()].filter(item => item.input.checked).map(item => item.label);
    summary.textContent = names.length === 1 ? names[0] : "已选 " + names.length + " 项";
    summary.title = names.join("、");
    summary.setAttribute("aria-label", "选择展示入口，当前显示" + summary.title);
  }

  function ensurePlayer(item, openHome = true) {
    if (item.player) return;
    item.player = createPlayer(item.viewport, {
      directory, status:item.status,
      setLocation(row, actions) {
        item.row = row;
        item.actions = actions;
        if (active === item) directory.activate(row, actions);
      },
      follow: showPage,
    });
    if (openHome) item.player.visitPage(directory.home(item.id));
  }

  function reveal(item, openHome = true) {
    if (!selected.has(item.id)) {
      if (selected.size === 1 || selected.size >= maxEntries) selected.delete(active.id);
      selected.add(item.id);
      updateSelection();
    }
    ensurePlayer(item, openHome);
    activate(item);
  }

  function focusView(item) {
    item.viewport.querySelector(".surface")?.focus({preventScroll:true});
    if (selected.size > 1) item.section.scrollIntoView({block:"nearest"});
  }

  function showPage(row, remember = false) {
    const origin = active;
    const dest = items.get(row.group);
    reveal(dest, remember);
    const resume = remember && origin && origin !== dest ? () => {
      reveal(origin);
      focusView(origin);
    } : null;
    dest.player.visitPage(row, remember, resume);
    if (remember) focusView(dest);
  }

  for (const group of config.groups) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = group.id;
    label.append(input, group.label);
    options.append(label);
    const section = document.createElement("section");
    section.className = "entry-pane";
    section.dataset.group = group.id;
    section.setAttribute("aria-label", group.label);
    section.hidden = true;
    const title = document.createElement("h2");
    title.className = "entry-name";
    title.textContent = group.label;
    const viewport = document.createElement("div");
    viewport.className = "entry-viewport";
    const status = document.createElement("output");
    status.className = "entry-status";
    status.setAttribute("aria-live", "polite");
    section.append(title, viewport, status);
    main.append(section);
    const item = {id:group.id, label:group.label, section, viewport, status, input};
    items.set(item.id, item);
    for (const event of ["pointerdown", "focusin", "wheel"]) {
      section.addEventListener(event, () => { if (active !== item) activate(item); }, {capture:true, passive:true});
    }
    input.onchange = () => {
      if (input.checked) {
        selected.add(item.id);
        updateSelection();
        ensurePlayer(item);
        activate(item);
      } else {
        if (selected.size > 1) selected.delete(item.id);
        updateSelection();
        if (!selected.has(active.id)) activate(items.get(selected.values().next().value));
      }
    };
  }
  document.addEventListener("pointerdown", event => {
    if (chooser.open && !chooser.contains(event.target)) chooser.open = false;
  });
  chooser.addEventListener("keydown", event => {
    if (chooser.open && event.key === "Escape") {
      chooser.open = false;
      summary.focus();
      event.preventDefault();
    }
  });
  chooser.hidden = false;
  showPage(directory.opening());
  return {directory, showPage, activePlayer: () => active.player};
}
