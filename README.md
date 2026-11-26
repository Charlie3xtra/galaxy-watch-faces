# Galaxy Watch 表盘

## 彩虹光辉 Pride Radiance

适用于支持 WFF 4 的 Wear OS 6 或更新版本。安装后在手表的表盘选择器中选用；在系统编辑页可选 I–V 五组配色。名称和配色辅助说明使用固件的本地化资源。

十个数字的三角网格、纹理坐标、五组颜色及息屏参数来自 watchOS 24S132 的 NTKPlumeriaFaceBundle.bundle。光束以六个烘焙状态和 WFF 透明度动画重现。高光、光晕、运动速度和圆屏布局是移植近似；未复现原生 Metal 渲染或运动传感器联动。

[下载彩虹光辉 1.0](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/pride-radiance-v1.0/PrideRadiance-1.0.apk) · [亮屏实机截图](PrideRadiance/active.png) · [息屏实机截图](PrideRadiance/ambient.png)

## 艺术家 Artist

在支持 Watch Face Push 的 Wear OS 6 或更新版本手表上安装 APK，并打开一次。首次替换当前表盘时，按 Wear OS 提示确认。首次使用从安装器点「打开」。艺术家仅在表盘选择器中展示，应用抽屉中没有图标。点按可换脸，距离上次换脸超过一小时后再次亮屏也会换脸。息屏显示同一张脸的轮廓。

[下载艺术家 4.5](https://github.com/Charlie3xtra/galaxy-watch-faces/releases/download/artist-v4.5/Artist-4.5.apk) · [固件素材与索引](https://github.com/Charlie3xtra/watchos-face-assets)

![艺术家](Artist/selector.png)

Artist 目录含生成器、WFF 场景和本地 PowerShell 构建脚本。重新构建需要 Android SDK、Wear SDK、wearable complications 库、Push 验证工具及自己的签名密钥。应用通过前台服务监听亮屏，系统管理该服务的通知。



表盘与安装入口的名称采用固件 24S132 中 44 项语言与地区资源的官方译名。启用提示、通知和无障碍点按说明跟随系统语言。艺术家使用固件的十个手绘数字字形。
