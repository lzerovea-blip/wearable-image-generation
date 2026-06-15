import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const workspace = path.resolve(path.dirname(__filename), "..");
const componentRoot = path.join(workspace, "官方设计规范", "组件资源");
const manifestPath = path.join(componentRoot, "组件资源索引_manifest.json");
const outputPath = path.join(componentRoot, "组件资源索引.xlsx");
const versionDir = path.join(componentRoot, "索引版本");

function colName(index) {
  let n = index;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

function style(sheet, colCount, rowCount) {
  const lastCol = colName(colCount);
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
  body.format.autofitColumns();
  body.format.autofitRows();
}

const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const workbook = Workbook.create();

const index = workbook.worksheets.add("组件索引");
const indexHeader = ["控件名字", "类型", "控件图片本地地址", "版本号", "来源端", "来源截图", "备注"];
const indexRows = manifest.components.map((item) => [
  item.name,
  item.kind,
  item.image_path,
  item.version,
  item.source_end,
  item.source_image,
  `${item.note}；字体口径：鸿蒙字体`,
]);
index.getRange(`A1:G${indexRows.length + 1}`).values = [indexHeader, ...indexRows];
style(index, indexHeader.length, indexRows.length + 1);

const version = workbook.worksheets.add("版本说明");
const versionRows = [
  ["当前版本号", manifest.version],
  ["更新日期", manifest.date],
  ["本次新增组件数", manifest.component_count],
  ["本次处理截图数", manifest.source_count],
  ["App截图数", manifest.app_source_count],
  ["穿戴图片数", manifest.wearable_source_count],
  ["说明", "初始版本：自动裁切运动健康 App 与穿戴截图组件，建立组件索引和版本快照；App 与穿戴界面描述统一使用鸿蒙字体口径。"],
];
version.getRange(`A1:B${versionRows.length}`).values = versionRows;
style(version, 2, versionRows.length);

const changes = workbook.worksheets.add("变更记录");
const changeHeader = ["版本号", "日期", "动作", "新增/修改/删除数量", "说明"];
const changeRows = [[
  manifest.version,
  manifest.date,
  "初始提取",
  `新增 ${manifest.component_count} / 修改 0 / 删除 0`,
  `处理 ${manifest.source_count} 张源图，输出 App 与穿戴截图组件。`,
]];
changes.getRange("A1:E2").values = [changeHeader, ...changeRows];
style(changes, changeHeader.length, 2);

await fs.mkdir(versionDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const versionPath = path.join(versionDir, `组件资源索引_${manifest.version}.xlsx`);
await fs.copyFile(outputPath, versionPath);

console.log(JSON.stringify({
  outputPath,
  versionPath,
  rows: indexRows.length,
  version: manifest.version,
}, null, 2));
