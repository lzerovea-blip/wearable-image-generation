# 新增功能的联机建模与备份

每次新增可操作功能，先在对应实机走一遍，再生成交付版本。已有模型改版时对照变更路径补采。用户可操作手表并同步录屏，或由操作者通过已授权的设备连接采集。先确认设备型号、系统版本和手机 App 版本，分别写实际读数与未知项。

## 采集顺序

1. 确认目标设备。Android 可用 `adb devices -l`，HarmonyOS 可用 `hdc list targets -v`。多设备时按目标选择；仅配对到手机的手表需要通过可见的投屏或用户实机操作观察。
2. 从实际入口依次操作，记录「起点 → 动作 → 结果」。覆盖这个功能的入口、各分支、等待与结果、上下滚动、退出和返回。跨端功能在另一台设备单独核对入口与对应记录。现场无法触发的状态标为待补采。
3. 只保存本功能画面到私有工作目录 `evidence/`。设备已进入目标页面时，可用 `adb -s <目标> exec-out screencap -p > <本地截图>.png`。使用 HDC 时先确认设备支持的截图命令，再用 `hdc -t <目标> file recv` 取回本次截图。手表交由用户操作时也可保存一段实际操作录像，注明时间段。HTML 展示使用经过裁切、去身份信息的素材。备份可包含明确选入的原始证据。
4. 每个功能一个工作目录，放 `feature.json`、`model.json` 和引用的素材。先列出要验证的路径，再逐项把状态从 `pending` 更新到 `live`。旧截图可以证明画面外观，操作路径尚待本次验证时用 `reference`。实机复核场景顺序、内容和返回行为后将 `reviewed` 设为 true。

```json
{
  "feature": "health-insight",
  "devices": {"watch": {"model": "HUAWEI WATCH 5", "os": "待采集"}},
  "reviewed": false,
  "steps": [
    {"scene": "enter", "device": "watch", "from": "表盘", "action": "按表冠", "to": "应用列表", "source": "pending", "files": []}
  ]
}
```

`feature` 和 `scene` 对应功能和场景 ID。每条 live 记录还须有实际观测时间 `observedAt` 及相对路径 `files`，可增加备注说明视频时间码。记录中有待采项，或某场景关键图涉及的端尚未观测时，使用草稿交付。

## 逐页来源与授权

在 model.json 的 frameEvidence 中为每个页面登记 sources（实机原图或录像的相对路径与 SHA-256）和 renders（实际展示图片的相对路径与 SHA-256）。来源文件也纳入当次 live 步骤。允许对原图进行裁切、长页拼接、无损转码和隐私遮挡；替换文案、绘制曲线、模拟读数或动画均属于替代内容，需单独授权。

对于具体同意展示的替代页面，在同一模型的 pageApprovals 中按页面 ID 保存 approvedAt、userStatement 和 description，注明用户同意的内容和范围。设备调试授权、应用知情同意和流程操作授权只用于各自的事项。缺图时可以记录 pending 步骤和 pendingHotspots，保持当前设备画面，并在设备外提示。复核截图的文字、布局和前台页面；调试回传首页、启动图或同一帧时，只登记实际能看到的状态。

WATCH 6 网页展示图去除截图中的斜向设备编号。优先采用同页、同一滚动位置的无水印 HDC 帧，核对标题、正文和按钮位置。配对手机同步的腕上截屏可能以 `WatchScreenshot_` 或 `WatchApScreenshot_` 开头。需要处理带编号的截图时，保留原图，使用同机配对画面核对水印范围，只改展示图，并在逐页来源中记录处理方式。验收时从最终 HTML 打开该页，放大核对正文及右下角。

## 使用实机长页

在 Mate 50 录制手机界面时，可将功能的 `phoneProfile` 设为 `mate50`，并用 `phoneHome` 指向已采集的入口页。独立 App 可以用 `phoneHomeLabel` 指定返回首页按钮的名称，如「创新研究首页」。自定义页面的 `capture` 可包含固定的 `header`、可滚动的 `content` 和固定的 `footer`。内容区必填，各区引用功能目录内的图片。连续截图先按重叠内容对齐，再裁出共用顶栏和底栏。仅一张截图时用 content。

