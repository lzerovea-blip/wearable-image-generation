"""Compile scoped, local demo styling and validate optional editable capture text."""
import re

# Use the same selectors as the baseline stylesheet. Emit only configured properties
# so that an unspecified value retains its original responsive and device defaults.
ROLES = {
    "directory": ["#directory-results", "#directory-results summary", "#directory-results button"],
    "title": [".feature-heading h2", ".reading-head h2", ".wrist-flow h2", ".watch-replay h3"],
    "body": [".paragraph p", ".wrist-flow p", ".watch-replay p"],
    "caption": [".reading-head small", ".bound-caption", "#directory-current"],
    "metric": [".flow-metric", ".analysis-number b"],
    "unit": [".analysis-number span"],
    "button": [".action", ".flow-choice", ".directory-actions button"],
    "launcherRow": [".watch-app-row"],
    "content": [".wrist-flow", ".feature-body", ".directory-body"],
}
TEXT_ROLES = {"title", "body", "caption", "metric", "unit", "button"}
LENGTH = r"(?:0|(?:\d+(?:\.\d+)?|\.\d+)(?:px|em|rem|%|cqw))"
FORMATS = {
    **dict.fromkeys(("font-size", "letter-spacing", "border-radius", "min-height"), LENGTH),
    **dict.fromkeys(("padding", "margin"), rf"{LENGTH}(?: {LENGTH}){{0,3}}"),
    **dict.fromkeys(("color", "background-color"), r"(?:#[\da-fA-F]{3}|#[\da-fA-F]{6}|#[\da-fA-F]{8}|transparent|currentColor)"),
    "font-weight": r"(?:[1-9]00|normal|bold)",
    "font-family": r"""[\w "'-]+(?:,[\w "'-]+)*""",
    "line-height": rf"(?:normal|\d+(?:\.\d+)?|{LENGTH})",
    "text-align": r"(?:left|center|right|start|end)",
}


def declarations(values):
    if not isinstance(values, dict):
        raise ValueError("样式属性需要对象")
    result = []
    for prop, value in values.items():
        if prop not in FORMATS or not isinstance(value, str) or not re.fullmatch(FORMATS[prop], value):
            raise ValueError(f"未知样式或无效单位 {prop}={value!r}")
        result.append(f"{prop}:{value}")
    return ";".join(result)


def compile_styles(theme, features, directory):
    if not isinstance(theme, dict) or set(theme) - {"global", "devices", "features", "pages"}:
        raise ValueError("样式范围须为 global、devices、features 或 pages")
    valid = {"devices": {"phone", "watch"}, "features": {f["id"] for f in features},
             "pages": {row["key"] for row in directory["pages"]}}
    scopes = [("", theme.get("global", {}))]
    for kind, attr in (("devices", "device"), ("features", "feature"), ("pages", "page")):
        for key, roles in theme.get(kind, {}).items():
            if key not in valid[kind]:
                raise ValueError(f"样式定位无效 {kind}/{key}")
            scopes.append((f' :where([data-theme-{attr}="{key}"])', roles))
    rules = []
    for scope, roles in scopes:
        for role, styles in roles.items():
            if role not in ROLES:
                raise ValueError(f"未知样式角色 {role}")
            selectors = list(ROLES[role])
            if role in TEXT_ROLES:
                selectors.append(f'.editable-text[data-role="{role}"]')
            # A fixed extra specificity wins over the baseline device/class rules.
            prefix = ":root :is(#main, .workspace, #instructions)" + scope + " "
            rules.append(",\n".join(prefix + s for s in selectors) + "{" + declarations(styles) + "}")
    return "\n".join(rules)


def validate_elements(capture):
    ids = set()
    for item in capture.get("elements", []):
        key = item["id"]
        box = item["box"]
        if (not re.fullmatch("[a-z][a-z0-9-]*", key) or key in ids
                or item.get("role") not in TEXT_ROLES or item.get("zone") not in ("header", "content", "footer")
                or item["zone"] not in capture or not isinstance(item.get("text"), str)
                or len(box) != 4 or not all(type(v) in (int, float) and 0 <= v <= 100 for v in box)
                or not 0 < box[2] <= 100-box[0] or not 0 < box[3] <= 100-box[1]):
            raise ValueError(f"可编辑文字层标识、分区或位置无效 {key}")
        ids.add(key)
        declarations(item.get("style", {}))
