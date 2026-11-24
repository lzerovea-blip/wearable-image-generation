"use strict";
const { features, media, reports = [], navigation, wristLauncher } = JSON.parse(document.getElementById("demo-data").textContent);
const nav = document.getElementById("scenes");
const picker = document.getElementById("feature");
const appNames = [...new Set(features.map(f => f.appName).filter(Boolean))];
const multiApp = appNames.length > 1;
const systemNames = {
  "@face": "表盘",
  "@launcher": "应用列表",
  "@minus": "负一屏",
  "@cards": "超级卡片",
  "@home": "健康首页",
  "@summary": "健康摘要",
};
const systemParent = { "@launcher": "@face", "@minus": "@face", "@cards": "@face", "@summary": "@home" };
const models = { watch: "HUAWEI WATCH 5", phone: "HUAWEI Pura 70 Pro" };

function createDemoPlayer(main, context) {
  let feature = features[0],
    scene = null,
    devices = {};
  const directory = context?.directory;
  const phoneActions = context ? document.createElement("div") : document.getElementById("phone-actions");
  phoneActions.classList.add("device-controls");
  const timers = {};
  function syncPicker() {
    if (!context) picker.value = feature.id;
  }
  function visitPage(row, remember = false, resume = null) {
    const sourceDevice = Object.keys(devices)[0];
    const origin = {feature, scene, devices};
    const scroll = activeScroller(main.querySelector(".surface"))?.scrollTop || 0;
    if (remember && !resume && feature.id === row.feature && devices[row.device]?.id === row.page) {
      if (watchScrollLayout(row.device, row.page)) refreshDevice(row.device);
      return;
    }
    feature = features.find(f => f.id === row.feature);
    selectScene(row.scene, [row.device, row.page], remember);
    if (remember) {
      devices[row.device].trail = [{origin, device:sourceDevice, scroll, resume}];
      refreshDevice(row.device);
    }
  }
  const savedRoutes = new Map();
  const flowValues = new Map();
  function flowState() {
    if (!flowValues.has(feature.id)) flowValues.set(feature.id, {...feature.flowDefaults});
    return flowValues.get(feature.id);
  }
  function flowText(text) {
    return String(text || "").replace(/\{([a-z]+)\}/g, (_, key) => flowState()[key] ?? "—");
  }
  function watchFlow(page) {
    const flow = page.watchFlow;
    const state = flowState();
    const actions = (flow.actions || []).filter(a => !a.related || features.some(f => f.id === a.related))
      .filter(a => !a.when || Object.entries(a.when).every(([k,v]) => state[k] === v))
      .map(a => {
        const attrs = a.related ? 'data-related="' + e(a.related) + '" data-destination="' + e(a.page) + '"' :
          a.page === "@back" ? 'data-control="back"' : 'data-page="' + e(a.page) + '"';
        return button(flowText(a.label), attrs + (a.set ? ' data-assign="' + e(JSON.stringify(a.set)) + '"' : '') +
          (a.increment ? ' data-increment="' + e(JSON.stringify(a.increment)) + '"' : ''), "flow-choice");
      }).join("");
    let calendar = "";
    if (flow.calendar) {
      const cursor = new Date((state.month || "2026-11") + "-01T12:00:00");
      const count = new Date(cursor.getFullYear(), cursor.getMonth()+1, 0).getDate();
      const month = cursor.getFullYear() + "-" + String(cursor.getMonth()+1).padStart(2, "0");
      const days = Array.from({length:count}, (_, i) => {
        const date = month + "-" + String(i+1).padStart(2,"0");
        return button(i+1,'data-date="' + date + '" aria-pressed="' + (date === state.date) + '"');
      }).join("");
      calendar = '<div class="month-nav">' + button("‹",'data-month="-1" aria-label="上个月"') + e(month) +
        button("›",'data-month="1" aria-label="下个月"') + '</div><div class="flow-calendar">' +
        "日一二三四五六".split("").map(x=>'<small>'+x+'</small>').join("") +
        "<i></i>".repeat(cursor.getDay()) + days + '</div>';
    }
    const title = '<h2>' + e(page.title) + '</h2>';
    const art = page.cover ? imageTag(feature.media[page.cover], "flow-art", "") : "";
    const metric = flow.value ? '<strong class="flow-metric' + (flow.ring ? " flow-ring" : "") + '">' + e(flowText(flow.value)) + '</strong>' : "";
    const note = flow.text ? '<p>' + e(flowText(flow.text)) + '</p>' : "";
    return '<div class="scroll wrist-flow tone-' + e(flow.color || "teal") + '">' + title + art + metric + calendar + note + actions + '</div>';
  }
  function resolvedPage(page) {
    return savedRoutes.get(feature.id)?.get(page) || page;
  }
  let enlargedPhone = false;
  const escapeText = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const e = escapeText;
  function icon(name) {
    const paths = {
      overview:
        '<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
      watch: '<rect x="5" y="5" width="14" height="14" rx="6"/><path d="M9 5V2h6v3m-6 14v3h6v-3m-3-10v3l2 1"/>',
      phone: '<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 5h2m-2 14h2"/>',
      arrow: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
      back: '<path d="m14 5-7 7 7 7"/>',
      scene: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="m10 9 5 3-5 3z"/>',
      today: '<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4m8-4v4M5 10h14m-10 4h6"/>',
      exercise: '<circle cx="15" cy="4" r="1.7"/><path d="m6 11 5-4 4 4 4 1m-8-4-2 7 5 2 1 5m-5-9-3 5-5 2"/>',
      user: '<circle cx="12" cy="7" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
      restart: '<path d="M4 10a8 8 0 1 1 1 7m-1-13v6h6"/>',
    };
    return (
      '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
      paths[name] +
      "</svg>"
    );
  }
  function imageTag(src, cls = "", alt = "") {
    return '<img draggable="false" class="' + cls + '" alt="' + e(alt) + '" src="' + src + '">';
  }
  function button(label, attrs, cls = "") {
    return '<button type="button" class="' + cls + '" ' + attrs + ">" + e(label) + "</button>";
  }
  function link(label, page, cls = "action") {
    return button(label, 'data-page="' + e(page) + '"', cls);
  }
  function pageTitle(id) {
    if (id === "@home" && feature.phoneHomeLabel) return feature.phoneHomeLabel;
    if (id === "@home" && multiApp && feature.phoneHome) return feature.pages[feature.phoneHome].title;
    return id.startsWith("@") ? systemNames[id] : feature.pages[id].title;
  }
  function entryIcon() {
    return feature.icon
      ? imageTag(
          feature.icon.startsWith("@") ? media[feature.icon.slice(1)] : feature.media[feature.icon],
          "entry-icon",
        )
      : '<span class="entry-icon fallback-icon" aria-hidden="true">' + e(feature.name.slice(0, 1)) + "</span>";
  }

  function face() {
    const ticks = Array.from(
      { length: 60 },
      (_, n) => '<i class="' + (n % 5 === 0 ? "major" : "") + '" style="--angle:' + n * 6 + 'deg"></i>',
    ).join("");
    return (
      '<div class="dial"><div class="ticks">' +
      ticks +
      '</div><div class="hourmarks"><b>12</b><b>3</b><b>6</b><b>9</b></div><span class="dial-date">THU&nbsp; 19</span><span class="dial-label">HUAWEI</span><div class="hand hour"></div><div class="hand minute"></div><div class="hand second"></div><i class="pin"></i></div>'
    );
  }
  function launcher() {
    const rows = [
      ["锻炼", "workout"],
      ["锻炼记录", "record"],
      ["训练状态", "training"],
      ["活动记录", "rings-icon"],
      ["减脂塑形", "shape"],
    ];
    const fixedRow = ([name, key]) =>
      '<div class="app-row">' + imageTag(media[key], "entry-icon") + "<span>" + name + "</span></div>";
    const entry = feature.entries.launcher;
    const nativeInsight = entry?.label === "健康洞察" ? "" : fixedRow(["健康洞察", "insight-icon"]);
    return (
      '<div class="scroll launcher">' +
      rows.map(fixedRow).join("") +
      nativeInsight +
      (entry
        ? '<button type="button" class="app-row" data-page="' +
          e(entry.page) +
          '">' +
          entryIcon() +
          "<span>" +
          e(entry.label) +
          "</span></button>"
        : "") +
      fixedRow(["情绪健康", "emotion"]) +
      "</div>"
    );
  }
  function cardScreen(side) {
    const item = feature.entries[side];
    const content = item
      ? '<button class="service-card" data-page="' +
        e(item.page) +
        '"><span class="service-head">' +
        entryIcon() +
        "<span>" +
        e(item.label) +
        "<small>" +
        e(item.detail) +
        "</small></span><i>›</i></span><strong>" +
        e(item.value || item.label) +
        "</strong><small>" +
        e(item.note) +
        "</small></button>"
      : "";
    const nativeCard =
      side === "minus" && item?.label !== "健康洞察"
        ? '<div class="service-card"><span class="service-head">' +
          imageTag(media["insight-icon"], "entry-icon") +
          "<span>健康洞察<small>锻炼时长</small></span></span><strong>40 分钟</strong><small>过去 7 天日均值</small></div>"
        : "";
    return (
      '<div class="scroll watch-cards ' +
      side +
      '"><div class="card-clock">11:06</div><div class="calendar-date">11月19日 星期四</div>' +
      nativeCard +
      content +
      (side === "minus"
        ? '<div class="calendar-chip">▦　日程</div>'
        : '<div class="carousel-dots">●　○　○</div>') +
      "</div>"
    );
  }
  function phoneNav(title) {
    return (
      '<div class="phone-nav"><button type="button" aria-label="返回" data-control="back">' +
      icon("back") +
      "</button><b>" +
      e(title) +
      "</b><span></span></div>"
    );
  }
  function phoneBar() {
    return '<div class="phone-status"><b>11:06</b><span aria-hidden="true">▴ ▮▮ ▰</span></div>';
  }
  function phoneTabs() {
    return (
      '<div class="phone-tabs">' +
      [
        ["today", "今日"],
        ["exercise", "锻炼"],
        ["watch", "设备"],
        ["user", "我的"],
      ]
        .map(
          ([name, label], i) =>
            '<span class="' + (i === 0 ? "on" : "") + '">' + icon(name) + "<small>" + label + "</small></span>",
        )
        .join("") +
      "</div>"
    );
  }
  function phoneHome() {
    return (
      '<div class="app-home scroll"><div class="app-heading">健康</div>' +
      imageTag(media.rings, "home-asset", "健康三环") +
      imageTag(media.shortcuts, "home-asset", "快捷入口") +
      '<button class="summary-link" data-page="@summary"><span class="summary-symbol">✦</span><span><b>健康摘要</b><small>查看近期健康趋势</small></span><i>›</i></button>' +
      imageTag(media.activity, "home-asset", "运动记录") +
      "</div>" +
      phoneTabs()
    );
  }
  function summary() {
    const item = feature.entries.summary;
    return (
      phoneNav("健康摘要") +
      '<div class="scroll phone-body summary"><div class="segments"><b>精选摘要</b><span>趋势列表</span></div><h3>您的健康数据整体结果如何？</h3><div class="analysis-number"><b>4</b><span>项<br>数据分析</span></div>' +
      (item
        ? '<button data-page="' +
          e(item.page) +
          '" class="phone-entry">' +
          entryIcon() +
          "<span><b>" +
          e(item.label) +
          "</b><small>" +
          e(item.detail) +
          "</small></span><i>›</i></button>"
        : "") +
      imageTag(media.analysis, "home-asset", "健康摘要分析卡片") +
      "</div>"
    );
  }
  function paragraphs(items = []) {
    return items
      .map((x) => '<section class="paragraph"><h3>' + e(x.title) + "</h3><p>" + e(x.text) + "</p></section>")
      .join("");
  }
  function featurePage(device, id) {
    const p = feature.pages[id],
      watch = device === "watch";
    const rec = feature.records?.[p.record];
    if (watch && p.watchFlow) return watchFlow(p);
    let header = "",
      content = "";
    if (rec) {
      header = watch ? "" : phoneNav(p.title);
      content =
        '<div class="reading-head">' +
        (watch || rec.title !== p.title ? "<h2>" + e(rec.title) + "</h2>" : "") +
        "<small>" +
        e(rec.date) +
        " 生成</small></div>" +
        paragraphs(rec.sections) +
        '<div class="ai-credit">内容由 AI 生成</div>';
      return (
        header +
        '<div class="scroll reading ' +
        (watch ? "watch-reading" : "phone-body phone-reading") +
        '">' +
        content +
        "</div>"
      );
    }
    if (!watch) header = phoneNav(p.title);
    if (p.cover) {
      content += '<div class="screen-cover">' + imageTag(feature.media[p.cover], "", p.title);
      if (p.coverAction) {
        const [x, y, w, h] = p.coverAction.box;
        content +=
          '<button class="hotspot" style="left:' +
          x +
          "%;top:" +
          y +
          "%;width:" +
          w +
          "%;height:" +
          h +
          '%" aria-label="' +
          e(p.coverAction.label) +
          '" data-page="' +
          e(p.coverAction.page) +
          '"></button>';
      }
      content += "</div>";
    } else if (watch || p.subtitle) {
      const subtitle = watch && p.subtitle ? "<small>" + e(p.subtitle) + "</small>" : "";
      content +=
        '<div class="feature-heading">' + subtitle + "<h2>" + e(watch ? p.title : p.subtitle) + "</h2></div>";
    }
    if (p.sections?.length || p.action)
      content +=
        '<div class="feature-body">' +
        paragraphs(p.sections) +
        (p.action ? link(p.action.label, p.action.page) : "") +
        "</div>";
    return (
      header + '<div class="scroll feature-scroll ' + (watch ? "" : "phone-body") + '">' + content + "</div>"
    );
  }
  function editableText(capture, zone) {
    return (capture.elements || []).filter(item => item.zone === zone).map(item => {
      const [x,y,w,h] = item.box;
      const style = Object.entries(item.style || {}).map(([key,value]) => key + ":" + value).join(";");
      return '<span class="editable-text" data-element="' + e(item.id) + '" data-role="' + e(item.role) +
        '" style="left:' + x + '%;top:' + y + '%;width:' + w + '%;height:' + h + '%;' + e(style) +
        '">' + e(item.text) + '</span>';
    }).join("");
  }
  function captureBand(capture, zone, extent) {
    if (!capture[zone]) return "";
    const spots = [...(capture.hotspots || []), ...(capture.pendingHotspots || []).map(s => ({...s, pending: true}))];
    const controls = spots.filter(hotspot => {
      const center = hotspot.box[1] + hotspot.box[3] / 2;
      return hotspot.zone === zone && (!extent || (center >= extent[0] && center < extent[1]));
    }).map(hotspot => {
      const [x, y, width, height] = hotspot.box;
      const mode = hotspot.mode ? 'data-mode="' + e(hotspot.mode) + '" ' : '';
      const keepScroll = hotspot.keepScroll ? 'data-keep-scroll ' : '';
      const remember = hotspot.rememberRoutes ? 'data-routes="' + e(JSON.stringify(hotspot.rememberRoutes)) + '" ' : '';
      const owner = hotspot.feature ? 'data-feature="' + e(hotspot.feature) + '" data-entry-scene="' + e(hotspot.scene) + '" ' : '';
      const handoff = hotspot.openFeature;
      const linked = handoff && features.some(f => f.id === handoff.id)
        ? 'data-related="' + e(handoff.id) + '" data-destination="' + e(handoff.page) + '" ' : '';
      const action = hotspot.pending ? 'data-pending="' + e(hotspot.label) + '"' :
        hotspot.page === "@back" ? 'data-control="back"' : 'data-page="' + e(hotspot.page) + '"';
      return '<button type="button" class="hotspot" aria-label="' + e(hotspot.label) + '" ' + mode + keepScroll + remember + owner + linked + action +
        ' style="left:' + x + '%;top:' + y + '%;width:' + width + '%;height:' + height + '%"></button>';
    }).join("");
    const labels = (zone === "content" ? capture.bindings || [] : []).filter(item =>
      flowState()[item.key] !== feature.flowDefaults?.[item.key]).map(item => {
      const [x,y,w,h] = item.box;
      return '<span class="bound-caption caption-'+e(item.tone)+'" style="left:'+x+'%;top:'+y+'%;width:'+w+'%;height:'+h+'%">'+e(flowText(item.text))+'</span>';
    }).join("");
    const elements = editableText(capture, zone);
    return '<div class="capture-band'+(elements ? ' editable-band' : '')+'" data-capture-zone="'+zone+'">'+imageTag(feature.media[capture[zone]] || media[capture[zone]], "", capture[zone + "Label"] || "")+labels+elements+controls+'</div>';
  }
  function capturedScreen(capture) {
    return '<div class="captured-screen">'+captureBand(capture,"header")+'<div class="scroll capture-scroll">'+captureBand(capture,"content")+'</div>'+captureBand(capture,"footer")+'</div>';
  }
  function launcherAnchor(device, id) {
    return device === "watch" && feature.watchProfile === "watch6" && wristLauncher?.anchors[id];
  }
  function watchScrollLayout(device, id) {
    if (device !== "watch") return null;
    const anchor = launcherAnchor(device, id);
    if (anchor) return {kind:"launcher", index:wristLauncher.rows.findIndex(row => row.feature === anchor)};
    for (const menu of feature.watchLists || []) {
      if (Object.hasOwn(menu.anchors, id)) return {kind:"menu", menu, index:menu.anchors[id]};
    }
    for (const group of feature.watchScrollGroups || []) {
      const pages = Array.isArray(group) ? group : group.pages;
      const index = pages.indexOf(id);
      if (index >= 0) return {kind:group.mode === "paged" ? "pager" : "pages", pages, index};
    }
    if (feature.pages[id]?.capture?.listBands) return {kind:"pages", pages:[id], index:0};
    return null;
  }
  function sameWatchScroll(device, id, other) {
    const layout = watchScrollLayout(device, id);
    if (!layout) return false;
    if (layout.kind === "launcher") return Boolean(launcherAnchor(device, other));
    if (layout.menu) return Object.hasOwn(layout.menu.anchors, other);
    return layout.pages.includes(other);
  }
  function launcherList() {
    return '<div class="scroll watch-app-list" aria-label="腕上应用列表">' + wristLauncher.rows.map(row =>
      '<button type="button" class="watch-app-row" data-wrist-app="' + e(row.feature) + '" aria-label="' + e(row.label) + '">' +
      (row.image ? imageTag(row.image, "wrist-app-icon", "") : "") + '<span>' + e(row.label) + '</span></button>'
    ).join("") + '</div>';
  }
  function captureBands(id) {
    const cap = feature.pages[id].capture;
    return cap.listBands.map(([start,end]) =>
      '<div class="watch-list-band" data-theme-page="' + e(themePage("watch", id)) + '" data-location-page="' + e(id) + '" style="height:' + (end-start) +
      '%"><div class="band-source" style="top:' + (-100*start/(end-start)) + '%;height:' + (10000/(end-start)) + '%">' +
      captureBand(cap, "content", [start,end]) + '</div></div>').join("");
  }
  function watchScrollContent(layout) {
    if (layout.kind === "launcher") return launcherList();
    if (layout.pages) {
      const paged = layout.kind === "pager";
      const panels = layout.pages.map(id => {
        const cap = feature.pages[id].capture;
        if (!paged && cap.listBands) return captureBands(id);
        const content = paged && cap.scrollSources
          ? '<div class="scroll card-menu">' + cap.scrollSources.map(captureBands).join("") + '</div>'
          : captureBand(cap, "content");
        return '<div class="study-panel" data-theme-page="' + e(themePage("watch", id)) + '" data-location-page="' + e(id) + '">' + content + '</div>';
      }).join("");
      return (paged ? '<div class="watch-page-track">' : '<div class="scroll watch-app-list watch-panels">') + panels + '</div>';
    }
    const {menu} = layout;
    return '<div class="scroll watch-app-list study-list' + (menu.naturalRows ? ' natural-rows' : '') + '" aria-label="' + e(menu.label) + '">' + menu.rows.map(row => {
      const [x,y,w,h] = row.crop;
      const asset = feature.pages[row.source].capture.content;
      const src = feature.media[asset] || media[asset];
      const attrs = row.pending ? 'data-pending="' + e(row.label) + '"' : 'data-page="' + e(row.page) + '"';
      const cropStyle = 'width:' + 10000/w + '%;height:' + 10000/h + '%;left:' + (-100*x/w) + '%;top:' + (-100*y/h) + '%';
      const elements = editableText(feature.pages[row.source].capture, "content");
      const art = elements
        ? '<span class="study-editable-source" data-theme-page="' + e(themePage("watch", row.source)) + '" style="' + cropStyle + '">' +
          imageTag(src) + elements + '</span>'
        : '<img draggable="false" alt="" src="' + src + '" style="' + cropStyle + '">';
      const secondary = row.secondary;
      const extra = secondary ? button(secondary.label, (secondary.page ? 'data-page="' + e(secondary.page) : 'data-pending="' +
        e(secondary.label)) + '" aria-label="' + e(secondary.label) + '"', 'row-secondary') : '';
      return '<div class="study-row" data-theme-page="' + e(themePage("watch", row.location)) + '" data-location-page="' + e(row.location) + '" style="--art-ratio:' + w/h + '">' +
        (row.heading ? '<small>' + e(row.heading) + '</small>' : '') +
        '<button class="study-choice' + (row.compact ? ' compact' : '') + '" type="button" aria-label="' +
        e(row.label) + '" ' + attrs + '>' + art + '</button>' + extra + '</div>';
    }).join("") + '</div>';
  }
  function centerWatchRow(list, index) {
    if (index <= 0) { list.scrollTop = 0; return; }
    if (index >= list.children.length - 1) { list.scrollTop = list.scrollHeight; return; }
    const row = list.children[index];
    if (row) list.scrollTop = row.offsetTop - (list.clientHeight - row.offsetHeight) / 2;
  }
  const watchPagers = new WeakMap();
  function activeScroller(surface) {
    return surface?.querySelector(surface.classList.contains("paged-screen")
      ? '.study-panel[aria-current]:not([inert]) .scroll' : '.scroll');
  }
  function canScrollIn(list, delta) {
    return list && (delta < 0 ? list.scrollTop > 1 : list.scrollTop < list.scrollHeight - list.clientHeight - 1);
  }
  function setupWatchPager(surface, layout, onLocation) {
    const track = surface.firstElementChild;
    const panels = [...track.children];
    const clamp = value => Math.max(0, Math.min(panels.length - 1, value));
    let target = layout.index, position = target, frame = 0;
    function draw(value) {
      position = value;
      track.style.transform = 'translateY(' + (-100 * value) + '%)';
    }
    function finish() {
      draw(target);
      panels.forEach((panel, i) => {
        panel.inert = i !== target;
        if (i === target) panel.setAttribute("aria-current", "page");
        else panel.removeAttribute("aria-current");
      });
      onLocation(layout.pages[target]);
    }
    function settle(next, animate = true) {
      cancelAnimationFrame(frame);
      target = clamp(next);
      const start = position, distance = target - start;
      if (!animate || Math.abs(distance) < .001 || matchMedia("(prefers-reduced-motion: reduce)").matches) {
        finish();
        return;
      }
      panels.forEach(panel => { panel.inert = true; });
      const began = performance.now(), duration = 140 + 100 * Math.min(1, Math.abs(distance));
      function tick(now) {
        if (!track.isConnected) return;
        const t = Math.min(1, Math.max(0, (now - began) / duration));
        if (t === 1) return finish();
        draw(start + distance * (1 - (1 - t) ** 3));
        frame = requestAnimationFrame(tick);
      }
      frame = requestAnimationFrame(tick);
    }
    finish();
    return {
      grab() { cancelAnimationFrame(frame); return position; },
      drag(start, delta) { draw(clamp(Math.max(target - 1, Math.min(target + 1, start + delta)))); },
      step(delta) { settle(target + delta); },
      advance(delta) {
        const list = activeScroller(surface);
        if (canScrollIn(list, delta)) list.scrollTop += delta * list.clientHeight * .55;
        else settle(target + delta);
      },
      boundary(last) { settle(last ? panels.length - 1 : 0, false); },
    };
  }
  function setupWatchScroll(list, layout, id, scroll, onLocation) {
    const rows = [...list.children];
    const index = layout.kind === "pages" ? rows.findIndex(row => row.dataset.locationPage === id) : layout.index;
    if (list.matches(".watch-panels, .natural-rows")) {
      list.style.setProperty("--leading", Math.max(0,(list.clientHeight-rows[0].offsetHeight)/2) + "px");
      list.style.setProperty("--trailing", Math.max(0,(list.clientHeight-rows.at(-1).offsetHeight)/2) + "px");
    }
    if (scroll != null) list.scrollTop = scroll;
    else if (rows[index]?.classList.contains("watch-list-band") && !feature.pages[id]?.facePanel) list.scrollTop = rows[index].offsetTop;
    else centerWatchRow(list, index);
    let selected;
    function highlight(report) {
      const center = list.scrollTop + list.clientHeight / 2;
      const distances = rows.map(row => Math.abs(row.offsetTop + row.offsetHeight / 2 - center));
      let nearest, closest = Infinity;
      for (const [i, row] of rows.entries()) {
        const distance = distances[i];
        if (row.matches(".study-row,.watch-app-row")) row.style.setProperty("--row-scale", String(Math.max(.76, 1 - .14 * distance / row.offsetHeight)));
        if (distance < closest) { closest = distance; nearest = row; }
      }
      if (nearest === selected) return;
      selected?.removeAttribute("aria-current");
      nearest?.setAttribute("aria-current", "true");
      selected = nearest;
      if (report && nearest?.dataset.locationPage) onLocation(nearest.dataset.locationPage);
    }
    highlight(false);
    list.addEventListener("scroll", () => highlight(true), {passive:true});
  }
  function pageCapture(device, id) {
    const page = device === "watch" ? feature.watchScreens?.[id] : id === "@home" && feature.phoneHome;
    return feature.pages[page || id]?.capture;
  }
  function pageSwipes(device, id) {
    return pageCapture(device, id)?.swipe || feature.pages[id]?.watchFlow?.swipe || {};
  }
  let pendingTimeout;
  function showPending(label) {
    const status = context?.status || document.getElementById("capture-status");
    if (!status) return;
    status.textContent = "「" + label + "」待实机采集";
    if (directory) {
      clearTimeout(pendingTimeout);
      pendingTimeout = setTimeout(() => { status.textContent = ""; }, 3500);
    }
  }
  function screenContent(device, id) {
    const capture = pageCapture(device, id);
    if (capture) return capturedScreen(capture);
    let body;
    switch (id) {
      case "@face":
        body = face();
        break;
      case "@launcher":
        body = launcher();
        break;
      case "@minus":
        body = cardScreen("minus");
        break;
      case "@cards":
        body = cardScreen("cards");
        break;
      case "@home":
        body = phoneHome();
        break;
      case "@summary":
        body = summary();
        break;
      default:
        body = featurePage(device, id);
    }
    return (device === "phone" ? phoneBar() : "") + body;
  }
  function ancestor(device, id) {
    if (id.startsWith("@")) return systemParent[id];
    const parent = feature.pages[id].parent;
    return typeof parent === "string" ? parent : parent[device];
  }
  function direct(device, id) {
    id = feature.pages[id]?.aliasOf || id;
    const trail = [];
    let child = id;
    for (let p = ancestor(device, id); p; p = ancestor(device, p)) {
      if (!sameWatchScroll(device, child, p)) trail.unshift({id:p, scroll:null});
      child = p;
    }
    return { id, trail };
  }
  function clearTimers() {
    for (const id of Object.values(timers)) clearTimeout(id);
  }
  function openFeature(next) {
    feature = next;
    syncPicker();
    const view = next.initialView;
    selectScene(view?.scene ?? (multiApp ? next.scenes[0].id : null), view && [view.device, view.page]);
  }
  function selectScene(id, key, keepRoutes = false) {
    clearTimers();
    if (!keepRoutes) savedRoutes.delete(feature.id);
    scene = feature.scenes.find((s) => s.id === id) || null;
    devices = {};
    if (scene) {
      for (const [d, id] of Object.entries(scene.start)) devices[d] = direct(d, id);
      if (key) devices[key[0]] = direct(key[0], key[1]);
    }
    render();
    if (scene) {
      const focusDevice = key ? key[0] : scene.keys[0][0];
      main.querySelector('[data-device="' + focusDevice + '"]').classList.add("primary-device");
    }
    const active = nav.querySelector("[aria-current]");
    if (active && nav.scrollWidth > nav.clientWidth) {
      nav.scrollLeft += active.getBoundingClientRect().left - nav.getBoundingClientRect().left - 8;
    }
    if (!context) window.scrollTo(0, 0);
  }
  function go(device, id, replace = false, scroll = null) {
    if (!id) return;
    id = feature.pages[id]?.aliasOf || id;
    const d = devices[device];
    if (!replace && d.id !== id && (!sameWatchScroll(device, d.id, id) || feature.pages[id]?.parent === d.id)) {
      const scroller = activeScroller(main.querySelector('[data-device="' + device + '"] .surface'));
      d.trail.push({ id: d.id, scroll: scroller?.scrollTop || 0 });
    }
    d.id = id;
    refreshDevice(device, scroll);
  }
  function control(device, action) {
    const d = devices[device],
      id = d.id;
    if (action === "zoom") {
      enlargedPhone = !enlargedPhone;
      const panel = main.querySelector('[data-device="phone"]');
      const stage = panel.querySelector(".stage");
      stage.classList.toggle("enlarged", enlargedPhone);
      fitFrame(stage, stage.clientWidth, stage.clientHeight);
      stage.scrollTop = 0;
      const button = phoneActions.querySelector('[data-control="zoom"]');
      button.textContent = enlargedPhone ? "适应窗口" : "放大";
      button.setAttribute("aria-pressed", String(enlargedPhone));
      return;
    }
    if (action === "back") {
      const prev = d.trail.pop();
      if (prev?.origin) {
        clearTimers();
        ({feature, scene, devices} = prev.origin);
        syncPicker();
        render();
        if (scene && devices[prev.device || device]) refreshDevice(prev.device || device, prev.scroll);
        prev.resume?.();
        return;
      }
      if (prev) go(device, prev.id, true, prev.scroll);
    }
    if (action === "home") {
      devices[device] = direct(device, device === "watch" ? "@face" : "@home");
      refreshDevice(device);
    }
    if (action === "crown") {
      if (id === "@face" || id === feature.watchScreens?.["@face"]) go(device, "@launcher");
      else control(device, "home");
    }
    if (["left", "right", "up", "down"].includes(action)) {
      const pager = device === "watch" && watchPagers.get(main.querySelector('[data-device="watch"] .surface'));
      if (pager && (action === "up" || action === "down")) return pager.advance(action === "up" ? 1 : -1);
      const list = device === "watch" && main.querySelector('[data-device="watch"] .surface .watch-app-list');
      if (list && (action === "up" || action === "down")) {
        const selected = [...list.children].indexOf(list.querySelector("[aria-current]"));
        const next = selected + (action === "up" ? 1 : -1);
        if (next >= 0 && next < list.children.length) return centerWatchRow(list, next);
        const dest = pageSwipes(device, id)[action];
        if (!dest || sameWatchScroll(device, id, dest)) return;
      }
      const swipePage = pageSwipes(device, id)[action];
      if (swipePage === "@face" && device === "watch") return control(device, "home");
      if (swipePage && device === "watch" && feature.pages[swipePage]?.facePanel) {
        if (d.trail[d.trail.length - 1]?.id === swipePage) return control(device, "back");
        return go(device, swipePage);
      }
      if (swipePage) return go(device, swipePage, true);
      const pending = pageCapture(device, id)?.pendingSwipes?.[action];
      if (pending) return showPending(pending);
      if (action === "up" || action === "down") return;
      if (device === "watch" && !feature.watchScreens) {
        if (id === "@face") return go(device, action === "right" ? "@minus" : "@cards");
        if ((id === "@minus" && action === "left") || (id === "@cards" && action === "right"))
          return control(device, "home");
      }
      if (action === "right" && d.trail.length) control(device, "back");
    }
  }
  // Previews contain the same interactive page markup. Keep the preview trigger outside it.
  function keyMarkup(k, i) {
    const holder = document.createElement("div");
    holder.className = "key";
    holder.dataset.themeDevice = k[0];
    holder.dataset.themeFeature = feature.id;
    holder.dataset.themePage = themePage(k[0], k[1]);
    holder.innerHTML =
      '<div class="mini-slot" aria-hidden="true" inert><div class="mini-frame ' +
      k[0] + (k[0] === "watch" && media.watch6Case ? " photo-case" : "") +
      '"><div class="mini-screen">' +
      screenContent(k[0], k[1]) +
      "</div></div></div>" +
      '<span class="key-label">' +
      e(k[2]) +
      '</span><button class="key-open" data-key="' +
      i +
      '" type="button" aria-label="定位到' +
      e(k[2]) +
      '"></button>';
    return holder.outerHTML;
  }
  function overview() {
    const count = feature.scenes.reduce((n, s) => n + s.keys.length, 0);
    return (
      '<div class="main-title"><div><h1>场景总览</h1><p>' +
      e(feature.name) +
      '的关键界面，点击即可进入操作。</p></div><span class="count">' +
      feature.scenes.length +
      " 个场景　/　" +
      count +
      ' 个界面</span></div><div class="map">' +
      feature.scenes
        .map((s) => {
          const names = [...new Set(s.keys.map((k) => k[0]))];
          return (
            '<article class="scene-card" data-scene="' +
            e(s.id) +
            '"><div class="card-title"><div class="kind">' +
            names.map(icon).join("") +
            "</div><h2>" +
            e(s.title) +
            '</h2><button type="button" class="enter" data-start aria-label="进入' +
            e(s.title) +
            '">' +
            icon("arrow") +
            '</button></div><div class="key-strip">' +
            s.keys.map(keyMarkup).join("") +
            "</div></article>"
          );
        })
        .join("") +
      "</div>"
    );
  }
  function devicePanel(d) {
    const mate = d === "phone" && feature.phoneProfile === "mate50";
    const watch6 = d === "watch" && feature.watchProfile === "watch6";
    const model = watch6 ? "HUAWEI WATCH 6" : mate ? "HUAWEI Mate 50" : models[d];
    const standaloneCapture = (d === "phone" && !devices.watch) || (watch6 && !devices.phone);
    const heading = standaloneCapture ? "" : '<div class="panel-head">' + icon(d) + "<h2>" + model + '</h2><span class="page-name"></span></div>';
    return (
      '<section class="device-panel ' +
      d +
      '" data-device="' +
      d +
      '">' + heading + '<div class="stage' +
      (d === "phone" && enlargedPhone && !devices.watch ? " enlarged" : "") +
      '"><div class="hardware ' +
      d + (mate ? ' mate' : watch6 ? (media.watch6Case ? ' watch6 photo-case' : ' watch6') : '') +
      '"><div class="surface" tabindex="0" aria-label="' +
      model +
      ' 屏幕"></div>' +
      (mate ? '<div class="mate-bezel" aria-hidden="true"></div>' : watch6 ? "" : imageTag(media[d], "frame")) +
      (d === "watch"
        ? '<button type="button" class="crown" data-control="crown" aria-label="按下表冠" title="按下表冠"></button>'
        : "") +
      '</div></div>' + (d === "watch" && !directory ? '<aside class="watch-replay" hidden></aside>' : "") +
      (standaloneCapture ? "" : '<div class="device-controls"></div>') + '</section>'
    );
  }
  function renderSceneNavigation(standalone, recordedWatch) {
    const sceneTools = document.getElementById("scene-tools");
    sceneTools.innerHTML = standalone
      ? '<details><summary>场景说明</summary><p>' + e(scene.hint) + '</p></details><button type="button" class="restart" data-restart>' + icon("restart") + '重置</button>'
      : "";
    if (scene?.phonePageIndex?.length) {
      const select = document.createElement("select");
      select.dataset.phoneJump = "";
      select.setAttribute("aria-label", "本模块页面");
      select.add(new Option("本模块页面", ""));
      for (const id of scene.phonePageIndex) {
        const titles = [], seen = new Set();
        let key = id;
        while (feature.pages[key] && !seen.has(key)) {
          seen.add(key);
          const page = feature.pages[key];
          if (!titles.length || titles[0] !== page.title) titles.unshift(page.title);
          key = page.parent;
        }
        select.add(new Option(titles.join(" › "), id));
      }
      sceneTools.append(select);
    }
    if (recordedWatch && scene) {
      const systemPages = Object.values(feature.watchScreens);
      const pages = [["@face","表盘"], ["@launcher","应用列表"], ...Object.entries(feature.pages)
        .filter(([id,p]) => p.device === "watch" && !p.aliasOf && !systemPages.includes(id) && !p.capture?.launcherRows)
        .map(([id,p]) => [id,p.title])];
      const options = pages.map(([id,title]) => '<option value="'+e(id)+'">'+e(title)+'</option>').join("");
      sceneTools.insertAdjacentHTML("beforeend", '<div id="wrist-navigation">' +
        button("返回",'data-watch-back') + button("应用列表",'data-watch-list') +
        '<select aria-label="跳转到界面" data-watch-jump><option value="">跳转到界面</option>'+options+'</select><output></output></div>');
    }
    if (scene) {
      if (feature.pendingScreens?.length) {
        sceneTools.insertAdjacentHTML("beforeend", '<details><summary>待采集界面</summary><p>' +
          feature.pendingScreens.map(e).join("、") + '</p></details>');
      }
      sceneTools.insertAdjacentHTML("beforeend", '<output id="capture-status" aria-live="polite"></output>');
    }
    nav.innerHTML = [{ id: "", title: "总览" }, ...feature.scenes]
      .map(
        (s) =>
          '<button type="button" data-side="' +
          e(s.id) +
          '" ' +
          ((scene?.id || "") === s.id ? 'aria-current="page"' : "") +
          ">" +
          icon(s.id ? "scene" : "overview") +
          "<span>" +
          e(s.title) +
          "</span></button>",
      )
      .join("");
  }
  function render() {
    phoneActions.replaceChildren();
    if (!context && multiApp) document.getElementById("app-name").textContent = feature.appName || "穿戴交互演示";
    const recordedWatch = feature.watchProfile === "watch6";
    const standalone = scene && Object.keys(devices).length === 1 && (devices.phone || recordedWatch);
    if (!context) {
      document.querySelector(".watch-help").textContent = recordedWatch
        ? "在表盘上滑看通知，下滑打开控制中心，左滑看卡片，右滑进入负一屏。反向滑动可回到表盘。按表冠可打开应用列表，进入应用后右滑返回。"
        : "点表冠打开应用列表。表盘右滑进入负一屏，左滑进入超级卡片。";
      document.body.classList.toggle("watch-recording", recordedWatch);
      document.body.classList.toggle("phone-workspace", feature.scenes.every(s => Object.keys(s.start).length === 1 && (s.start.phone || recordedWatch)));
      document.body.classList.toggle("phone-demo", Boolean(standalone));
    }
    if (!directory) renderSceneNavigation(standalone, recordedWatch);
    main.innerHTML = scene
      ? (standalone ? "" : '<div class="main-title"><div><h1>' +
        e(scene.title) +
        "</h1><p>" +
        e(scene.hint) +
        '</p></div><button class="restart" type="button" data-restart>' +
        icon("restart") +
        '重置场景</button></div>') + '<div class="device-grid">' +
        Object.keys(devices).map(devicePanel).join("") +
        "</div>"
      : overview();
    syncPicker();
    if (scene) Object.keys(devices).forEach((device) => refreshDevice(device));
    else context?.setLocation(null, []);
    attachSizes();
  }
  function refreshWatchReplay(panel, id, swipes) {
    const replay = pageCapture("watch", id)?.replay;
    const launcher = launcherAnchor("watch", id) || id === "@launcher" || !!pageCapture("watch", id)?.launcherRows?.length;
    const apps = launcher && features.some(f => f.watchReplayEntry)
      ? features.filter(f => f.watchScreens && (f.watchReplayEntry || f.scenes.some(s =>
        s.keys.some(k => k[0] === "watch" && k[1] === f.entries?.launcher?.page))))
      : [];
    const tray = panel.querySelector(".watch-replay");
    tray.hidden = !replay && !apps.length;
    panel.classList.toggle("with-watch-replay", !tray.hidden);
    if (tray.hidden) return;
    const options = apps.map(f => '<option value="'+e(f.id)+'">'+e(f.name)+'</option>').join("");
    const buttons = (replay?.actions || []).map(({label, page}) =>
      button(label, 'data-page="'+e(page)+'"')).join("");
    const gestures = [["上滑","up"],["下滑","down"]].filter(([, dir]) => swipes[dir])
      .map(([label, dir]) => button(label, 'data-control="'+dir+'"')).join("");
    const pending = replay?.pending || [];
    tray.innerHTML = '<h2>'+e(launcher ? "腕上应用" : "实机流程回放")+'</h2><h3>'+e(pageTitle(id))+'</h3>'+
      (replay ? '<p>'+e(replay.description)+'</p>' : "")+
      (options ? '<label>打开应用 <select data-replay-app><option value="">选择腕上应用</option>'+options+'</select></label>' : "")+
      (buttons ? '<div class="replay-choices">'+buttons+'</div>' : "")+
      '<div class="replay-gestures">'+gestures+
      button("返回上一层",'data-control="back"'+(devices.watch.trail.length ? "" : " disabled"))+'</div>'+
      (pending.length ? '<div class="replay-pending"><strong>待采集</strong><ul>'+
        pending.map(step => '<li>'+e(step)+'</li>').join("")+'</ul></div>' : "");
  }
  function refreshPageNavigation(panel, device, id, swipes) {
    if (!directory) {
      if (device === "watch") {
        panel.querySelector(".watch-replay").dataset.themePage = themePage(device, id);
        refreshWatchReplay(panel, id, swipes);
      }
      return;
    }
    const row = directory.lookup(feature.id, device, id);
    const capture = pageCapture(device, id);
    const replay = capture?.replay?.actions || [];
    const actions = [];
    if (replay.length) {
      const surface = panel.querySelector(".surface");
      const current = surface.querySelector(".watch-page-track > [aria-current]") || surface;
      const targets = new Set(Array.from(current.querySelectorAll("button[data-page]:not([data-related]):not([data-feature])"),
        button => button.dataset.page));
      for (const {page, label} of replay) {
        if (!targets.has(page) && !Object.values(swipes).includes(page)) {
          actions.push({label, run: () => go(device, resolvedPage(page))});
        }
      }
    }
    context.setLocation(row, actions);
  }
  function themePage(device, id) {
    return directory?.lookup(feature.id, device, id)?.key || [feature.id,device,id].join("/");
  }
  function refreshDevice(device, scroll = null) {
    clearTimeout(timers[device]);
    const panel = main.querySelector('[data-device="' + device + '"]');
    const d = devices[device],
      surface = panel.querySelector(".surface");
    if (feature.pages[d.id]?.enterValues) Object.assign(flowState(),feature.pages[d.id].enterValues);
    panel.querySelector(".stage").scrollTop = 0;
    surface.dataset.page = d.id;
    const captureStatus = context?.status || document.getElementById("capture-status");
    if (captureStatus) captureStatus.textContent = "";
    const phoneJump = document.querySelector("[data-phone-jump]");
    if (device === "phone" && phoneJump) phoneJump.value = scene.phonePageIndex.includes(d.id) ? d.id : "";
    const layout = watchScrollLayout(device, d.id);
    panel.dataset.themeFeature = feature.id;
    panel.dataset.themeDevice = device;
    surface.dataset.themePage = !layout || layout.kind === "launcher" ? themePage(device, d.id) : "";
    const paged = layout?.kind === "pager";
    const swipes = {...pageSwipes(device, d.id)};
    if ((layout && !paged) || feature.pages[d.id]?.capture?.scrollSources) Object.assign(swipes, {up:true, down:true});
    const pending = pageCapture(device, d.id)?.pendingSwipes || {};
    surface.classList.toggle("list-screen", Boolean(layout) && !paged);
    surface.classList.toggle("paged-screen", paged);
    surface.classList.toggle("vertical-pages", !layout && Boolean(swipes.up || swipes.down || pending.up || pending.down));
    surface.innerHTML = layout ? watchScrollContent(layout) : screenContent(device, d.id);
    const scroller = surface.querySelector(".scroll");
    const onLocation = id => {
      if (d.id === id || devices[device] !== d || !surface.isConnected) return;
      d.id = id;
      surface.dataset.page = id;
      if (layout?.kind === "launcher") surface.dataset.themePage = themePage(device, id);
      surface.setAttribute("aria-description", pageTitle(id));
      const title = panel.querySelector(".page-name");
      if (title) title.textContent = pageTitle(id);
      if (captureStatus) captureStatus.textContent = "";
      const directions = feature.pages[id]?.capture?.scrollSources ? {up:true, down:true} :
        paged ? pageSwipes(device, id) : swipes;
      refreshPageNavigation(panel, device, id, directions);
      if (paged) {
        const controls = panel.querySelector(".device-controls") || phoneActions;
        for (const dir of ["up","down"]) {
          const button = controls.querySelector('[data-control="' + dir + '"]');
          if (button) button.disabled = !directions[dir];
        }
      }
    };
    watchPagers.delete(surface);
    if (paged) {
      watchPagers.set(surface, setupWatchPager(surface, layout, onLocation));
      const list = activeScroller(surface);
      if (list && scroll != null) list.scrollTop = scroll;
    }
    else if (layout) setupWatchScroll(scroller, layout, d.id, scroll, id => {
      if (scroller.isConnected) onLocation(id);
    });
    else if (scroller && scroll) {
      scroller.scrollTop = scroll;
      const img = scroller.querySelector(".capture-band img");
      if (img && !img.complete) img.addEventListener("load", () => { scroller.scrollTop = scroll; }, {once:true});
    }
    const title = panel.querySelector(".page-name");
    if (title) title.textContent = pageTitle(d.id);
    surface.setAttribute("aria-description", pageTitle(d.id));
    const watchNav = document.getElementById("wrist-navigation");
    if (watchNav && device === "watch") {
      watchNav.querySelector("[data-watch-back]").disabled = !d.trail.length;
      const source = feature.pages[d.id]?.provenance;
      watchNav.querySelector("output").textContent = source || "WATCH 6 实机";
    }
    refreshPageNavigation(panel, device, d.id, swipes);
    const cb = (label, action, disabled = false) =>
      button(label, 'data-control="' + action + '"' + (disabled ? " disabled" : ""));
    const onFace = d.id === "@face";
    const controls = panel.querySelector(".device-controls") || phoneActions;
    if (controls === phoneActions) controls.dataset.owner = device;
    controls.innerHTML =
      cb("返回", "back", !d.trail.length) +
      (device === "watch" && feature.watchScreens
        ? cb("上滑", "up", !swipes.up) + cb("下滑", "down", !swipes.down) + cb("左滑", "left", !swipes.left) + cb("右滑", "right", !swipes.right && !d.trail.length) + cb("表冠", "crown")
        : device === "watch"
        ? cb("左滑", "left", !(onFace || d.id === "@minus")) +
          cb("表冠", "crown") +
          cb("右滑", "right", !(onFace || d.id === "@cards"))
        : cb(pageTitle("@home"), "home") + (!devices.watch ? button(enlargedPhone ? "适应窗口" : "放大", 'data-control="zoom" aria-pressed="' + enlargedPhone + '"') : ""));
    const next = feature.pages[d.id]?.after;
    if (next) timers[device] = setTimeout(() => go(device, next.page, true), next.ms);
  }
  function fitFrame(target, availableWidth, availableHeight) {
      const frame = target.firstElementChild;
      if (!frame || !availableWidth || !availableHeight) return;
      let width, height;
      if (target.classList.contains("mini-slot") && !frame.classList.contains("photo-case")) {
        [width, height] = frame.classList.contains("watch") ? [314, 314] : [274, 589];
      } else [width, height] = [frame.offsetWidth, frame.offsetHeight];
      const fit = Math.min(availableWidth / width, availableHeight / height);
      const scale = target.classList.contains("enlarged") ? Math.min(availableWidth / width, fit * 1.6) : fit;
      frame.style.setProperty("--scale", scale);
      if (target.classList.contains("enlarged")) target.style.setProperty("--frame-height", Math.ceil(height * scale) + "px");
  }
  const sizeObserver = new ResizeObserver(entries => entries.forEach(({target, contentRect}) =>
    fitFrame(target, contentRect.width, contentRect.height)));
  function attachSizes() {
    sizeObserver.disconnect();
    main.querySelectorAll(".stage,.mini-slot").forEach((el) => {
      fitFrame(el, el.clientWidth, el.clientHeight);
      sizeObserver.observe(el);
    });
  }
  if (!context) {
    if (multiApp) {
      document.title = appNames.join("与") + " · 交互演示";
      picker.labels[0].textContent = "切换应用与功能";
    }
    const appGroups = new Map();
    for (const f of features) {
      let parent = picker;
      if (multiApp && f.appName) {
        if (!appGroups.has(f.appName)) {
          const group = document.createElement("optgroup");
          group.label = f.appName;
          picker.add(group);
          appGroups.set(f.appName, group);
        }
        parent = appGroups.get(f.appName);
      }
      parent.append(new Option(f.name, f.id));
    }
    picker.addEventListener("change", () => openFeature(features.find(f => f.id === picker.value)));
    document.getElementById("scene-tools").addEventListener("click", (ev) => {
      if (ev.target.closest("[data-restart]")) {
        flowValues.delete(feature.id);
        selectScene(scene.id);
      }
      if (ev.target.closest("[data-watch-back]")) control("watch","back");
      if (ev.target.closest("[data-watch-list]")) {
        devices.watch = direct("watch","@launcher");
        refreshDevice("watch");
      }
    });
    document.getElementById("scene-tools").addEventListener("change", ev => {
      if (ev.target.matches("[data-phone-jump]") && ev.target.value) go("phone", ev.target.value);
      if (ev.target.matches("[data-watch-jump]") && ev.target.value) {
        go("watch",ev.target.value);
        ev.target.value = "";
      }
    });
    nav.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-side]");
      if (b) selectScene(b.dataset.side);
    });
  }
  function openWristApp(id) {
    const next = features.find(f => f.id === id);
    const scroll = main.querySelector(".watch-app-list")?.scrollTop ?? 0;
    const dest = next.watchReplayEntry || next.entries.launcher.page;
    const targetScene = next.initialView?.page === dest
      ? next.initialView.scene
      : next.scenes.find(s => s.keys.some(k => k[0] === "watch" && k[1] === dest)).id;
    const origin = {feature, scene, devices};
    feature = next;
    syncPicker();
    selectScene(targetScene, ["watch", dest]);
    devices.watch.trail = [{origin, device:"watch", scroll}];
    refreshDevice("watch");
  }
  main.addEventListener("change", ev => {
    if (ev.target.matches("[data-replay-app]") && ev.target.value) openWristApp(ev.target.value);
  });
  main.addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.wristApp) return openWristApp(b.dataset.wristApp);
    const row = b.closest("[data-scene]");
    if (row) {
      const id = row.dataset.scene,
        s = feature.scenes.find((s) => s.id === id);
      selectScene(id, b.hasAttribute("data-key") ? s.keys[Number(b.dataset.key)] : null);
      return;
    }
    if (b.hasAttribute("data-restart")) {
      selectScene(scene.id);
      return;
    }
    const device = b.closest("[data-device]")?.dataset.device;
    if (device && b.dataset.pending) return showPending(b.dataset.pending);
    if (device && b.dataset.assign) {
      for (const [key, value] of Object.entries(JSON.parse(b.dataset.assign))) flowState()[key] = flowText(value);
    }
    if (device && b.dataset.increment) {
      for (const [key, delta] of Object.entries(JSON.parse(b.dataset.increment))) flowState()[key] = String(Number(flowState()[key] || 0) + delta);
    }
    if (device && (b.dataset.month || b.dataset.date)) {
      const state = flowState();
      if (b.dataset.month) {
        const date = new Date((state.month || "2026-11")+"-01T12:00:00");
        date.setMonth(date.getMonth()+Number(b.dataset.month));
        state.month = date.getFullYear()+"-"+String(date.getMonth()+1).padStart(2,"0");
      } else state.date = b.dataset.date;
      refreshDevice(device, b.closest(".scroll").scrollTop);
      return;
    }
    if (device && b.dataset.related) {
      const next = features.find(f => f.id === b.dataset.related);
      const dest = b.dataset.destination;
      const targetDevice = next?.pages[dest]?.device;
      const targetScene = next?.scenes.find(s => s.keys.some(k => k[0] === targetDevice && k[1] === dest));
      if (!targetScene) return;
      if (context) {
        const target = directory.lookup(next.id, targetDevice, dest);
        if (target && target.group !== main.parentElement.dataset.group) return context.follow(target, true);
      }
      const origin = {feature, scene, devices}, scroll = b.closest(".scroll")?.scrollTop || 0;
      feature = next;
      syncPicker();
      selectScene(targetScene.id,[targetDevice,dest],true);
      devices[targetDevice].trail = [{origin, device, scroll}];
      refreshDevice(targetDevice);
      return;
    }
    if (device && b.dataset.page) {
      if (b.dataset.routes) {
        if (!savedRoutes.has(feature.id)) savedRoutes.set(feature.id, new Map());
        const routes = savedRoutes.get(feature.id);
        for (const [entry, target] of Object.entries(JSON.parse(b.dataset.routes))) {
          if (entry === target) routes.delete(entry);
          else routes.set(entry, target);
        }
      }
      if (b.dataset.feature && (b.dataset.feature !== feature.id || b.dataset.entryScene !== scene.id)) {
        const origin = {feature, scene, devices};
        const scroll = b.closest(".surface").querySelector(".scroll")?.scrollTop || 0;
        feature = features.find(f => f.id === b.dataset.feature);
        syncPicker();
        selectScene(b.dataset.entryScene, [device, resolvedPage(b.dataset.page)], true);
        devices[device].trail = [{origin, scroll}];
        refreshDevice(device);
        return;
      }
      const scroll = b.hasAttribute("data-keep-scroll") ? b.closest(".surface")?.querySelector(".scroll")?.scrollTop : 0;
      if (b.dataset.mode === "dismiss") devices[device].trail.pop();
      go(device, resolvedPage(b.dataset.page), ["replace", "dismiss"].includes(b.dataset.mode), b.hasAttribute("data-keep-scroll") ? scroll : null);
    }
    if (device && b.dataset.control) control(device, b.dataset.control);
  });
  let drag = null,
    blockClick = false;
  function horizontalGesture(surface, direction, startX, startY) {
    const device = surface.closest("[data-device]").dataset.device;
    const capture = pageCapture(device, surface.dataset.page);
    const area = capture?.swipeAreas?.[direction];
    if (area) {
      const zone = capture.swipeAreaZones?.[direction];
      const anchor = zone ? surface.querySelector('[data-capture-zone="' + zone + '"]') : surface;
      if (!anchor) return;
      const rect = anchor.getBoundingClientRect();
      const x = 100 * (startX - rect.left) / rect.width;
      const y = 100 * (startY - rect.top) / rect.height;
      if (x < area[0] || x > area[2] || y < area[1] || y > area[3]) {
        if (device === "phone" && direction === "right") control(device,"back");
        return;
      }
    }
    control(device, direction);
  }
  main.addEventListener("pointerdown", (ev) => {
    const surface = ev.target.closest(".surface");
    if (!surface || !ev.isPrimary || ev.button !== 0) return;
    blockClick = false;
    const scroll = activeScroller(surface);
    drag = {
      surface,
      scroll,
      top: scroll?.scrollTop || 0,
      x: ev.clientX,
      y: ev.clientY,
      id: ev.pointerId,
      axis: null,
      device: surface.closest("[data-device]").dataset.device,
      scale: surface.getBoundingClientRect().width / surface.offsetWidth,
    };
    const pager = watchPagers.get(surface);
    if (pager) {
      drag.pager = pager;
      drag.height = surface.getBoundingClientRect().height;
      drag.samples = [{time:ev.timeStamp, y:ev.clientY}];
    }
  });
  function samplePager(gesture, ev) {
    const samples = gesture.samples;
    samples.push({time:ev.timeStamp, y:ev.clientY});
    while (samples.length > 1 && ev.timeStamp - samples[0].time > 100) samples.shift();
    const first = samples[0];
    return (first.y - ev.clientY) / gesture.height / Math.max(1, ev.timeStamp - first.time);
  }
  window.addEventListener("pointermove", (ev) => {
    if (!drag || drag.id !== ev.pointerId) return;
    if (!drag.surface.isConnected) { drag = null; return; }
    const dx = ev.clientX - drag.x,
      dy = ev.clientY - drag.y;
    if (!drag.axis && Math.max(Math.abs(dx), Math.abs(dy)) > 8) {
      drag.axis = Math.abs(dx) > Math.abs(dy) * 1.2 ? "x" : "y";
      drag.surface.setPointerCapture(ev.pointerId);
      if (drag.axis === "y" && drag.pager) {
        drag.scrollCard = canScrollIn(drag.scroll, -dy);
        if (!drag.scrollCard) drag.startPage = drag.pager.grab();
      }
    }
    if (drag.pager) {
      samplePager(drag, ev);
      if (drag.axis === "y") {
        if (drag.scrollCard) drag.scroll.scrollTop = drag.top - dy / drag.scale;
        else drag.pager.drag(drag.startPage, -dy / drag.height);
      }
      return;
    }
    if (drag.axis === "y" && drag.scroll && (ev.pointerType === "mouse" || drag.surface.classList.contains("vertical-pages")))
      drag.scroll.scrollTop = drag.top - dy / drag.scale;
    if (drag.axis && drag.device === "watch" && !drag.surface.classList.contains("list-screen")) {
      const horiz = drag.axis === "x";
      const distance = horiz ? dx : dy;
      const dest = pageSwipes("watch", devices.watch.id)[horiz ? (dx < 0 ? "left" : "right") : (dy < 0 ? "up" : "down")];
      const atEdge = horiz || !drag.scroll || Math.abs(drag.scroll.scrollTop-drag.top) < 2;
      if (dest && atEdge) {
        if (drag.peek?.dataset.target !== dest) {
          drag.peek?.remove();
          drag.peek = document.createElement("div");
          drag.peek.className = "wrist-peek";
          drag.peek.dataset.target = dest;
          drag.peek.inert = true;
          drag.peek.innerHTML = screenContent("watch",dest);
          drag.surface.append(drag.peek);
        }
        const size = horiz ? drag.surface.offsetWidth : drag.surface.offsetHeight;
        const shift = Math.max(-size, Math.min(size, distance / drag.scale));
        const axis = horiz ? "translateX(" : "translateY(";
        drag.surface.firstElementChild.style.transform = axis + shift + "px)";
        drag.peek.style.transform = axis + (shift + (distance < 0 ? size : -size)) + "px)";
      } else if (drag.peek) {
        drag.peek.remove();
        drag.peek = null;
        drag.surface.firstElementChild.style.transform = "";
      }
    }
  });
  function endGesture(ev) {
    if (!drag || drag.id !== ev.pointerId) return;
    const { axis, device, x, y, surface, top, scroll, pager } = drag;
    const dx = ev.clientX - x, dy = ev.clientY - y;
    if (pager && axis === "y" && !drag.scrollCard && watchPagers.get(surface) === pager && surface.isConnected) {
      const delta = -dy / drag.height, velocity = samplePager(drag, ev);
      const flick = Math.abs(delta) >= .07 && Math.sign(delta) * velocity >= .0017;
      pager.step(ev.type === "pointerup" && (Math.abs(delta) >= .2 || flick) ? Math.sign(delta) : 0);
    }
    const horizontal = axis === "x" || (!axis && Math.abs(dx) > Math.abs(dy)*1.2);
    if (drag.peek) {
      drag.peek.remove();
      surface.firstElementChild.style.transform = "";
    }
    drag = null;
    if (axis || (horizontal && Math.abs(dx) > 27)) {
      blockClick = true;
      setTimeout(() => {
        blockClick = false;
      }, 0);
    }
    if (ev.type !== "pointerup" || !surface.isConnected) return;
    if (horizontal && Math.abs(dx) > 27) horizontalGesture(surface, dx > 0 ? "right" : "left", x, y);
    if (ev.pointerType === "mouse" && axis === "y" && Math.abs(dy) > 27 && exitScrollEdge(surface, top, dy < 0 ? "up" : "down")) return;
    if (axis === "y" && surface.classList.contains("vertical-pages") && Math.abs(dy) > 27 && Math.abs((scroll?.scrollTop || 0)-top) < 2)
      control(device, ev.clientY < y ? "up" : "down");
  }
  function exitScrollEdge(surface, top, direction) {
    if (!surface.isConnected || !surface.classList.contains("list-screen")) return false;
    const id = surface.dataset.page, dest = pageSwipes("watch", id)[direction];
    if (!dest || sameWatchScroll("watch", id, dest)) return false;
    const list = surface.querySelector(".watch-app-list");
    const atEdge = direction === "down" ? top < 1 : top >= list.scrollHeight - list.clientHeight - 1;
    if (atEdge) control("watch", direction);
    return atEdge;
  }
  let touchEdge;
  main.addEventListener("touchstart", ev => {
    const surface = ev.target.closest(".list-screen");
    const t = ev.touches[0];
    touchEdge = surface && ev.touches.length === 1 ? {surface, x:t.clientX, y:t.clientY, top:surface.querySelector(".scroll").scrollTop} : null;
  }, {passive:true});
  main.addEventListener("touchcancel", () => { touchEdge = null; }, {passive:true});
  main.addEventListener("touchend", ev => {
    if (!touchEdge) return;
    const {surface,x,y,top} = touchEdge, t = ev.changedTouches[0];
    touchEdge = null;
    const dy = t.clientY-y;
    if (Math.abs(dy)>27 && Math.abs(dy)>Math.abs(t.clientX-x)*1.2) exitScrollEdge(surface, top, dy < 0 ? "up" : "down");
  }, {passive:true});
  let lastWheel = 0;
  let wheelGesture;
  main.addEventListener("wheel", ev => {
    const surface = ev.target.closest(".surface");
    if (!surface || ev.ctrlKey) return;
    const pager = watchPagers.get(surface);
    if (pager) ev.preventDefault();
    if (surface.classList.contains("list-screen") && Math.abs(ev.deltaY) >= Math.abs(ev.deltaX) && ev.deltaY) {
      ev.preventDefault();
      const list = surface.querySelector(".watch-app-list");
      const unit = ev.deltaMode === 1 ? 16 : ev.deltaMode === 2 ? list.clientHeight : 1;
      const now = performance.now(), fresh = !wheelGesture || now - wheelGesture.time > 180;
      wheelGesture = {x:0, y:0, axis:"y", time:now, handled:false};
      if (fresh && exitScrollEdge(surface, list.scrollTop, ev.deltaY > 0 ? "up" : "down")) {
        wheelGesture.handled = true;
        return;
      }
      list.scrollTop += ev.deltaY * unit * surface.clientHeight / surface.getBoundingClientRect().height;
      return;
    }
    const now = performance.now();
    if (!wheelGesture || now - wheelGesture.time > 180) {
      wheelGesture = {x: 0, y: 0, axis: null, handled: false};
    }
    wheelGesture.time = now;
    const unit = ev.deltaMode === 1 ? 16 : ev.deltaMode === 2 ? surface.clientWidth : 1;
    wheelGesture.x += ev.deltaX * unit;
    wheelGesture.y += ev.deltaY * unit;
    const x = Math.abs(wheelGesture.x), y = Math.abs(wheelGesture.y);
    if (!wheelGesture.axis && Math.max(x, y) > 8) {
      if (x > y * 1.2) wheelGesture.axis = "x";
      else if (y > x * 1.2) wheelGesture.axis = "y";
    }
    if (!wheelGesture.axis && Math.abs(ev.deltaX) > Math.abs(ev.deltaY) * 1.2) {
      ev.preventDefault();
      return;
    }
    if (wheelGesture.axis === "x") {
      ev.preventDefault();
      if (!wheelGesture.handled && x > 27) {
        wheelGesture.handled = true;
        horizontalGesture(surface, wheelGesture.x < 0 ? "right" : "left", ev.clientX, ev.clientY);
      }
      return;
    }
    if (pager) {
      if (wheelGesture.axis !== "y" || wheelGesture.handled) return;
      if (!Object.hasOwn(wheelGesture, "cardList")) {
        const list = activeScroller(surface);
        wheelGesture.cardList = canScrollIn(list, wheelGesture.y) ? list : null;
      }
      if (wheelGesture.cardList) {
        wheelGesture.cardList.scrollTop += ev.deltaY * unit * surface.clientHeight / surface.getBoundingClientRect().height;
      } else if (y >= 18) {
        wheelGesture.handled = true;
        pager.step(Math.sign(wheelGesture.y));
      }
      return;
    }
    if (!surface.classList.contains("vertical-pages") || wheelGesture.axis !== "y" || Math.abs(ev.deltaY) < 2) return;
    const scroller = surface.querySelector(".scroll");
    if (scroller && (ev.deltaY > 0 ? scroller.scrollTop + scroller.clientHeight < scroller.scrollHeight-2 : scroller.scrollTop > 1)) return;
    ev.preventDefault();
    if (surface.dataset.page === "@face" || feature.pages[surface.dataset.page]?.facePanel || wheelGesture.handled) {
      if (!wheelGesture.handled && y > 18) {
        wheelGesture.handled = true;
        control("watch", wheelGesture.y > 0 ? "up" : "down");
      }
      return;
    }
    if (Date.now()-lastWheel > 280) {
      lastWheel = Date.now();
      control(surface.closest("[data-device]").dataset.device, ev.deltaY > 0 ? "up" : "down");
    }
  }, {passive:false});
  window.addEventListener("pointerup", endGesture);
  window.addEventListener("pointercancel", endGesture);
  main.addEventListener(
    "click",
    (ev) => {
      if (blockClick) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
      }
    },
    true,
  );
  main.addEventListener("keydown", (ev) => {
    const surface = ev.target.closest(".surface");
    if (!surface) return;
    const device = surface.closest("[data-device]").dataset.device;
    const pager = watchPagers.get(surface);
    if (pager && ["ArrowUp", "ArrowDown", "Home", "End"].includes(ev.key)) {
      ev.preventDefault();
      if (ev.key === "Home" || ev.key === "End") pager.boundary(ev.key === "End");
      else pager.advance(ev.key === "ArrowDown" ? 1 : -1);
      return;
    }
    if (surface.classList.contains("list-screen")) {
      if (ev.key === "Enter" && ev.target === surface && !surface.querySelector(".watch-panels")) {
        ev.preventDefault();
        surface.querySelector(".watch-app-row[aria-current], .study-row[aria-current] button")?.click();
        return;
      }
      if (["ArrowUp","ArrowDown","Home","End"].includes(ev.key)) {
        ev.preventDefault();
        surface.focus({preventScroll:true});
        const list = surface.querySelector(".watch-app-list");
        if (ev.key === "Home" || ev.key === "End") centerWatchRow(list, ev.key === "Home" ? 0 : list.children.length - 1);
        else control(device, ev.key === "ArrowDown" ? "up" : "down");
        return;
      }
    }
    if (device === "watch" && ["ArrowLeft", "ArrowRight"].includes(ev.key)) {
      ev.preventDefault();
      control(device, ev.key === "ArrowLeft" ? "left" : "right");
    }
    if (device === "phone" && feature.pages[devices.phone.id]?.capture?.swipe && ["ArrowLeft", "ArrowRight"].includes(ev.key)) {
      ev.preventDefault();
      control(device, ev.key === "ArrowRight" ? "left" : "right");
    }
    if (ev.key === "Escape") {
      ev.preventDefault();
      control(device, "back");
    }
    if (["ArrowDown", "ArrowUp"].includes(ev.key)) {
      ev.preventDefault();
      if (device === "watch" && (surface.dataset.page === "@face" || feature.pages[surface.dataset.page]?.facePanel))
        control(device, ev.key === "ArrowUp" ? "up" : "down");
      else if (surface.classList.contains("vertical-pages")) control(device, ev.key === "ArrowDown" ? "up" : "down");
      else surface.querySelector(".scroll")?.scrollBy(0, ev.key === "ArrowDown" ? 90 : -90);
    }
  });
  phoneActions.addEventListener("click", (ev) => {
    const action = ev.target.closest("[data-control]");
    if (!action) return;
    document.getElementById("instructions").close();
    control(phoneActions.dataset.owner, action.dataset.control);
  });
  if (!context) openFeature(feature);
  return {visitPage, helpControls:phoneActions};
}