`capture.hotspots` 中每个热点包含 `zone`、`label`、`page` 和 `box`。box 为该区内的百分比左、上、宽、高，page 可指向页面或 `@back`。同页切换周期、页签、展开状态时可用 `mode: "replace"` 保持系统返回路径。在同一长页切换图表周期时，加上 `keepScroll: true` 可以保留滚动位置。对于实机横滑页面，`capture.swipe` 的 `left` 和 `right` 可分别指定向左、向右滑动后的页面。浏览器内核对各热点、滚动和横滑方向，再记录本次覆盖的操作。

确认弹窗需要同时关闭并更新下层页面时，确认按钮可用 `mode: "dismiss"`，取消按钮使用 `@back`。若实机在启动评估或保存设置后改变了再次进入的页面，可在按钮上配置 `rememberRoutes`。例如 `{"g-main":"g-progress"}` 使本次演示中再次打开项目进入评估进度，`{"g-main":"g-main"}` 恢复原入口。主动选择或重置场景时从该场景的起始状态回放。

## 生成和恢复

生成手机演示前，在原始截图上量出状态栏中应用通知图标的范围，并从展示用图片中清理。时间、连接状态、电量和 App 标题栏按实机保留。若顶部背景平整，可用 `python3 scripts/clean_capture_notifications.py 功能目录/feature.json --screen-width 原始像素宽 --box 左 上 右 下`。工具按截图宽度换算区域，只处理顶栏或包含状态栏的整屏展示图。处理后核对总览缩略图及场景画面，再生成 HTML。

正常生成命令会校验联机记录，并将交付与模型一起备份。设备暂缺、分支未走通或用户明确要求早期原型时，在原命令加 `--draft` 保存当前进度。草稿使用相同的逐页来源校验。

```sh
python3 scripts/generate_interactive_demo.py --feature 工作目录/feature.json
python3 scripts/generate_interactive_demo.py --feature 工作目录/feature.json --draft
python3 scripts/generate_interactive_demo.py --feature 工作目录/feature.json --archive-existing 已验收的交付目录
```

默认备份根目录为 `~/Documents/穿戴功能模型备份/`，可用 `--archive-dir` 指定其他本地磁盘。备份按内容版本保留，输入与交付相同会复用同一版本。浏览器验收完成并补写报告后，用 `--archive-existing` 归档最终报告；草稿仍加 `--draft`。如果备份写入失败，交付目录保留，可用同一条归档命令重试。

解压 ZIP 后直接打开 `demo/index.html`。要继续编辑，使用 `features/<功能 ID>/` 中的配置和证据。包中的 `skill/` 含当时的生成脚本、设备模板和所用字体，从解压目录运行 `python3 skill/scripts/generate_interactive_demo.py --feature features/<功能 ID>/feature.json` 可重建相同网页。多功能演示按原顺序重复传入 `--feature`。快照中的 `manifest.json` 记录每项功能的建模状态和每个文件的 SHA-256，生成器落盘前逐项复核。


## 页面基线和跨版本比较

手机在目标页面停稳后，可使用 `python3 scripts/record_phone_page.py today-sleep --out 新版采集`。工具通过已连接的 ADB 手机保存原始 PNG、控件树、App 版本和校验值，每次采集写入独立目录。多台手机连接时用 `--serial` 指定设备，华为创新研究使用 `--package com.huawei.study.hiresearch`。原始记录只存放在本地，发布时使用处理过身份信息的展示素材，把相应截图填入模型的逐页证据清单。

同一产品按 App 版本、采集时间新建目录。沿用页面和控件的功能标识，记录实际的 App 版本号、系统、连接设备、纳入的标签和排除项。页面重命名时保留原标识。每个页面在 inventory.json 的 pages 中记录 module、controls 和 pending，scope 记录比较范围，capturedAt 记录采集时间。控件可用 baselineId 稳定标识。对照来源目录保留原始证据，在交付用的界面中遮盖身份信息。对可恢复设置的实机采集应记录原值和复原读数，特别核对联动开关。

```sh
python3 scripts/health_ui_baseline.py snapshot 功能目录/feature.json --out 首版/baseline.json
python3 scripts/health_ui_baseline.py viewer 首版/baseline.json --out 首版/版本比较.html
python3 scripts/health_ui_baseline.py compare 首版/baseline.json 新版/baseline.json --out 差异报告.html
```

双击版本比较网页并选择新版 baseline.json，可离线核对页面、模块、操作目标、入口位置、滑动路径和截图变化。命令行 compare 也可输出 JSON。线上内容、历史记录和设备状态会影响截图，画面变化需结合控件与实机复核。未采到的页面单列。两版的采集范围须一致。
