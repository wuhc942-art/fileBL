# 发货看板项目交接上下文

更新时间：2026-06-23  
项目目录：`C:\Users\Administrator\Documents\excel push`

## 项目目标

做一个本地 Excel 发货分析软件。用户每天拖入一个或多个发货统计 Excel 大表，软件自动读取每个文件里的 `发货明细`，按选择日期汇总：

- 发货客户
- 型号/品名
- 数量
- 金额
- 来源文件
- 异常记录
- 老板/业务可快速查看的对比和提醒

后续目标是：

- 这些大表里本身包含历史日期，要把历史记录一直拉进来作为历史库。
- 给外地的人看，不只在本地运行。
- 计划使用 Cloudflare Tunnel 把本地服务安全映射成 HTTPS 地址。

## 当前已完成

### 1. 本地看板

本地服务地址：

```text
http://127.0.0.1:8765/
```

启动脚本：

```powershell
.\start_dashboard.ps1
```

或手动启动：

```powershell
python app_server.py --host 127.0.0.1 --port 8765 --no-browser
```

当前服务是一个 Python `ThreadingHTTPServer`，前端在 `web/` 目录，不依赖 npm。

### 2. 上传文件数量已改成不固定

最初 UI 写的是“三张发货统计表”，现在已经改成：

- `拖入发货统计表`
- 支持一个或多个 Excel 文件
- 后端不再要求固定 3 个文件

### 3. 每日汇总

核心解析在：

```text
summarize_shipments.py
```

核心接口在：

```text
app_server.py
```

当前会读取 Excel 的 `发货明细` sheet，按选择日期筛选送货记录，输出：

- KPI：发货笔数、客户数、总数量、总金额
- 客户金额排行
- 型号金额排行
- 来源文件占比
- 客户汇总
- 发货明细表

### 4. 型号识别规则

已经支持“纯胶膜后面才是产品名称”的规则。

规则中心在：

```text
shipment_config.json
```

当前配置包含：

```json
"product_name_rules": [
  { "model": "纯胶膜", "use_spec_as_name": true },
  { "model": "覆盖膜", "use_spec_as_name": true },
  { "model": "保护膜", "use_spec_as_name": true },
  { "model": "离型膜", "use_spec_as_name": true }
]
```

也预留了客户/型号别名库：

```json
"aliases": {
  "customers": {},
  "models": {}
}
```

### 5. 数据核对功能

已加：

- 导入检查：是否有 `发货明细`、是否能识别日期列、月份是否匹配
- 数据质量提示：
  - 空客户
  - 空型号
  - 金额为 0
  - 数量为 0
  - 金额为负
  - 数量为负
  - 缺送货单号
  - 缺单价
  - 疑似重复
- 去重逻辑：
  - 按 `送货单号 + 客户 + 型号 + 数量 + 金额` 判断疑似重复
- 异常页：
  - 不只是底部一句话，现在有“需要核对”列表
  - 点击异常记录可以定位到明细

### 6. 老板/业务速览

已加：

- 今天 vs 昨天
- 今天 vs 上周同日
- 金额、数量、客户数变化
- 客户排行可点击
- 型号排行可点击
- 型号抽屉：点型号后看哪些客户买了它
- 金额结构：
  - 含税 / 现金
  - 奥科泰 / 科泰顺
- 大客户提醒：
  - 当前阈值 `100000`
  - 配置在 `shipment_config.json` 的 `high_value_threshold`
- 新客户 / 沉默客户：
  - 当前基于昨天和上周同日做初版判断
  - 后续要改成基于全量历史库判断

### 7. 日报工作流

已加：

- 保存日报包按钮
- 保存路径：

```text
reports\YYYY-MM-DD\
```

例如：

```text
reports\2026-06-23\
```

包含：

- `summary-YYYY-MM-DD.json`
- `details-YYYY-MM-DD.csv`
- `anomalies-YYYY-MM-DD.csv`
- `manifest-YYYY-MM-DD.json`

### 8. 日报模板

前端已加三种模板切换：

- 老板版
- 财务版
- 仓库版

目前是通过前端显示/隐藏模块实现，后续可以继续优化为真正不同的导出模板。

### 9. PNG 图片报表修复

之前 PNG 报表里型号文字、绿色条和金额重叠。已修复：

- PNG 画布加宽
- 型号排行自动留更宽文字列
- 条形图、金额、文字分区
- 长型号截断

## 已验证

最后一次完整验证通过：

```powershell
python -m unittest discover -s tests -v
python -m py_compile app_server.py summarize_shipments.py
```

测试结果：

- 4 个单元测试通过
- Python 编译通过
- 浏览器刷新无前端错误
- 用真实上传样例打接口，确认：
  - `importChecks`
  - `anomalies`
  - `comparisons`
  - `amountStructure`
  - `businessAlerts`
  都正常返回
- `保存日报包` 已验证能写入 `reports/2026-06-23`

