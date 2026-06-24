# 发货看板桌面版

## 打包

在项目目录运行：

```powershell
.\build_desktop.ps1
```

输出目录：

```text
release\发货看板\
```

## 使用

把整个 `release\发货看板\` 文件夹拷贝到老板或其他电脑，双击：

```text
发货看板.exe
```

## 数据

桌面版会把数据放在 exe 同级目录：

```text
data\history.sqlite
uploads\
reports\
shipment_config.json
```

换电脑时如果要保留历史数据，把整个文件夹一起拷贝。

## 注意

- 第一次打开可能会被 Windows Defender 扫描，稍等即可。
- 如果打不开窗口，请确认系统已安装 Microsoft Edge WebView2 Runtime。Windows 10/11 通常已经自带。
- 这个桌面版不需要 Cloudflare、域名或公网访问。
