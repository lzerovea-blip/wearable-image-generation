# 交互网页演示

现有 WATCH 6 三入口合集的源文件、逐页定位、样式覆盖和可迁移备份见[合集开发与离线恢复](maintain-watch6-collection.md)。


当用户需要可点击、可滑动的华为穿戴 / 运动健康 App HTML 时，读取本文件及目标设备的设计约束。先确定要演示的功能、场景起点、关键画面，以及新增入口要接入的原有页面。每页使用目标设备的实机图；展示参考图或复原页前需取得用户对该页的明确授权。每个场景可以使用手表、手机或双端。

新增功能先执行 [联机建模与备份](live-feature-modeling.md)，将实机操作与功能模型对应。已建模功能可直接再生成。

按标签建立 App 页面基线时，给模块和页面保留跨版稳定的 ID。场景可用 `phonePageIndex` 列出本模块已采到的页面，网页会在侧栏提供直接跳转。一次启动另一 App 的真实操作可在热点中记录 `openFeature` 的 `id` 与 `page`，并保留同一热点的本地采集目标；合集可沿此入口跨功能并返回。对限定区域的横滑，用 `swipeAreas` 记录设备视口的百分比边界。随长页滚动的分类栏可在 `swipeAreaZones` 中为相同方向指定 `content`，此时边界使用整张内容截图的百分比。每版分别保存页面清单与截图证据，并按联机建模文档生成离线版本比较页。

## 生成

在 skill 根目录传入已建模的功能或合集。身体状态准备度示例中的原型界面也需要逐页授权。

```sh
python3 scripts/generate_interactive_demo.py --feature path/to/first/feature.json --feature path/to/second/feature.json --out path/to/new-demo
```

每个文件定义一个顶部可选功能。生成后会输出本地版本备份路径；尚在补采阶段时使用 `--draft`。生成目录包含独立可打开的 `index.html` 和 `generation-report.md`。默认使用 `outputs/<时间>-interactive-demo-<功能 ID>/`。HTML 已嵌入设备、字体、截图和脚本，展示端可直接使用桌面或触屏浏览器。

同一 App 的多个研究项目各用一个功能文件。检测、预测、问卷等操作放在项目自己的场景列表里。合集文件指定显示顺序，例如 `{"id":"research","name":"创新研究","features":["血糖健康研究/feature.json","心脏健康研究/feature.json"]}`。跨 App 合集可在同一列表中引用各 App 的功能文件，选择器会按模型中记录的 `devices.phone.app` 分组。将合集路径传给 `--feature` 即可生成。备份解压后可传入 `features/collection.json` 重建。

`initialView` 指定打开功能时显示的可操作界面，包含与一张关键图对应的 `scene`、`device` 和 `page`。若多个功能使用同一实机首页截图和布局，给它们设置相同的 `sharedPhoneHome` 标识，各自在 `phoneHome` 上定义自己负责的卡片或标签入口。合集自动汇总这些入口，打开卡片时同时选择对应功能。

## 合集入口与逐页维护

在合集 JSON 的 `navigation.groups` 中按显示顺序登记各入口的 `id`、`label` 和 `home`，用 `navigation.default` 指定首次开场入口。`home` 引用模型的 `feature`、`device` 和 `page`。与入口模型相同 App 名称或手表型号的功能自动归入该入口。各功能继续独立维护。新增功能时先完成联机采集和逐页来源登记，将其路径追加到 `features`，在已有界面的实机热点或合集连接中登记入口。

每个实机页面自动进入可搜索的界面目录。点击「复制页面定位」可获取中文路径和 `功能ID/设备/页面ID`。用功能 ID 找到对应的 `feature.json`，按页面 ID 修改截图、热区或返回路径，同步更新 `model.json` 的证据。页面改名或替换素材时沿用原 ID。共用表盘与列表按页面角色和实机图内容去重。表盘四向系统页由模板的 `watch6-face/navigation.json` 和 `evidence.json` 管理。各模型共享的应用列表需要一并核对截图和入口。不同日期采集的详细流程可在 `navigation.links` 中登记 `from`、`to` 和 `label`，连接位于顶栏「界面目录」的「当前页操作」中。

