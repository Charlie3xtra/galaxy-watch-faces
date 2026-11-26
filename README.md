# Galaxy Watch 表盘

## 彩虹线条 Pride Threads

| 亮屏 | 息屏 |
| :---: | :---: |
| <a href="PrideThreads/screenshots/active.png"><img src="PrideThreads/screenshots/active.png" width="220" alt="彩虹线条 Pride Threads · 亮屏"></a> | <a href="PrideThreads/screenshots/ambient.png"><img src="PrideThreads/screenshots/ambient.png" width="220" alt="彩虹线条 Pride Threads · 息屏"></a> |

16 根彩线的宽度组成两行时间，点按一根线会触发局部振动。三星编辑器提供浅色和深色背景，表盘名称与背景名称跟随系统语言。支持 Wear OS 6 的 WFF 4 表盘选择器。

[下载彩虹线条 1.1](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-threads-v1.1/PrideThreads-1.1.apk) · [浅色编辑页](PrideThreads/watch-editor.png) · [深色编辑页](PrideThreads/watch-editor-dark.png)

24S132 的 NTKLilypadFaceBundle 提供数字图集、数字起止位置、灰度到线宽的查找表，以及两组各 16 个 RGBA 值。生成器复用单色遮罩，并按每根线的位置着色。圆屏布局参照官方 10:09 图调整。点按和亮屏振动使用 WFF 的 TAP 与 ON_VISIBLE 播放预绘波形。原版的噪声、跨线物理传播、腕部运动与数码表冠连续输入尚未复现。息屏使用黑底、窄线和静止数字。

## 彩虹光辉 Pride Radiance

| 亮屏（1.10） | 息屏（1.4） |
| :---: | :---: |
| <a href="PrideRadiance/screenshots/active.png"><img src="PrideRadiance/screenshots/active.png" width="220" alt="彩虹光辉 Pride Radiance · 亮屏（1.10）"></a> | <a href="PrideRadiance/ambient-1.4.png"><img src="PrideRadiance/ambient-1.4.png" width="220" alt="彩虹光辉 Pride Radiance · 息屏（1.4）"></a> |

适用于支持 WFF 4 的 Wear OS 6 或更新版本。安装后在手表的表盘选择器中选用；在系统编辑页可选 I–V 五组配色。名称和配色辅助说明使用固件的本地化资源。

数字网格、纹理坐标和五组配色来自 watchOS 24S132 固件。五组配色的光流均按各自的色表和混合参数绘制，在 32 秒内经过 32 个关键位置，Wear OS 在相邻位置间按 30 帧/秒的目标插值。Apple 的 getDesiredFPSForDevice: 请求 30 或 60 帧/秒。圆屏版的排版、光流初始相位、循环、插值与光晕滤波经过适配。

息屏按各配色的 tritium 设置生成，使用专用颜色、色段长度、字形加宽和无外发光的静态绘制。相位与亮度映射仍是移植值，尚无同机同刻的 Apple 实拍校准。

[下载彩虹光辉 1.10](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-radiance-v1.10/PrideRadiance-1.10.apk) · [紫色光晕修正前后对照](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-radiance-v1.7/purple-compare-1.7.png) · [配色 II–V 动态对照](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-radiance-v1.5/colorways-II-V-1.5.mp4) · [Galaxy Watch 息屏实拍截图](PrideRadiance/ambient-1.4.png)

1.10 使用一秒线性渐变在完整画面之间过渡。保留系统双色圆点、五组配色和每轮 32 个关键位置。亮屏光场纹理使用预乘透明度缩放，WFF 内存检查通过。

## 艺术家 Artist

| 亮屏 | 息屏 |
| :---: | :---: |
| <a href="Artist/screenshots/active.png"><img src="Artist/screenshots/active.png" width="220" alt="艺术家 Artist · 亮屏"></a> | <a href="Artist/screenshots/ambient.png"><img src="Artist/screenshots/ambient.png" width="220" alt="艺术家 Artist · 息屏"></a> |

在支持 Watch Face Push 的 Wear OS 6 或更新版本手表上安装 APK，并打开一次。首次替换当前表盘时，按 Wear OS 提示确认。首次使用从安装器点「打开」。艺术家仅在表盘选择器中展示，应用抽屉中没有图标。点按可换脸，距离上次换脸超过一小时后再次亮屏也会换脸。息屏显示同一张脸的轮廓。

