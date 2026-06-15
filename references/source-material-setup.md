# 参考素材放置说明

共享本 skill 或在另一台机器安装时，读取本文件。

## 分享原则

本 skill 应尽量可移交，不应要求接收者必须拥有作者机器上的绝对路径。当前项目已把完整运动健康素材放到 `运动健康素材/官方设计规范/`，共享安装时优先读取这个相对路径。

文字规范已经内置在 `references/` 中：

- `references/wearable-ux-guidelines.md`
- `references/phone-health-app-design-constraints.md`

已删除的通用学习笔记不属于共享结构。

对外分享时，除非用户确认拥有再分发权限，不要默认打包第三方官方设计资源、字体、截图、组件裁片或产品机框。推荐做法是随 skill 分发精简规则文本，让接收者在自己的机器上放置有权使用的素材副本。

## 推荐目录结构

接收者可以保持如下结构：

```text
wearable-image-generation/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── design-requirements.md
│   ├── generation-workflows.md
│   ├── source-material-setup.md
│   ├── phone-health-app-design-constraints.md
│   └── wearable-ux-guidelines.md
└── 运动健康素材/
    └── 官方设计规范/
        ├── README.md
        ├── 组件资源/
        ├── 功能截图/
        ├── 华为字体/
        └── 模板资源/
```

当 `运动健康素材/官方设计规范/` 存在时，优先使用它作为共享安装中的素材路径。

## 路径查找顺序

需要查找组件截图、功能截图、字体、模板或官方资源包时，按以下顺序尝试：

1. skill 内素材路径：`运动健康素材/官方设计规范/`
2. 用户在当前对话中提供的新素材路径

如果这些路径都不存在，继续使用 `references/` 中的两份内置设计规范和 `references/design-requirements.md` 的摘要规则。只有当任务必须使用具体截图、组件图片、字体、模板或官方资源包时，才向用户询问素材位置。

## 可随 skill 打包的内容

可以打包：

- `SKILL.md`
- `agents/openai.yaml`
- `references/` 下的精简规则和两份内置设计规范
- 用户自有的示例提示词或生成示例
- 用户自有的图标或预览图

需要确认授权后再打包：

- 官方设计截图
- 组件裁片
- 字体压缩包
- 产品机框
- 下载的官方资源包

避免打包：

- 只在作者机器上有效的绝对路径
- 大量重复截图库
- 已隔离或不确定适用性的素材目录