「设为本机开场」仅保存到当前浏览器和当前 HTML 路径。恢复默认、移动文件或换浏览器后从合集默认页开始。交付前在桌面和触屏验证实际入口、返回位置、复制定位及本机开场，归档后从备份中的 `features/collection.json` 离线重建。

## 配置功能

复制 [准备度配置](../assets/interactive-demo/examples/readiness/feature.json) 所在的示例目录后编辑。图标和页面图片采用相对于配置文件的本地 PNG、JPEG 或 WebP 路径。功能内容使用纯文本。

| 字段 | 用法 |
| --- | --- |
| `id`、`name`、`icon` | 小写英文功能 ID，顶部显示名称，可选圆形入口图标。健康洞察可引用固定图标 `@insight-icon`。 |
| `entries` | 选择需要接入的位置。手表有 `launcher`、`minus`、`cards`，手机有 `summary`。每个入口填写 `label`、`page`，卡片可补 `detail`、`value`、`note`。 |
| `pages` | 自定义页面按 ID 索引，填写 `device`（watch、phone 或 both）、`title` 和 `parent`。双端返回路径可分别指定。普通页面可设 `subtitle`、`sections`（含 title 和 text）与 `action`（含 label 和 page）。 |
| 参考界面与反馈 | `cover` 指定首屏截图。`coverAction` 含按钮名称 label、目标 page 和百分比热区 box（左、上、宽、高）。截图下的正文可滚动。生成中等过渡页面可配置 `after` 的目标 page 和等待毫秒数 ms。 |
| `records` | 每条记录含 title、date 和 sections。通过页面的 `record` 引用，手表和手机会使用各自布局展示同一正文。 |
| `scenes` | 每项含 id、title、操作提示 hint、起点 start 和数组 keys。起点示例为 `{"watch":"@face","phone":"@home"}`。每张关键图写成 `["watch","insight","健康洞察"]`。总览按此顺序绘制缩略图，点击定位到同一步。 |
| `references` | 可选字符串列表。写入报告，说明参考截图、推定布局、模拟数据和跨端扩展。 |

手表固定页面使用 `@face`、`@launcher`、`@minus`、`@cards`。手机使用 `@home`、`@summary`。自定义页面 ID 以小写英文字母开头，可含小写字母、数字和连接号。机框、表盘、滑动方向、系统页面、列表行和卡片容器由模板管理。设计其他功能时在配置内添加页面和入口。

## 素材与验收

WATCH 6 的四向表盘导航由 `assets/interactive-demo/watch6-face/navigation.json` 共用。上滑进入消息通知，下滑进入控制中心，左滑进入手表卡片，右滑进入小艺建议。继续滑动可翻看同方向的后续页面。卡片上的功能入口按当前合集中的功能 ID 接通，右滑应返回进入前的卡片。新增腕上功能时复用这套导航。修改系统界面时，联机记录去程、逆向返回和页面节点，更新同目录的截图与 `evidence.json`，并随演示备份。

WATCH 6 联机模型使用 `watchProfile: "watch6"`。`watchScreens` 将 `@face` 和 `@launcher` 分别指向实机表盘与列表截图页。表冠从表盘打开列表，从应用回到表盘。在列表截图的 `capture.hotspots` 中登记本功能入口，`capture.launcherRows` 可列出同屏其他应用的实机名称和百分比热区。生成合集时自动接入已建模的同机型应用。用 `capture.swipe.up` 和 `down` 关联实际观察到的上下滑动结果，保留可逆的翻页路径。仅取得同步或启动画面时，在模型的操作记录中标明待补采步骤。

多个功能可共用同一组实机列表截图，在每个功能的 `entries.launcher` 中写入真实应用名称和目标页，页面的 `capture.launcherRows` 为对应应用提供点击区域。将多个列表位置用 `capture.swipe` 连接，即可从表冠进入并滑动到其他功能。参考截图或复原页面用 `provenance` 写明来源，显示在设备外侧。复原页的 `watchFlow` 支持操作按钮、日历和示例状态。按钮用 `page` 定义去向，可通过 `related` 进入另一个已建模功能。浏览器内分别验证触屏滑动、鼠标拖动、滚轮、页内操作与跨端返回。