[下载艺术家 4.5](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/artist-v4.5/Artist-4.5.apk) · [固件素材与索引](https://github.com/Charlie3xtra/watchos-face-assets)

![艺术家](Artist/selector.png)

Artist 目录含生成器、WFF 场景和本地 PowerShell 构建脚本。重新构建需要 Android SDK、Wear SDK、wearable complications 库、Push 验证工具及自己的签名密钥。应用通过前台服务监听亮屏，系统管理该服务的通知。



表盘与安装入口的名称采用固件 24S132 中 44 项语言与地区资源的官方译名。启用提示、通知和无障碍点按说明跟随系统语言。艺术家使用固件的十个手绘数字字形。

## X-Large · 大文字

| 纯时间 | 电池组件 |
| :---: | :---: |
| <a href="XLarge/screenshots/active.png"><img src="XLarge/screenshots/active.png" width="220" alt="X-Large · 大文字 · 纯时间"></a> | <a href="XLarge/screenshots/battery.png"><img src="XLarge/screenshots/battery.png" width="220" alt="X-Large · 大文字 · 电池组件"></a> |

[下载大文字 1.3](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/tag/xlarge-1.3)。默认两行纯时间。选择一个组件后，时间连同冒号移到顶部一行，组件占据下方的大圆区。圆屏比例参考 [Apple Watch 使用手册第 148 页](https://help.apple.com/pdf/watch/9/en_US/apple-watch-user-guide-watchos9.pdf#page=148)。

The default lavender and three numeral silhouettes were sampled from the Apple gallery image. The other digits use the closest measured SF Compact Rounded weight from build 24S132. The 26 additional solid colors use firmware catalog components. Round-screen spacing and ambient dimming are adaptations. Apple provider graphics, seasonal palettes, color sliders and alternate numeral scripts are outside this release. Build the included Android resources directly with XLarge/build.ps1. Regeneration additionally needs Pillow, NumPy, and the extracted 24S132 directory structure referenced in generate.py.

## 双行数字 · Numerals Duo

| 彩虹亮屏 | 彩虹息屏 |
| :---: | :---: |
| <a href="NumeralsDuo/screenshots/active.png"><img src="NumeralsDuo/screenshots/active.png" width="220" alt="双行数字 · Numerals Duo · 彩虹亮屏"></a> | <a href="NumeralsDuo/screenshots/ambient.png"><img src="NumeralsDuo/screenshots/ambient.png" width="220" alt="双行数字 · Numerals Duo · 彩虹息屏"></a> |

[下载 1.1](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/tag/numerals-duo-1.1)。使用 24S132 固件表盘程序内嵌的 Tokyo 和 Tokyo Outline 字形。原生编辑器支持三套数字、实心 / 混合 / 空心样式与 62 种配色。另有彩虹选项。新版默认使用从上到下贯穿两行的六色渐变，原官方预览的紫色组合仍可选。渐变取自 24S132 的 NTKPrideColorUtils，息屏叠加 Tokyo Outline 并降低填充强度。直接运行 NumeralsDuo/build.ps1 可用现成资源构建。

## Nike 地球 · Nike Globe

| 亮屏 | 息屏 |
| :---: | :---: |
| <a href="NikeGlobe/screenshots/active.png"><img src="NikeGlobe/screenshots/active.png" width="220" alt="Nike 地球 · Nike Globe · 亮屏"></a> | <a href="NikeGlobe/screenshots/ambient.png"><img src="NikeGlobe/screenshots/ambient.png" width="220" alt="Nike 地球 · Nike Globe · 息屏"></a> |

[下载 1.1](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/tag/nike-globe-1.1)。WFF 4 单 APK。亮屏跟随当前秒数显示固件中的 Globe_00 至 Globe_59，息屏切换到独立 Globe 网格。上下两行使用内嵌 Vivaldi 字体的小时和分钟连字。提供 23 种固件配色与一个参考官方预览图制作的黑底珊瑚色方案。1.1 移除四角组件，网格、时间和标志整体放大 20%。中央标志为装饰。APK 可直接从 NikeGlobe/build.ps1 构建，重新生成资源需要 Pillow、fontTools 和 24S132 提取目录。
