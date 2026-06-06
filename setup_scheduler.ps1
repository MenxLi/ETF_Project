# setup_scheduler.ps1
# Run as Administrator in PowerShell

$Python   = "D:\AI_PROJECT\.venv\Scripts\python.exe"
$WorkDir  = "D:\AI_PROJECT"
$Weekdays = @("Monday","Tuesday","Wednesday","Thursday","Friday")

function Register-WeekdayTask {
    param($Name, $Argument, $Time, [int]$TimeoutMin = 10)
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    $trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekdays -At $Time
    $action   = New-ScheduledTaskAction -Execute $Python -Argument $Argument -WorkingDirectory $WorkDir
    $settings = New-ScheduledTaskSettingsSet -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes $TimeoutMin) -StartWhenAvailable
    Register-ScheduledTask -TaskName $Name -Trigger $trigger -Action $action -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Host "  OK $Name  (Weekday $Time)" -ForegroundColor Green
}

function Register-SundayTask {
    param($Name, $Argument, $Time, [int]$TimeoutMin = 30)
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    $trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $Time
    $action   = New-ScheduledTaskAction -Execute $Python -Argument $Argument -WorkingDirectory $WorkDir
    $settings = New-ScheduledTaskSettingsSet -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes $TimeoutMin) -StartWhenAvailable
    Register-ScheduledTask -TaskName $Name -Trigger $trigger -Action $action -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Host "  OK $Name  (Sunday $Time)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Registering scheduled tasks..." -ForegroundColor Cyan
Write-Host ""

Write-Host "-- Weekday tasks --" -ForegroundColor Yellow
Register-WeekdayTask "Quant_Open"  "-m quant.signals.intraday --node open"  "09:25"
Register-WeekdayTask "Quant_Amend" "-m quant.signals.intraday --node amend" "11:25"
Register-WeekdayTask "Quant_PM"    "-m quant.signals.intraday --node pm"    "13:05"
Register-WeekdayTask "Quant_Close" "-m quant.signals.intraday --node close" "14:50"
Register-WeekdayTask "Quant_Daily" "run_daily.py"                           "15:35"

Write-Host ""
Write-Host "-- Sunday tasks --" -ForegroundColor Yellow
Register-SundayTask "Quant_Weekly"  "run_weekly.py"  "10:00" 30
Register-SundayTask "Quant_Monthly" "run_monthly.py" "12:00" 90

Write-Host ""
Write-Host "All tasks registered." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Weekdays:"
Write-Host "    09:25  Intraday open node"
Write-Host "    11:25  Intraday morning close node"
Write-Host "    13:05  Intraday afternoon open node"
Write-Host "    14:50  Intraday close node"
Write-Host "    15:35  Daily signal + report"
Write-Host ""
Write-Host "  Sundays:"
Write-Host "    10:00  Weekly model retrain"
Write-Host "    12:00  Monthly Optuna tuning (first Sunday only)"
