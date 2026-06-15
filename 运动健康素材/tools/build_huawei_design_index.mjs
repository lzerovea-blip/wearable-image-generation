import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const workspace = path.resolve(path.dirname(__filename), "..");
const today = "2026-06-10";

const outputDir = path.join(workspace, "outputs");
const outputPath = path.join(outputDir, "华为设计规范与资源索引.xlsx");
const officialManifestPath = path.join(workspace, "官方设计规范", "下载记录", "官方设计资源manifest.json");

const imageExtensions = new Set([".jpg", ".jpeg", ".png", ".webp", ".heic"]);

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.name === "node_modules" || entry.name === ".git" || entry.name === "outputs") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await walk(full));
    } else {
      files.push(full);
    }
  }
  return files;
}

function rel(filePath) {
  return path.relative(workspace, filePath);
}

function classifyProduct(relPath) {
  if (relPath.startsWith("华为运动健康app/")) return "App";
  if (relPath.startsWith("华为穿戴/")) return "穿戴设备";
  if (relPath.startsWith("华为创新研究app/")) return "创新研究 App";
  if (relPath.startsWith("官方设计规范/")) return "官方设计规范";
  return "待分类";
}

function guessSource(relPath) {
  if (relPath.startsWith("华为运动健康app/") || relPath.startsWith("华为穿戴/")) return "用户截图";
  if (relPath.startsWith("官方设计规范/")) return "官方整理";
  return "待确认";
}

function addRows(sheet, range, rows) {
  sheet.getRange(range).values = rows;
}

function widthFor(value, min = 12, max = 48) {
  const len = String(value ?? "").length;
  return Math.max(min, Math.min(max, Math.ceil(len * 1.2)));
}