三入口合集中的 WATCH 6 使用连续滚动的应用列表。`assets/interactive-demo/watch6-launcher/layout.json` 记录应用顺序、实机图标裁片及其来源，`anchors` 把已有列表页面 ID 对应到居中的应用。新增应用沿用功能 ID 和 `watchReplayEntry` 或 `entries.launcher.page`，补入实机素材和校验值即可固定列表图标与顺序。点开应用时保存列表实际滚动位置，右滑退出后在原位置继续浏览。应用内的研究项目和详情按钮用 `capture.hotspots` 直接接到对应页。

腕上实机截图可用 `capture.replay` 在表框旁显示操作。该字段包括 `description`、`actions` 和 `pending`。每条操作填写 `label` 与本功能目标 `page`，待采集步骤填写说明。上下翻页复用 `capture.swipe`。配置 `watchReplayEntry` 后，共用应用列表会提供表框外的应用选择，返回时恢复进入前的列表位置。

腕上应用内需要连续滚动时，可参考华为创新研究的模型。`watchLists` 中每个列表包含 `label`、`rows` 和 `anchors`。每一行用 `source` 引用本功能的实机截图页，`crop` 按左、上、宽、高百分比截取原始按钮，`page` 指定点击去向。缺少目标画面时写 `pending: true`。行的 `location` 关联目录位置，`anchors` 将原页面 ID 映射到从零开始的居中行号。对于项目内通过上下滑动连续阅读的实机画面，在 `watchScrollGroups` 按阅读顺序列出已有双向滑动路径的页面 ID。确认、测量和问卷操作仍按原有按钮进入。

整屏翻页的分组在 `watchScrollGroups` 中写成 `{"mode":"paged","pages":[…]}`。每张实机截图独占一屏，松手后吸附，目录随停稳的页面更新。健康洞察将九张主卡片放在同一分页组，AI 解读和说明各自使用普通数组以连续阅读。

同一页有多次取图时，在重复页填写 `aliasOf` 指向正式页面，并将场景、按钮和滑动路径接回正式页面。旧定位仍可搜索及用作本机开场。对于「更多」这类可滚动的整屏，在正式页的 `capture.scrollSources` 中按顺序列出本页与下方位置的截图 ID，沿用各自的 `listBands` 保留不重复的条目及热区。一次手势在卡片内滚到边缘，松手后再滑才切换整页。

锻炼模式行可设置 `secondary`，填写独立的 `label` 和可选的设置页 `page`，对应实机右侧省略号。`naturalRows: true` 按照片中每行的原始比例显示。对于同屏记录、设置、选项或统计列表，在 `capture.listBands` 中按顺序列出各条目占截图高度的起止百分比。连续采集位置间有重复行时只取一次，点击区的中心须位于保留范围内。验收时用短拖停在两行之间，点入二级界面后右滑，核对返回前后的偏移。

生成器识别腕上方形截图的白色或透明外角，用原圆屏边缘的背景色延展网页展示图的外角，原始采集文件独立保留。检查深色和浅色界面的滑动中间帧，尤其是「活动记录 → 今日详情 → 运动建议」。机框固定，验证时把两张画面的接缝拖到圆屏中央。

手机和手表都支持在设备屏幕内右滑返回。触屏和鼠标使用从左向右的拖动，触控板使用双指横滑。点入详情后返回应恢复进入前的菜单及滚动位置，跨应用和跨设备时也应恢复原入口。分页引导优先执行配置的 `capture.swipe.right`。验证触控板时，一次横滑连同惯性应只触发一次返回。

固定机框取自素材库 WATCH 5 和 Pura 70 Pro 的透明 PNG，Launcher 采用列表式实机布局，手机首页从组件库同源的 live_health_home.png 提取完整三环、快捷入口与运动记录内容区，配以 HarmonyOS 系统壳层，健康摘要分析卡片取自手机组件库。固定表盘为可操作的模拟指针表盘。负一屏参考实机卡片，超级卡片和手机跨端入口属于原型补全。内置示例使用 11 月 19 日的健康洞察及 AI 解读截图，依据三张结果截图整理出可滚动正文。截图只用于已有界面，浏览器绘制实际按钮、滚动内容与运行状态。

在浏览器中从表盘按表冠，经列表进入功能；从表盘分别向右、向左滑进入负一屏和超级卡片；上下滑动长页并返回；从手机健康首页进入同一结果。检查总览的每张缩略图、顶部功能切换、场景重置，以及窄窗口和离线打开。将本次实际检查的结果追加到生成报告中。

