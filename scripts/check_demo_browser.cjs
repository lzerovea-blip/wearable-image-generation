// Optional browser regression check. Run with Node, Playwright and a local Chrome installation.
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

async function inspect(browser, file, touch) {
  const ctx = await browser.newContext({
    offline: true, hasTouch: touch, isMobile: touch,
    permissions: ["clipboard-read", "clipboard-write"],
    viewport: touch ? { width: 390, height: 844 } : { width: 1440, height: 900 }
  });
  try {
    const page = await ctx.newPage();
    const errors = [], requests = [];
    page.on("pageerror", err => errors.push(err.message));
    page.on("request", req => { if (/^https?:/.test(req.url())) requests.push(req.url()); });
    await page.goto(pathToFileURL(path.resolve(file)).href);
    const activePane = page.locator(".entry-pane[data-active]");
    const screen = activePane.locator(".surface");
    const at = id => page.waitForFunction(id => document.querySelector(".entry-pane[data-active] .surface")?.dataset.page === id, id);
    const press = node => touch ? node.tap() : node.click();
    const directory = page.getByRole("dialog", {name: "界面目录"});
    const openDirectory = () => press(page.getByRole("button", {name: "界面目录", exact: true}));
    const summary = page.locator("#entry-chooser summary");
    const checks = page.locator("#entry-chooser input");
    const check = id => page.locator('#entry-chooser input[value="' + id + '"]');
    async function choose(...groups) {
      await press(summary);
      for (const id of groups) if (!await check(id).isChecked()) await press(check(id));
      for (const box of await checks.all()) {
        if (!groups.includes(await box.inputValue()) && await box.isChecked()) await press(box);
      }
      assert.deepEqual((await page.locator(".entry-pane:visible").evaluateAll(els =>
        els.map(el => el.dataset.group))).sort(), [...groups].sort());
      if (groups.length === 1) assert(await check(groups[0]).isDisabled());
      await press(summary);
    }
    async function currentAction(name) {
      await openDirectory();
      await press(directory.getByRole("button", {name, exact: true}));
      assert.equal(await directory.count(), 0);
    }
    async function checkStage() {
      assert.equal(await page.locator(".sidebar").isVisible(), false);
      assert.equal(await directory.count(), 0);
      const box = await activePane.locator(".stage").boundingBox();
      const viewport = page.viewportSize();
      assert(box.width >= viewport.width - 24 && box.height >= viewport.height - 80, "设备舞台应占满顶栏以下的区域");
      assert(Math.abs(box.x + box.width / 2 - viewport.width / 2) < 2);
    }
    await at("today");
    await checkStage();
    await press(screen.getByRole("button", {name: "查看详情", exact: true}));
    await at("today-insight");
    await currentAction("完整健康解读");
    await at("digest");
    await press(screen.getByRole("button", {name: "返回", exact: true}));
    await at("today-insight");
    await choose("research");
    await at("home");
    await checkStage();
    if (!touch) {
      const totals = await page.evaluate(async () => {
        const groups = {};
        let images = 0;
        for (const row of navigation.pages) {
          collection.showPage(row);
          const pane = document.querySelector(".entry-pane[data-active]");
          const surface = pane.querySelector(".surface");
          if (surface.dataset.page !== row.page || pane.dataset.group !== row.group ||
              document.querySelector("#directory-current").title !== row.key) throw Error(row.key);
          for (const img of surface.querySelectorAll("img")) { await img.decode(); images++; }
          groups[row.group] = (groups[row.group] || 0) + 1;
        }
        for (const [key, target] of Object.entries(navigation.aliases)) {
          if (collection.directory.lookup(...key.split("/"))?.key !== target) throw Error(key);
        }
        return { groups, features: features.length, aliases: Object.keys(navigation.aliases).length, images };
      });
      console.log(totals);
      await page.reload();
    }
    await choose("watch");
    await at("@face");
    await checkStage();
    await press(activePane.locator(".crown"));
    assert.equal(await page.locator(".watch-replay").count(), 0);
    await press(screen.getByRole("button", { name: "微体检", exact: true }));
    await at("live-066");
    await press(screen.getByRole("button", {name: "测量", exact: true}));
    assert.match(await activePane.locator(".entry-status").innerText(), /待实机采集/);
    const cdp = touch && await ctx.newCDPSession(page);
    async function swipe(dx, dy) {
      const box = await screen.boundingBox();
      const x = box.x + box.width * (dx ? 0.28 : 0.5);
      const y = box.y + box.height * (dy ? 0.74 : 0.5);
      if (touch) await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
      else { await page.mouse.move(x, y); await page.mouse.down(); }
      for (let i = 1; i <= 6; i++) {
        const point = { x: x + dx * box.width * i/6, y: y + dy * box.height * i/6 };
        if (touch) await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [point] });
        else await page.mouse.move(point.x, point.y);
      }
      if (touch) await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      else await page.mouse.up();
    }
    await swipe(0, -0.5);
    await at("live-069");
    await press(screen.getByRole("button", { name: "历史报告", exact: true }));
    await at("live-072");
    await swipe(0.45, 0);
    await at("live-069");
    await swipe(0.45, 0);
    await screen.getByRole("button", {name: "锻炼记录", exact: true}).waitFor({state:"attached"});
    await press(screen.getByRole("button", {name: "锻炼记录", exact: true}));
    await press(screen.getByRole("button", {name: "登山 · 2.45 公里", exact: true}));
    await press(screen.getByRole("button", {name: "AI 解读", exact: true}));
    await at("live-027");
    await currentAction("查看后续分析状态");
    await at("live-028");
    await currentAction("查看解读结果");
    await at("live-029");
    await swipe(0.45, 0);
    await at("live-028");
    const key = "watch6-insight/watch/sleep-score";
    await openDirectory();
    await directory.getByRole("searchbox").fill("睡眠质量评分");
    await press(directory.locator('[data-location="' + key + '"]'));
    await at("sleep-score");
    assert.equal(await directory.count(), 0);
    await openDirectory();
    await press(directory.getByRole("button", {name:"复制页面定位"}));
    await page.waitForFunction(key => navigator.clipboard.readText().then(text => text.includes(key)), key);
    await press(directory.getByRole("button", {name:"设为本机开场"}));
    await page.reload();
    await at("sleep-score");
    await checkStage();
    await openDirectory();
    await press(directory.getByRole("button", {name:"恢复默认开场"}));
    await page.reload();
    await at("today");
    for (const groupSet of [["health","watch"], ["watch","research"], ["research","health"], ["research","health","watch"]])
      await choose(...groupSet);
    const visible = page.locator(".entry-pane:visible");
    const first = await visible.nth(0).boundingBox(), second = await visible.nth(1).boundingBox();
    assert(touch ? second.y >= first.y + first.height : second.x >= first.x + first.width);
    const watch = page.locator('.entry-pane[data-group="watch"]');
    const health = page.locator('.entry-pane[data-group="health"]');
    await press(watch.locator(".crown"));
    await press(watch.getByRole("button", {name: "微体检", exact: true}));
    await at("live-066");
    await press(health.getByRole("button", {name: "查看详情", exact: true}));
    await at("today-insight");
    assert.equal(await watch.locator(".surface").getAttribute("data-page"), "live-066");
    await currentAction("完整健康解读");
    await at("digest");
    await choose("health", "research");
    await choose("health", "research", "watch");
    await at("live-066");
    assert.equal(await health.locator(".surface").getAttribute("data-page"), "digest");
    await openDirectory();
    const handoff = "huawei-health-today-devices/phone/device-research";
    await directory.getByRole("searchbox").fill(handoff);
    await press(directory.locator('[data-location="' + handoff + '"]'));
    await at("device-research");
    const researchScreen = page.locator('.entry-pane[data-group="research"] .surface');
    const researchPage = await researchScreen.getAttribute("data-page");
    await press(screen.getByRole("button", {name:"前往", exact:true}));
    await at("h-detect");
    await swipe(0.45, 0);
    await at("device-research");
    assert.equal(await researchScreen.getAttribute("data-page"), researchPage);
    assert.equal(await watch.locator(".surface").getAttribute("data-page"), "live-066");
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, []);
    console.log(touch ? "模拟触屏通过" : "桌面通过");
  } finally {
    await ctx.close();
  }
}

(async () => {
  const file = process.argv[2] || "outputs/20261119-WATCH6与手机全功能合集/index.html";
  const browser = await chromium.launch({channel: "chrome"});
  try {
    for (const touch of [false, true]) await inspect(browser, file, touch);
  } finally {
    await browser.close();
  }
})().catch(err => { console.error(err); process.exitCode = 1; });