const stageRoot = document.getElementById("main");
let collection;
if (navigation) {
  document.body.classList.add("collection-demo", "phone-demo");
  document.getElementById("app-name").textContent = "穿戴演示";
  document.querySelector(".feature-picker").hidden = true;
  document.querySelector("#instructions p").textContent =
    "勾选一至三个展示入口。点击设备后，界面目录会显示其当前位置和可用操作。也可在目录中搜索界面、复制定位和设置本机开场。";
  if (media.watch6Case) {
    const bytes = Uint8Array.from(atob(media.watch6Case.split(",")[1]), c => c.charCodeAt(0));
    const caseURL = URL.createObjectURL(new Blob([bytes], {type:"image/png"}));
    document.body.style.setProperty("--watch6-case", 'url("' + caseURL + '")');
  }
  document.title = navigation.groups.map(group => group.label).join(" · ");
  collection = createCollectionWorkspace(navigation, stageRoot, createDemoPlayer);
} else {
  createDemoPlayer(stageRoot);
}
document.getElementById("help").onclick = () => {
  if (collection) {
    document.getElementById("phone-actions").replaceChildren(collection.activePlayer().helpControls);
    const watch = document.querySelector(".entry-pane[data-active] .device-panel.watch");
    const help = document.querySelector(".watch-help");
    help.hidden = !watch;
    if (watch) help.textContent = "点击表冠打开应用列表，上下滑动浏览，点选应用，右滑返回。";
  }
  document.getElementById("instructions").showModal();
};
if (reports.length) {
  const dialog = document.getElementById("baseline-report");
  const frame = dialog.querySelector("iframe");
  const links = document.createElement("div");
  links.className = "baseline-links";
  for (const report of reports) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = report.title;
    button.onclick = () => {
      document.getElementById("report-title").textContent = report.title;
      frame.title = report.title;
      frame.srcdoc = report.html;
      dialog.showModal();
    };
    links.append(button);
  }
  dialog.addEventListener("close", () => frame.removeAttribute("srcdoc"));
  document.getElementById("instructions").insertBefore(links, document.getElementById("close-help"));
}
document.getElementById("close-help").onclick = () => document.getElementById("instructions").close();
