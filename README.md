# KPL 全赛季 iOS 日历订阅

这个项目从 KPL 官网公开接口读取当前赛季的全部赛程，生成 `kpl-summer-playoffs.ics`。每场比赛使用固定 UID，因此“待定”对阵、比分、状态或时间变化时，iOS 会更新原事件，不会重复创建新比赛。

程序会自动读取官网标记的当前赛季，不再硬编码某个夏季赛或只筛选季后赛。当前赛季结束后，官网切换到春季赛、夏季赛或年度总决赛时，订阅会自动跟随新赛季。

## 立即生成一次

在本目录打开 PowerShell：

```powershell
python .\update_calendar.py --output .\kpl-summer-playoffs.ics
```

如需查看历史赛季，可临时指定赛季 ID，例如：

```powershell
python .\update_calendar.py --season-id KPL2026S2 --output .\kpl-summer-playoffs.ics
```

## 每天 00:00 自动更新（Windows）

以当前 Windows 用户运行一次：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
```

电脑在 00:00 关机或睡眠时，任务会在下次可运行时补执行。也可以双击 `run_update.bat` 手动更新。

## 让 iPhone 订阅

### 同一 Wi-Fi 临时使用

1. 先运行更新程序，再启动服务：

   ```powershell
   python .\serve_calendar.py --port 8787
   ```

2. 在 Windows PowerShell 查询本机局域网 IPv4：

   ```powershell
   (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi').IPAddress
   ```

3. 在 iPhone：设置 → 日历 → 日历账户 → 添加账户 → 添加订阅日历，填写：

   `http://电脑局域网IP:8787/kpl-summer-playoffs.ics`

电脑必须保持开机、服务保持运行，且手机和电脑在同一网络。若 Windows 防火墙拦截 8787 端口，需要允许 Python 通过专用网络。

### 长期、跨网络使用（推荐）

GitHub Actions 会按北京时间每天 00:00（GitHub 的 `16:00 UTC`）抓取官网当前赛季的全部阶段并提交新的 ICS。日历文件变化后，GitHub Pages 会自动重新发布。

GitHub 的定时任务可能因平台排队延迟几分钟，iOS 也会按系统的订阅刷新策略获取更新；如果需要立即检查，可在仓库 Actions 页面手动运行 `Update KPL calendar`。

本仓库已经部署好的公网订阅地址：

`https://moqingquan.github.io/kpl-summer-playoffs-calendar/kpl-summer-playoffs.ics`

在 iPhone 中请使用“添加订阅日历”添加上面的地址，不要选择“导入文件”；否则只能得到一次性快照。

## 数据来源与边界

- 数据源：KPL 官网赛程页使用的公开接口，官网页面为 <https://kpl.qq.com/#/Schedule>。
- 接口返回的“待定”队伍会在官方赛果确认后变为真实队伍；程序不会根据传闻或自行推测结果。
- 比赛结束时间按开始时间后 4 小时估算，日历主要用于提醒开赛；官方时间如有调整，以官网为准。
- 如果官方临时改期，下一次更新会同时修改事件的开始时间。

