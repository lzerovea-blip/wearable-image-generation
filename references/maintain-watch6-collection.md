# 维护 WATCH 6 与手机合集

在 skill 根目录工作。交付页固定在 `outputs/20261119-WATCH6与手机全功能合集/index.html`。功能源文件、模型和实机素材位于 [projects/watch6-health](../projects/watch6-health/collection.json)。包内的相对路径支持在另一台机器解压后继续开发。

在顶栏勾选要同时展示的入口，至少一项、最多三项。宽屏并排，窄屏上下排列。每个入口独立记录当前页和返回路径，本次打开期间取消勾选后再勾选可接着操作。首次打开显示运动健康「今日」，已设本机开场时显示对应入口。

顶栏「界面目录」跟随最近操作的设备，提供搜索、复制定位和开场设置。选中页面后目录自动关闭。锻炼记录的后续 AI 解读、跨功能的完整解读等补充入口位于目录内的「当前页操作」。

## 从一句修改要求找到页面

用户可以说「手表 → 微体检 → 更多，修改测量提醒的跳转」，也可以直接粘贴网页「复制页面定位」的两行文字。优先使用最后一行的稳定 ID。

```sh
python3 scripts/demo_project.py locate '手表 → 健康洞察 → 睡眠质量评分'
python3 scripts/demo_project.py locate 'watch6-health-check/watch/main'
```

结果含中文路径、正式 ID、兼容别名、分区展示图、原图、证据文件、样式、热区、进入和离开该页的连接。查询有多个结果时返回候选路径和 ID。例如「微体检」可同时匹配手机与手表。先根据用户指明的设备和上级功能缩小范围。合并列表中的热区带有 `sourcePage`，修改对应截图分段。共享手机首页的跨功能热区还需核对目标功能的 `phoneHome`。共用四向表盘面板的源文件位于 `assets/interactive-demo/watch6-face/`。表冠、应用列表顺序和锚点见 `assets/interactive-demo/watch6-launcher/layout.json`。

## 修改字号和样式

[styles.json](../projects/watch6-health/styles.json) 控制网页文字和可编辑设备组件。基础样式在 [style.css](../assets/interactive-demo/style.css)。按 `global → devices → features → pages` 顺序逐属性覆盖，页级键使用查询返回的正式 ID。四层均可设置下表中的角色。

| 角色 | 控制对象 |
| --- | --- |
| directory、caption | 目录结果和分组文字、当前路径、辅助文字 |
| title、body | 设备中的可编辑标题、阅读段落及回放说明 |
| metric、unit | 可编辑数值与单位，各自独立 |
| button、launcherRow | 可编辑操作按钮、腕上应用列表行 |
| content | 可编辑内容的内边距、背景和圆屏文字安全区 |

调整目录字号可修改 `global.directory.font-size`。以下片段仅在手表微体检「更多」页将目录字号设为 16 CSS px。合并到已有的 `pages` 对象后重建。

```json
"pages": {
  "watch6-health-check/watch/live-069": {
    "directory": {"font-size": "16px"}
  }
}
```

字号、字重、字体族、行高、字间距、文字和背景颜色、圆角、内外边距、最小高度和对齐均使用 CSS 属性名。字号用带单位的字符串，字重用 `"500"` 等字符串，行高可用 `"1.45"`。几何尺寸支持 px、em、rem、%、cqw。颜色支持十六进制、transparent 和 currentColor。按钮的 `min-height` 控制可编辑控件的触达高度。实机按钮的热区使用对应截图分区的百分比框 `[左, 上, 宽, 高]`。修改目录或正文样式时，机框和热区使用原有坐标。

三种尺寸分别记录：

- 网页的 `13px` 目录字号、手表 launcher 的 `24px / 500` 来自当前 CSS。硬件层会等比缩放，CSS px 是缩放前的逻辑量。
- 手机的 Title_L 30 Bold、Body_M 14 Regular 等层级来自[手机设计约束](phone-health-app-design-constraints.md)。圆屏左右 26vp、顶部 20vp、底部 6vp 和长页末尾 40vp 来自[穿戴设计指南](wearable-ux-guidelines.md)。应用到授权重绘的页面时依实际屏幕换算并复核。
- 实机截图中的文字已经栅格化。量字高应记录原图文件、像素宽高和字形包围盒。字形高度、字号与字重分别记录。默认以实机像素呈现。HarmonyOS Sans SC Regular 与许可随 HTML 内嵌。

