from __future__ import annotations

import json
import re
import time
import urllib.request
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
OUT_DIR = WORKSPACE / "官方设计规范" / "下载记录"
CATALOG_PATH = OUT_DIR / "华为设计指南目录树.json"
SUMMARY_PATH = OUT_DIR / "华为设计指南候选约束摘要.json"
API_ROOT = "https://developer.huawei.com/consumer/cn/documentPortal"
REFERER = "https://developer.huawei.com/consumer/cn/doc/design-guides/ux-guidelines-wearable-0000002503475023"


class HtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.tables: list[list[list[str]]] = []
        self.in_table = False
        self.current_table: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self.in_table = True
            self.current_table = []
        elif tag == "tr" and self.in_table:
            self.current_row = []
        elif tag in ("td", "th") and self.in_table:
            self.current_cell = []
        elif tag in ("p", "h1", "h2", "h3", "h4", "li", "br") and not self.in_table:
            self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self.in_table and self.current_cell is not None:
            assert self.current_row is not None
            self.current_row.append(" ".join("".join(self.current_cell).split()))
            self.current_cell = None
        elif tag == "tr" and self.in_table and self.current_row is not None:
            if any(self.current_row):
                self.current_table.append(self.current_row)
            self.current_row = None
        elif tag == "table" and self.in_table:
            self.tables.append(self.current_table)
            self.in_table = False
            self.current_table = []
        elif tag in ("p", "h1", "h2", "h3", "h4", "li") and not self.in_table:
            self.text.append("\n")

    def handle_data(self, data: str) -> None:
        value = unescape(data)
        if self.in_table and self.current_cell is not None:
            self.current_cell.append(value)
        elif not self.in_table:
            self.text.append(value)


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{API_ROOT}/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Referer": REFERER,
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def flatten_catalog(nodes: list[dict], prefix: str = "") -> list[dict]:
    docs: list[dict] = []
    for node in nodes:
        name = node.get("nodeName", "")
        path = f"{prefix}/{name}" if prefix else name
        if node.get("relateDocument"):
            docs.append({"path": path, "relateDocument": node["relateDocument"]})
        docs.extend(flatten_catalog(node.get("children") or [], path))
    return docs


def parse_html(html: str) -> tuple[str, list[list[list[str]]]]:
    parser = HtmlExtractor()
    parser.feed(html)
    text = "\n".join(line.strip() for line in "".join(parser.text).splitlines() if line.strip())
    return text, parser.tables


def table_to_record(table: list[list[str]]) -> dict:
    record: dict[str, str] = {}
    for row in table:
        if len(row) >= 2:
            record[row[0]] = " ".join(row[1:])
    return record


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。；;])\s*", text.replace("\n", " "))
    return [" ".join(p.split()) for p in parts if len(p.strip()) > 8]


def candidate_sentences(text: str) -> list[str]:
    keywords = [
        "应", "需", "建议", "避免", "保持", "确保", "必须", "不要", "不应",
        "vp", "px", "fp", "lpx", "%", "安全", "边距", "导航", "列表", "图标",
        "按钮", "卡片", "文本", "字体", "颜色", "触控", "手势", "焦点", "响应式",
        "手机", "穿戴", "圆形屏", "方形屏", "健康", "运动",
    ]
    out = []
    for sentence in split_sentences(text):
        if any(k in sentence for k in keywords):
            out.append(sentence[:240])
        if len(out) >= 10:
            break
    return out


def is_wearable(path: str, text: str, tables: list[list[list[str]]]) -> bool:
    blob = path + "\n" + text[:3000] + "\n" + json.dumps(tables[:2], ensure_ascii=False)
    return any(k in blob for k in ["智能穿戴", "穿戴", "圆形屏", "方形屏", "ArcSwiper", "ArcList", "手表"])


def is_app(path: str, text: str, tables: list[list[list[str]]]) -> bool:
    app_roots = [
        "通用设计基础",
        "控件",
        "人机交互",
        "系统特性&能力/系统特性/导航条",
        "针对多设备设计/手机",
        "应用 UX 体验标准/通用应用 UX",
        "应用设计最佳实践/便捷生活类",
    ]
    excluded = ["智能穿戴", "智慧屏", "电脑", "折叠屏", "平板", "智能座舱", "汽车类", "游戏类"]
    if any(path.startswith(root) for root in app_roots) and not any(k in path for k in excluded):
        return True
    blob = path + "\n" + text[:3000] + "\n" + json.dumps(tables[:2], ensure_ascii=False)
    return any(k in blob for k in ["手机", "应用图标", "响应式", "导航条", "底部页签", "健康", "运动"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = post_json(
        "getCatalogTree",
        {
            "catalogName": "design-guides",
            "showHide": "1",
            "objectId": "ux-guidelines-wearable-0000002503475023",
            "language": "cn",
        },
    )
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    docs = flatten_catalog(catalog["value"]["catalogTreeList"])

    summary = []
    for index, doc in enumerate(docs, 1):
        response = post_json("getDocumentById", {"objectId": doc["relateDocument"], "language": "cn"})
        value = response.get("value") or {}
        html = ((value.get("content") or {}).get("content")) or ""
        text, tables = parse_html(html)
        records = [table_to_record(t) for t in tables]
        item = {
            "path": doc["path"],
            "relateDocument": doc["relateDocument"],
            "title": value.get("title") or doc["path"].split("/")[-1],
            "url": f"https://developer.huawei.com/consumer/cn/doc/design-guides/{doc['relateDocument']}",
            "wearable_relevant": is_wearable(doc["path"], text, tables),
            "app_relevant": is_app(doc["path"], text, tables),
            "tables": records[:12],
            "candidate_sentences": candidate_sentences(text),
        }
        summary.append(item)
        if index % 25 == 0:
            print(f"fetched {index}/{len(docs)}")
        time.sleep(0.03)

    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "docs": len(summary),
        "wearable": sum(1 for x in summary if x["wearable_relevant"]),
        "app": sum(1 for x in summary if x["app_relevant"]),
        "summary": str(SUMMARY_PATH.relative_to(WORKSPACE)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
