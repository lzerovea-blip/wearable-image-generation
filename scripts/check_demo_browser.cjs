// Optional browser regression check. Run with Node, Playwright and a local Chrome installation.
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

async function inspect(browser, file, touch) {
  const ctx = await browser.newContext({
    offline: true, hasTouch: touch, isMobile: touch,
    viewport: touch ? { width: 390, height: 844 } : { width: 1440, height: 900 }
  });
  try {
    const page = await ctx.newPage();
    const errors = [], requests = [];
    page.on("pageerror", err => errors.push(err.message));
    page.on("request", req => { if (/^https?:/.test(req.url())) requests.push(req.url()); });
    await page.goto(pathToFileURL(path.resolve(file)).href);
    const screen = page.locator("main .surface");
    const at = id => page.waitForFunction(id => document.querySelector("main .surface")?.dataset.page === id, id);
    const press = node => touch ? node.tap() : node.click();
    await at("today");
    if (!touch) {
      const totals = await page.evaluate(async () => {
        const groups = {};
        let images = 0;
        for (const row of navigation.pages) {
          visitPage(row);
          const surface = main.querySelector(".surface");
          if (surface.dataset.page !== row.page || picker.value !== row.group ||
              document.querySelector("#directory-current").title !== row.key) throw Error(row.key);
          for (const img of surface.querySelectorAll("img")) { await img.decode(); images++; }
          groups[row.group] = (groups[row.group] || 0) + 1;
        }
        for (const [key, target] of Object.entries(navigation.aliases)) {
          if (directory.lookup(...key.split("/"))?.key !== target) throw Error(key);
        }
        return { groups, features: features.length, aliases: Object.keys(navigation.aliases).length, images };
      });
      console.log(totals);
    }
    await page.locator("#feature").selectOption("watch");
    await at("@face");
    await press(page.locator(".crown"));
    await press(screen.getByRole("button", { name: "微体检", exact: true }));
    await at("live-066");
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
