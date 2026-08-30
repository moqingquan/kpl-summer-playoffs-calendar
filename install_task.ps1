$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python -ErrorAction Stop).Source
$Script = Join-Path $ProjectDir "update_calendar.py"
$Output = Join-Path $ProjectDir "kpl-summer-playoffs.ics"
$TaskName = "KPL Summer Playoffs Calendar Update"

$Action = New-ScheduledTaskAction `
  -Execute $Python `
  -Argument "`"$Script`" --season-id KPL2026S2 --output `"$Output`"" `
  -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Daily -At 00:00
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Write-Host "已设置每天 00:00 更新：$TaskName"
Write-Host "可用以下命令立即测试：python `"$Script`" --season-id KPL2026S2 --output `"$Output`""