## 关键文件

```text
app_server.py             # 本地 Web 服务和 API
summarize_shipments.py    # Excel 解析、汇总、规则
shipment_config.json      # 数据源、规则、阈值、别名配置
web/index.html            # 前端结构
web/app.js                # 前端交互、图表、导出
web/app.css               # 前端样式
tests/                    # 单元测试
reports/                  # 已保存的日报包
uploads/                  # 用户上传过的 Excel
run_daily.ps1             # 旧的定时日报脚本
send_wechat.ps1           # 旧的微信文件传输助手脚本
start_dashboard.ps1       # 本地看板启动脚本
```

## 下一步要做

用户最新需求：

> 发货历史记录表的数据也一直拉进去，做对比；落地成一个软件；不只在本地运行，可以分享给外地的人用。

用户补充说明：

> 历史记录不是单独文件，而是这些大表里面都有历史记录表/历史日期。要给外地的人看。用户有 Cloudflare 账号。

Cloudflare 账户主页用户给过：

```text
https://dash.cloudflare.com/f29132c44a81a657d9be9de42e9e9137/home/overview
```

注意：不要在未确认的情况下操作用户 Cloudflare 账户或发布公网服务。

## 建议实现方向

### A. 历史库能力

当前 `summarize_sources(paths, target_date)` 只按单日筛选。下一步要新增：

- 读取大表所有历史日期
- 建立本地历史索引
- 当前日期用于“今日看板”
- 全部历史用于对比和趋势

建议新增结构：

```text
history_store.py
```

或在 `summarize_shipments.py` 中新增：

- `extract_all_shipments(path)`
- `summarize_rows(rows, target_date)`
- `build_history_context(rows, target_date)`

历史对比建议包括：

- 今天 vs 昨天
- 今天 vs 上周同日
- 今天 vs 近 7 天平均
- 今天 vs 近 30 天平均
- 客户历史首发日期
- 客户最近发货日期
- 常发客户今天未发
- 客户金额趋势
- 型号金额趋势

### B. 新客户/沉默客户升级

当前新客户/沉默客户只看昨天和上周同日，下一步应改成：

- 新客户：历史库中从未出现，今天首次出现
- 沉默客户：过去 N 天常发，但今天没发
- 流失风险客户：超过 N 天未发
- 回流客户：沉默一段时间后今天重新发货

### C. 软件落地

分三档：

#### 1. 本地桌面版

打包成一个启动器：

- 双击启动 Python 服务
- 自动打开浏览器
- 适合老板电脑/办公室电脑使用

可以先写：

```text
start_dashboard_public.ps1
```

#### 2. 局域网版

服务绑定：

```powershell
python app_server.py --host 0.0.0.0 --port 8765 --no-browser
```

同一局域网的人通过：

```text
http://电脑IP:8765/
```

访问。

#### 3. 外地访问版

推荐使用 Cloudflare Tunnel：

- 本地仍跑 `http://127.0.0.1:8765`
- `cloudflared` 在本机发起隧道
- Cloudflare 提供公网 HTTPS 域名
- 不需要路由器端口映射
- 后续可以加 Cloudflare Access 登录保护

官方文档：

```text
https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/
https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/
```

建议新增：

```text
start_public_dashboard.ps1
CLOUDFLARE_DEPLOY.md
```

脚本思路：

1. 启动本地看板 `127.0.0.1:8765`
2. 启动 `cloudflared tunnel run <tunnel-name>`
3. 显示公网访问地址

## Cloudflare 外地访问注意事项

必须确认：

- 用户是否已有域名托管在 Cloudflare
- 想用什么子域名，例如：

```text
ship.example.com
fahuo.example.com
dashboard.example.com
```

- 是否要加访问密码/登录保护
- 是否允许外地用户上传 Excel
- 外地用户是只读看板，还是也能上传和保存日报

强烈建议：

- 先做 Cloudflare Tunnel + Access 登录
- 不要裸奔公开上传页面
- 至少加一个简单登录密码或 Cloudflare Access 邮箱白名单

## 推荐下一步对话开场

在另一台电脑继续时，可以直接说：

```text
请读取 HANDOFF.md，继续做下一步：
1. 从大表读取全量历史日期，建立历史对比；
2. 新客户/沉默客户改成基于全量历史；
3. 增加 Cloudflare Tunnel 外地访问部署脚本和说明；
4. 最后跑测试并启动本地服务。
```

## 当前风险和注意点

- 现在还没有登录权限，外地访问前必须考虑安全。
- 当前历史对比还不是全量历史，只是昨天/上周同日。
- Cloudflare 账号不能让 Codex 擅自操作，除非用户明确要求并在浏览器里配合。
- 当前服务是 Python 简单 HTTP 服务，够本地/小团队用；多人长期使用建议后续升级为 Flask/FastAPI + SQLite。
- 上传 Excel 中可能有敏感客户/金额数据，公网发布前必须加访问控制。

