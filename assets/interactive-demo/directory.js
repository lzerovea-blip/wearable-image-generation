"use strict";

function createPageDirectory(config, navigate) {
  const rows = new Map(config.pages.map(row => [row.key, row]));
  const previousIds = new Map();
  for (const [previous, key] of Object.entries(config.aliases)) {
    if (!previousIds.has(key)) previousIds.set(key, new Set());
    previousIds.get(key).add(previous.split("/").pop());
  }
  const groups = new Map(config.groups.map(group => [group.id, group]));
  const names = new Map();
  for (const row of rows.values()) {
    const name = row.group + "/" + row.section + "/" + row.title;
    names.set(name, (names.get(name) || 0) + 1);
  }
  const storageKey = "wearable-demo:opening:" + config.id + ":" + location.pathname;
  const pane = document.getElementById("page-directory");
  const search = pane.querySelector("input");
  const list = document.getElementById("directory-results");
  const current = document.getElementById("directory-current");
  const copy = document.getElementById("copy-location");
  const pin = document.getElementById("pin-opening");
  const status = document.getElementById("directory-status");
  const manual = document.getElementById("location-text");
  const links = document.getElementById("module-links");
  const operations = document.getElementById("directory-operations");
  let active, currentGroup = config.default, listing;
  let displayed = new Map();
  const opener = document.getElementById("open-directory");
  opener.hidden = false;
  opener.onclick = () => {
    pane.showModal();
    if (matchMedia("(pointer:fine)").matches) search.focus();
    highlight();
  };
  pane.addEventListener("click", event => {
    if (event.target !== pane) return;
    const rect = pane.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)
      pane.close();
  });
  function select(action) {
    pane.close();
    action();
    document.querySelector(".entry-pane[data-active] .surface")?.focus({preventScroll:true});
  }
  function lookup(featureId, device, page) {
    const key = [featureId, device, page].join("/");
    return rows.get(config.aliases[key] || key);
  }
  function matches(row, query) {
    return config.aliases[query] === row.key || previousIds.get(row.key)?.has(query) ||
      (row.path + " " + row.key).toLocaleLowerCase().includes(query);
  }
  function showResults() {
    const query = search.value.trim().toLocaleLowerCase();
    const scope = query ? "search:" + query : "group:" + currentGroup;
    if (listing === scope) return;
    listing = scope;
    displayed = new Map();
    const fragment = document.createDocumentFragment();
    const sections = new Map();
    for (const row of rows.values()) {
      if (query ? !matches(row, query) : row.group !== currentGroup) continue;
      const title = (query ? groups.get(row.group).label + " › " : "") + row.section;
      let section = sections.get(title);
      if (!section) {
        section = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = title;
        section.append(summary);
        section.open = Boolean(query);
        sections.set(title, section);
        fragment.append(section);
      }
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.location = row.key;
      const sameName = names.get(row.group + "/" + row.section + "/" + row.title) > 1;
      button.textContent = row.title;
      if (sameName) {
        const context = document.createElement("small");
        context.textContent = row.path.split(" › ").slice(2, -1).join(" › ") || row.page;
        button.append(context);
      }
      button.title = row.path + "\n" + row.key;
      section.append(button);
      displayed.set(row.key, button);
    }
    if (!sections.size) fragment.append("没有匹配的界面");
    list.replaceChildren(fragment);
    highlight();
  }
  function highlight() {
    list.querySelector("[aria-current]")?.removeAttribute("aria-current");
    const result = displayed.get(active?.key);
    if (!result) return;
    result.setAttribute("aria-current", "page");
    result.parentElement.open = true;
    if (pane.open && !search.value.trim()) {
      list.scrollTop += result.getBoundingClientRect().top - list.getBoundingClientRect().top - list.clientHeight / 2;
    }
  }
  function activate(row, pageActions = []) {
    active = row;
    const scope = pane.dataset;
    scope.themeFeature = row?.feature || "";
    scope.themeDevice = row?.device || "";
    scope.themePage = row?.key || "";
    current.textContent = row?.path || "请选择界面";
    current.title = row?.key || "";
    copy.disabled = pin.disabled = !row;
    status.textContent = "";
    manual.hidden = true;
    links.replaceChildren();
    if (row) {
      currentGroup = row.group;
      if (search.value && !matches(row, search.value.trim().toLocaleLowerCase())) {
        search.value = "";
      }
      const actions = config.links.filter(link => link.from === row.key).map(link => ({
        label:link.label, title:rows.get(link.to).path, run:() => navigate(rows.get(link.to), true)
      }));
      for (const action of [...actions, ...pageActions]) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = action.label;
        if (action.title) b.title = action.title;
        b.onclick = () => select(action.run);
        links.append(b);
      }
    }
    operations.hidden = !links.childElementCount;
    showResults();
    highlight();
  }
  list.addEventListener("click", event => {
    const item = event.target.closest("[data-location]");
    if (!item) return;
    select(() => navigate(rows.get(item.dataset.location), true));
  });
  search.addEventListener("input", showResults);
  copy.onclick = async () => {
    if (!active) return;
    const value = active.path + "\n" + active.key;
    try {
      await navigator.clipboard.writeText(value);
      status.textContent = "已复制页面定位";
    } catch {
      manual.value = value;
      manual.hidden = false;
      manual.focus();
      manual.select();
      let copied = false;
      try { copied = document.execCommand("copy"); } catch {}
      if (copied) manual.hidden = true;
      status.textContent = copied ? "已复制页面定位" : "请复制下方已选中的页面定位";
    }
  };
  pin.onclick = () => {
    if (!active) return;
    try {
      localStorage.setItem(storageKey, active.key);
      status.textContent = "本机开场已设为「" + active.title + "」";
    } catch { status.textContent = "浏览器未允许保存，本机开场设置失败"; }
  };
  document.getElementById("reset-opening").onclick = () => {
    try {
      localStorage.removeItem(storageKey);
      status.textContent = "已恢复默认开场，下次打开进入运动健康「今日」";
    } catch { status.textContent = "浏览器未允许更改本机开场"; }
  };
  function opening() {
    let key;
    try { key = localStorage.getItem(storageKey); } catch {}
    return rows.get(config.aliases[key] || key) || rows.get(groups.get(config.default).home);
  }
  return {lookup, activate, opening, home: id => rows.get(groups.get(id).home)};
}
