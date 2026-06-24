# 发货看板桌面版

## 打包

在项目目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop.ps1
```

输出目录：

```text
release\fa-huo-dashboard\
```

## 使用

把整个 `release\fa-huo-dashboard\` 文件夹拷贝到老板或其他电脑，双击：

```text
fa-huo-dashboard.exe
```

## 数据

桌面版会把数据放在 exe 同级目录：

```text
data\history.sqlite
uploads\
reports\
reports\exports\
shipment_config.json
app_settings.json
```

点击页面右上方的“数据目录”按钮，可以选择历史库、上传缓存、日报包保存在哪个本地目录。

导出 CSV、JSON、PNG 时会弹出“另存为”窗口，可以选择保存路径。浏览器模式下会保存到：

```text
reports\exports\
```

换电脑时如果要保留历史数据，把整个文件夹一起拷贝。

## 注意

- 第一次打开可能会被 Windows Defender 扫描，稍等即可。
- 如果打不开窗口，请确认系统已安装 Microsoft Edge WebView2 Runtime。Windows 10/11 通常已经自带。
- 这个桌面版不需要 Cloudflare、域名或公网访问。