### 只改截图中的一个元素

先定位页面，确认用户要改的元素、范围和展示文字，并保留原始采集、展示图及校验值。若需要模拟数值或重绘元素，先取得该页面的具体授权。在同目录 `model.json` 的 `pageApprovals[页面ID]` 登记实际授权时间 `approvedAt`、用户原话 `userStatement`、修改范围 `description` 和获准的元素 ID 数组 `elements`。生成器同时核验原图证据与元素授权。

在 `feature.json → pages[页面ID] → capture.elements` 为该元素设置稳定 ID、角色、文字、分区和百分比框，可附 `style`。例如下面是字段格式示例，坐标需按选中的原图量取。

```json
[{"id":"score-number","role":"metric","text":"示例","zone":"content",
  "box":[12,32,17,10],"style":{"font-size":"8cqw","font-weight":"700","color":"#ffffff"}}]
```

文字层以截图分区宽度计算 cqw，随设备缩放，原热区继续接收点击。若须遮住旧字，平坦底色可在获准区域设置 `background-color`。复杂纹理须使用对应的实机空底或经批准的局部修订图，另存文件并保留原件。元素的 `style` 优先于角色样式。包中默认页面沿用原有实机图。研究数值、评估结果和授权内容都不因样式调整而自动改变。

## 修改流程、扩展功能

- 在 `feature.json → pages` 修改 `capture.hotspots` 的 `page`，或由 `openFeature` 指向其他功能并保留本地后备页。定时切换使用 `after`。合集中跨功能的显式目录连接位于 `collection.json → navigation.links`。保持页面 ID 稳定，已有腕上旧定位可用 `aliasOf` 接回正式页。
- 列表行使用 `watchLists` 的 `source/crop/location/page`。整屏吸附组使用 `watchScrollGroups` 的 `{"mode":"paged","pages":[…]}`。连续长文组用页面 ID 数组。页内可滚动的「更多」用 `scrollSources` 和 `listBands` 合并同一页面的实机位置。微体检首页与更多分别是 `live-066`、`live-069`。
- `parent` 提供场景初始定位或本机开场的上级。由按钮点入或从目录选择时，访问历史记录实际来源功能、页面与滚动位置。跳转修改后走一次实际入口并右滑返回，再走一次目录直达与本机开场。保存开场的键含合集 ID 和 HTML 路径。
- 新功能先按[联机建模与备份](live-feature-modeling.md)采集，保留操作、设备、时间与原图。在项目中新增独立功能目录，将相对路径加入 `collection.json.features`，接回所属 App 或手表真实入口。尚缺素材的入口可用 `pendingHotspots` 提示。其他 schema 详见[交互网页演示](interactive-demo.md)。

## 重建、交付及恢复

解包端准备 Python 3.10+ 与支持 WebP 的 Pillow。本次字节复现环境为 Python 3.14.6、Pillow 12.3.0、libwebp 1.6.0。使用不同版本的图像编码库时，压缩字节可能变化。双击 HTML 浏览无需安装上述工具。

```sh
python3 scripts/demo_project.py build --out /tmp/watch6-preview
python3 scripts/demo_project.py build
python3 scripts/demo_project.py package
python3 scripts/demo_project.py verify '上一步输出的ZIP路径' --extract-to /tmp/watch6-restored
```

指定新目录可预览，默认重建会原位发布。HTML 内容变化时，旧 HTML 和报告先存入交付目录的 `versions/`。验收后执行 `package`，它会重新构建并比对当前 HTML，再将 skill、模型、证据、设备机框、字体、设计资源和单文件 HTML 一起打包。开发包按内容版本保存在 `outputs/开发包/`。`verify` 检查全部 SHA-256，再启动解压目录中的生成器并比对重建 HTML。可省略 `--extract-to` 进行临时验证。

桌面和模拟触屏验收覆盖：三入口、实际列表点击、分页正反滑、连续正文中停、微体检报告返回列表位置、目录与旧 ID、本机开场恢复；流程或截图修改后补测该页所有已登记入口。逐项注明需要腕上或手机实机复核的部分。

已在本机安装 Playwright、Node.js 与 Chrome 时，执行 `node scripts/check_demo_browser.cjs` 可遍历目录、校验旧 ID 和图片解码，并在桌面与模拟触屏各走一遍微体检报告。可在命令末尾指定其他 HTML 文件。
