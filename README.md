# Galaxy Watch 表盘

## 彩虹光辉 Pride Radiance

适用于支持 WFF 4 的 Wear OS 6 或更新版本。安装后在手表的表盘选择器中选用；在系统编辑页可选 I–V 五组配色。名称和配色辅助说明使用固件的本地化资源。

数字网格、纹理坐标和五组配色来自 watchOS 24S132 固件。五组配色的光流均按各自的色表和混合参数绘制，在 16 秒内经过 32 个关键位置，Wear OS 在相邻位置间按 30 帧/秒的目标插值。Apple 的 getDesiredFPSForDevice: 请求 30 或 60 帧/秒。圆屏版的排版、光流初始相位、循环、插值与光晕滤波经过适配。

息屏按各配色的 tritium 设置生成，使用专用颜色、色段长度、字形加宽和无外发光的静态绘制。相位与亮度映射仍是移植值，尚无同机同刻的 Apple 实拍校准。

[下载彩虹光辉 1.5](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-radiance-v1.5/PrideRadiance-1.5.apk) · [配色 II–V 动态对照](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-radiance-v1.5/colorways-II-V-1.5.mp4) · [Galaxy Watch 息屏实拍截图](PrideRadiance/ambient-1.4.png)

## 艺术家 Artist

在支持 Watch Face Push 的 Wear OS 6 或更新版本手表上安装 APK，并打开一次。首次替换当前表盘时，按 Wear OS 提示确认。首次使用从安装器点「打开」。艺术家仅在表盘选择器中展示，应用抽屉中没有图标。点按可换脸，距离上次换脸超过一小时后再次亮屏也会换脸。息屏显示同一张脸的轮廓。

[下载艺术家 4.5](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/artist-v4.5/Artist-4.5.apk) · [固件素材与索引](https://github.com/Charlie3xtra/watchos-face-assets)

![艺术家](Artist/selector.png)

Artist 目录含生成器、WFF 场景和本地 PowerShell 构建脚本。重新构建需要 Android SDK、Wear SDK、wearable complications 库、Push 验证工具及自己的签名密钥。应用通过前台服务监听亮屏，系统管理该服务的通知。



表盘与安装入口的名称采用固件 24S132 中 44 项语言与地区资源的官方译名。启用提示、通知和无障碍点按说明跟随系统语言。艺术家使用固件的十个手绘数字字形。
