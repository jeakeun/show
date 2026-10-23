# Registers the webdrama publish task (main PC only). Days/time must match config.json publish_days/publish_time.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$action = New-ScheduledTaskAction -Execute "$here\run_publish.bat" -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Thursday,Saturday -At 19:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "Webdrama_Publish" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Registered: Webdrama_Publish (Tue/Thu/Sat 19:00)"