function columnName(index) {
  let n = index;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

function styleSheet(sheet, colCount, rowCount, widths = []) {
  const lastCol = columnName(colCount);
  const header = sheet.getRange(`A1:${lastCol}1`);
  header.format = {
    fill: "#DDEBFF",
    font: { bold: true, color: "#111827" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#D1D5DB" },
  };
  const body = sheet.getRange(`A1:${lastCol}${rowCount}`);
  body.format = {
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#D1D5DB" },
  };
  body.format.autofitRows();
  body.format.autofitColumns();
}

const allFiles = await walk(workspace);
const screenshots = allFiles
  .filter((file) => imageExtensions.has(path.extname(file).toLowerCase()))
  .filter((file) => {
    const relative = rel(file);
    return relative.startsWith("华为运动健康app/") || relative.startsWith("华为穿戴/");
  })
  .map((file, index) => {
    const relative = rel(file);
    return [
      `SHOT-${String(index + 1).padStart(4, "0")}`,
      classifyProduct(relative),
      "待分类",
      "待识别",
      relative,
      guessSource(relative),
      "",
      today,
      "待拆解",
      "鸿蒙字体",
      "待补充：页面目标、核心模块、控件、icon、UX 流程、图生图提示词",
    ];
  });

let manifestRows = [];
try {
  const manifest = JSON.parse(await fs.readFile(officialManifestPath, "utf8"));
  manifestRows = manifest.map((item, index) => [
    `RES-${String(index + 5).padStart(4, "0")}`,
    item.resource_name,
    item.resource_type,
    item.resource_name.includes("穿戴") ? "穿戴设备" : item.resource_name.includes("智慧屏") ? "智慧屏" : "App / 多设备",
    item.source_link,
    item.destination_root,
    `${item.resource_name}，来自 ${item.source_zip}，已解压 ${item.file_count} 个文件。示例：${(item.sample_files ?? []).slice(0, 3).join("；")}`,
    item.resource_type === "Icon资源" ? "Icon 风格与图生图图标参考。" : item.resource_type === "模板资源" ? "设备机框、启动页或界面模板参考。" : "组件、交互和界面结构拆解参考。",
    item.status,
    item.registered_date,
    item.priority,
  ]);
} catch {
  manifestRows = [];
}

const resourceRows = [
  [
    "RES-0001",
    "官方设计入口",
    "设计要求",
    "App / 穿戴设备 / 多设备",
    "https://developer.huawei.com/consumer/cn/design/devstart/",
    "官方设计规范/README.md",
    "官方 DevStart 入口；资源包已由用户人工补入，页面正文仍需后续联网核验。",
    "作为运动健康素材库的官方设计基线入口。",
    "待联网核验",
    today,
    "P0",
  ],
  [
    "RES-0002",
    "华为设计要求学习笔记",
    "设计要求",
    "App / 穿戴设备",
    "https://developer.huawei.com/consumer/cn/design/devstart/",
    "官方设计规范/设计要求/华为设计要求学习笔记.md",
    "用于建立页面、控件、icon、UX 拆解口径；内容需后续逐条关联官方页面。",
    "拆解字段、图生图提示词、官方规范映射。",
    "待官方逐条核验",
    today,
    "P0",
  ],
  [
    "RES-0003",
    "待下载资源清单",
    "下载清单",
    "App / 穿戴设备 / 多设备",
    "https://developer.huawei.com/consumer/cn/design/devstart/",
    "官方设计规范/下载记录/待下载资源清单.md",
    "记录需要补充的官方组件、icon、模板、示例截图资源；当前已有部分资源包补入。",
    "后续资源核验和增补的工作清单。",
    "部分已补入",
    today,
    "P0",
  ],
  [
    "RES-0004",
    "资源下载失败记录",
    "下载记录",
    "全部",
    "https://developer.huawei.com/consumer/cn/design/devstart/",
    "官方设计规范/下载记录/资源下载失败记录.md",
    "记录本次自动联网失败原因，防止误判为已完成资源下载。",
    "审计与后续重试依据。",
    "已记录",
    today,
    "P0",
  ],
  ...manifestRows,
];

const designMappingRows = [
  ["REQ-0001", "字体", "App/穿戴界面字体统一使用鸿蒙字体。", "App / 穿戴设备", "页面标题、正文、数据指标、按钮、图生图提示词", "已确认用户要求", "AGENTS.md / memory", "高"],
  ["REQ-0002", "信息层级", "先描述页面目标，再拆核心数据、模块、控件、状态和反馈。", "App / 穿戴设备", "截图拆解、页面索引、UX 表", "待官方核验", "DevStart 待补", "高"],
  ["REQ-0003", "组件拆解", "按钮、列表、卡片、Tab、导航、弹窗、开关、选择器、进度、图表等需单独记录。", "App / 穿戴设备", "控件设计表、图生图提示词", "待官方核验", "DevStart 待补", "高"],
  ["REQ-0004", "Icon 描述", "记录 icon 语义、风格、颜色、状态和适用功能。", "App / 穿戴设备", "Icon 素材库、图生图素材描述", "待官方核验", "DevStart 待补", "高"],
  ["REQ-0005", "多设备适配", "手机 App 与穿戴设备分别记录布局密度、触控目标、内容优先级和数据同步关系。", "App / 穿戴设备", "运动健康 App 与手表/手环界面拆解", "待官方核验", "DevStart 待补", "中"],
  ["REQ-0006", "状态与反馈", "默认、选中、禁用、加载、空状态、错误、成功和告警状态需要拆开记录。", "App / 穿戴设备", "控件状态、健康数据反馈、运动完成反馈", "待官方核验", "DevStart 待补", "中"],
];

const decompositionHeader = [
  "素材ID",
  "产品形态",
  "一级功能",
  "二级页面",
  "截图路径",
  "来源",
  "设计来源",
  "适用平台",
  "页面目标",
  "核心UX流程",
  "模块/控件名称",
  "控件类型",
  "控件状态",
  "Icon描述",
  "视觉元素",
  "文案内容",
  "字体",
  "组件规范依据",
  "交互规则依据",
  "视觉风格依据",
  "资源授权/来源链接",
  "适用图生图场景",
  "图生图提示词",
  "备注",
];

const decompositionExamples = [
  [
    "EX-0001",
    "App",
    "健康数据",
    "待识别页面",
    "华为运动健康app/示例截图路径.jpg",
    "用户截图",
    "华为开发者设计规范待补",
    "手机",
    "展示健康指标概览并引导进入详情。",
    "打开 App > 查看健康卡片 > 点击指标进入详情。",
    "健康指标卡片",
    "卡片 / 数据模块",
    "默认",
    "指标语义图标，需记录线性或面性风格、颜色、尺寸和含义。",
    "白底卡片、圆角、数据大字、次级说明、状态色。",
    "待从截图识别",
    "鸿蒙字体",
    "待关联官方组件规范",
    "待关联官方交互规范",
    "待关联官方视觉规范",
    "https://developer.huawei.com/consumer/cn/design/devstart/",
    "生成运动健康 App 健康数据卡片。",
    "鸿蒙字体，运动健康 App，白色卡片，健康数据指标，清晰信息层级，官方设计风格。",
    "示例行，正式拆解时替换。",
  ],
];

const downloadRows = [
  ["2026-06-10", "https://developer.huawei.com/consumer/cn/design/devstart/", "页面读取", "失败", "DNS/审批超时/Node fetch failed", "官方设计规范/下载记录/资源下载失败记录.md"],
  ["2026-06-10", "官方组件资源", "人工补入", "部分完成", "已解压组件库、穿戴、智慧屏、实况窗、账号登录、设备连接流程；页面正文仍需联网核验", "官方设计规范/组件资源/"],
  ["2026-06-10", "官方 Icon 资源", "人工补入", "部分完成", "已解压 HarmonyOS 应用图标；仍需核验官方图标规范正文", "官方设计规范/Icon资源/"],
  ["2026-06-10", "官方模板资源", "人工补入", "部分完成", "已解压启动页与产品机框资源；仍需核验官方模板说明正文", "官方设计规范/模板资源/"],
  ...manifestRows.map((row) => [row[9], row[1], "人工下载资源解压", row[8], row[6], row[5]]),
];

const workbook = Workbook.create();
const overview = workbook.worksheets.add("资源索引");
const mapping = workbook.worksheets.add("设计要求映射");
const screenshotSheet = workbook.worksheets.add("已有截图清单");
const template = workbook.worksheets.add("截图拆解字段模板");
const downloadLog = workbook.worksheets.add("下载记录");

const resourceHeader = ["资源ID", "资源名称", "资源类型", "适用端", "来源链接", "本地路径", "资源说明", "可复用用途", "状态", "采集/登记日期", "优先级"];
addRows(overview, `A1:K${resourceRows.length + 1}`, [resourceHeader, ...resourceRows]);
styleSheet(overview, resourceHeader.length, resourceRows.length + 1, [12, 24, 16, 22, 48, 44, 48, 40, 16, 16, 10]);

const mappingHeader = ["要求ID", "设计维度", "要求/拆解口径", "适用端", "素材库应用", "核验状态", "依据链接/位置", "重要性"];
addRows(mapping, `A1:H${designMappingRows.length + 1}`, [mappingHeader, ...designMappingRows]);
styleSheet(mapping, mappingHeader.length, designMappingRows.length + 1, [12, 16, 52, 20, 36, 18, 28, 10]);

const screenshotHeader = ["素材ID", "产品形态", "一级功能", "二级页面", "截图路径", "来源", "来源链接", "采集/截图日期", "拆解状态", "字体", "备注"];
addRows(screenshotSheet, `A1:K${screenshots.length + 1}`, [screenshotHeader, ...screenshots]);
styleSheet(screenshotSheet, screenshotHeader.length, screenshots.length + 1, [12, 14, 14, 18, 54, 14, 28, 16, 14, 12, 48]);

addRows(template, `A1:X${decompositionExamples.length + 1}`, [decompositionHeader, ...decompositionExamples]);
styleSheet(template, decompositionHeader.length, decompositionExamples.length + 1, decompositionHeader.map((h) => widthFor(h, 12, 32)));

const downloadHeader = ["日期", "目标/来源", "动作", "结果", "原因/下一步", "记录或目录"];
addRows(downloadLog, `A1:F${downloadRows.length + 1}`, [downloadHeader, ...downloadRows]);
styleSheet(downloadLog, downloadHeader.length, downloadRows.length + 1, [14, 48, 16, 12, 48, 42]);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

console.log(JSON.stringify({
  outputPath,
  screenshotCount: screenshots.length,
  resourceRows: resourceRows.length,
  sheets: ["资源索引", "设计要求映射", "已有截图清单", "截图拆解字段模板", "下载记录"],
}, null, 2));
