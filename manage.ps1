#Requires -Version 5.1
<#
.SYNOPSIS
    KKU Bot Management Console
.DESCRIPTION
    Professional management script for KKU Bot project.
    Manages Bot, API, and Dashboard services.
.NOTES
    Author: KKU Bot Team
    Version: 2.0
#>

$ProjectPath = "C:\Users\qqq\Desktop\KKU BOT\kku-bot"
$BotScript = "bot.main"
$APICommand = "uvicorn bot.api.main:app --host 0.0.0.0 --port 8000 --reload"
$DashboardDir = "$ProjectPath\dashboard"
$PythonCmd = $null
$NodeCmd = $null
$NpmCmd = $null

# --- Color Definitions ---
$C = @{
    Header  = 'Green'
    Menu    = 'Cyan'
    Success = 'Green'
    Warning = 'Yellow'
    Error   = 'Red'
    Info    = 'White'
    Dim     = 'DarkGray'
    Accent  = 'Magenta'
    Title   = 'Cyan'
}

# ============================================================
#  INITIALIZATION
# ============================================================

function Test-Dependencies {
    Write-Host "`n  Checking dependencies..." -ForegroundColor $C.Dim

    # Python
    $pyPaths = @("python", "py", "python3")
    foreach ($cmd in $pyPaths) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) {
            $script:PythonCmd = $cmd
            $ver = & $cmd --version 2>&1
            Write-Host "  [OK] Python  : $ver" -ForegroundColor $C.Success
            break
        }
    }
    if (-not $script:PythonCmd) {
        Write-Host "  [!!] Python  : NOT FOUND" -ForegroundColor $C.Error
    }

    # Node.js
    $nodeFound = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeFound) {
        $script:NodeCmd = "node"
        $ver = & node --version
        Write-Host "  [OK] Node.js : $ver" -ForegroundColor $C.Success
    } else {
        Write-Host "  [!!] Node.js : NOT FOUND" -ForegroundColor $C.Error
    }

    # npm
    $npmFound = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmFound) {
        $script:NpmCmd = "npm"
        $ver = & npm --version
        Write-Host "  [OK] npm     : v$ver" -ForegroundColor $C.Success
    } else {
        Write-Host "  [!!] npm     : NOT FOUND" -ForegroundColor $C.Error
    }

    if (-not $script:PythonCmd -or -not $script:NodeCmd -or -not $script:NpmCmd) {
        Write-Host "`n  WARNING: Some dependencies are missing. Some features may not work." -ForegroundColor $C.Warning
        Start-Sleep -Seconds 2
    }
}

# ============================================================
#  UI HELPERS
# ============================================================

function Write-Box {
    param([string]$Text, [string]$Color = 'Cyan')
    $line = "=" * 50
    Write-Host ""
    Write-Host "  $line" -ForegroundColor $Color
    Write-Host "  $Text" -ForegroundColor $Color
    Write-Host "  $line" -ForegroundColor $Color
}

function Write-Status {
    param(
        [string]$Service,
        [string]$State,
        [string]$Detail = ""
    )
    $color = switch ($State) {
        "RUNNING" { $C.Success }
        "STOPPED" { $C.Error }
        "STARTING" { $C.Warning }
        "UNKNOWN" { $C.Dim }
    }
    $icon = switch ($State) {
        "RUNNING" { "[+]" }
        "STOPPED" { "[-]" }
        "STARTING" { "[~]" }
        "UNKNOWN" { "[?]" }
    }
    $detailStr = if ($Detail) { " - $Detail" } else { "" }
    Write-Host "  $icon " -ForegroundColor $color -NoNewline
    Write-Host "$Service : " -ForegroundColor $C.Info -NoNewline
    Write-Host "$State$detailStr" -ForegroundColor $color
}

function Write-Separator {
    Write-Host ("  " + "-" * 46) -ForegroundColor $C.Dim
}

function Confirm-Action {
    param([string]$Message)
    Write-Host ""
    Write-Host "  $Message" -ForegroundColor $C.Warning -NoNewline
    $resp = Read-Host " (y/N)"
    return ($resp -eq "y" -or $resp -eq "Y")
}

function Pause-Script {
    Write-Host ""
    Write-Host "  Press any key to continue..." -ForegroundColor $C.Dim
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# ============================================================
#  SERVICE PROCESS MANAGEMENT
# ============================================================

function Get-KKUProcesses {
    $procs = @{
        Bot  = @()
        API  = @()
        Dash = @()
    }

    # Bot and API both run as python with uvicorn/bot.main
    $pyProcesses = Get-Process python -ErrorAction SilentlyContinue
    foreach ($p in $pyProcesses) {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine) {
                if ($cmdLine -match "bot\.main") {
                    $procs.Bot += $p
                }
                elseif ($cmdLine -match "uvicorn.*bot\.api") {
                    $procs.API += $p
                }
            }
        } catch {}
    }

    # Dashboard - look for node processes related to vite
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
    foreach ($p in $nodeProcesses) {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine -and $cmdLine -match "vite|dashboard") {
                $procs.Dash += $p
            }
        } catch {}
    }

    return $procs
}

function Stop-ServiceProcesses {
    param(
        [string]$ServiceName = "All",
        [switch]$Silent
    )

    $procs = Get-KKUProcesses

    $toStop = @()
    switch ($ServiceName) {
        "All"      { $toStop = $procs.Bot + $procs.API + $procs.Dash }
        "Bot"      { $toStop = $procs.Bot }
        "API"      { $toStop = $procs.API }
        "Dashboard"{ $toStop = $procs.Dash }
    }

    if ($toStop.Count -eq 0) {
        if (-not $Silent) {
            Write-Host "  No $ServiceName processes to stop." -ForegroundColor $C.Dim
        }
        return
    }

    foreach ($p in $toStop) {
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            if (-not $Silent) {
                Write-Host "  Stopped process PID $($p.Id)" -ForegroundColor $C.Warning
            }
        } catch {
            if (-not $Silent) {
                Write-Host "  Failed to stop PID $($p.Id): $_" -ForegroundColor $C.Error
            }
        }
    }

    Start-Sleep -Milliseconds 500
}

# ============================================================
#  SERVICE STARTERS
# ============================================================

function Start-BotService {
    Write-Host ""
    Write-Host "  Starting Bot (Telegram)..." -ForegroundColor $C.Title

    if (-not $script:PythonCmd) {
        Write-Host "  [FAIL] Python not found!" -ForegroundColor $C.Error
        return $false
    }

    Stop-ServiceProcesses -ServiceName "Bot" -Silent

    $logFile = Join-Path $ProjectPath "logs\bot.log"
    $errFile = Join-Path $ProjectPath "logs\bot_error.log"
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath "logs") | Out-Null

    try {
        Start-Process -FilePath $script:PythonCmd `
            -ArgumentList "-m $BotScript" `
            -WorkingDirectory $ProjectPath `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError $errFile `
            -WindowStyle Hidden

        Start-Sleep -Seconds 3

        $procs = Get-KKUProcesses
        if ($procs.Bot.Count -gt 0) {
            Write-Host "  [OK] Bot started successfully (PID: $($procs.Bot[0].Id))" -ForegroundColor $C.Success
            return $true
        } else {
            Write-Host "  [FAIL] Bot failed to start. Check logs\bot_error.log" -ForegroundColor $C.Error
            return $false
        }
    } catch {
        Write-Host "  [FAIL] $_" -ForegroundColor $C.Error
        return $false
    }
}

function Start-APIService {
    Write-Host ""
    Write-Host "  Starting API Server..." -ForegroundColor $C.Title

    if (-not $script:PythonCmd) {
        Write-Host "  [FAIL] Python not found!" -ForegroundColor $C.Error
        return $false
    }

    Stop-ServiceProcesses -ServiceName "API" -Silent

    $logFile = Join-Path $ProjectPath "logs\api.log"
    $errFile = Join-Path $ProjectPath "logs\api_error.log"
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath "logs") | Out-Null

    try {
        Start-Process -FilePath $script:PythonCmd `
            -ArgumentList "-m $APICommand" `
            -WorkingDirectory $ProjectPath `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError $errFile `
            -WindowStyle Hidden

        Start-Sleep -Seconds 4

        $procs = Get-KKUProcesses
        if ($procs.API.Count -gt 0) {
            Write-Host "  [OK] API started successfully (PID: $($procs.API[0].Id))" -ForegroundColor $C.Success
            return $true
        } else {
            Write-Host "  [FAIL] API failed to start. Check logs\api_error.log" -ForegroundColor $C.Error
            return $false
        }
    } catch {
        Write-Host "  [FAIL] $_" -ForegroundColor $C.Error
        return $false
    }
}

function Start-DashboardService {
    Write-Host ""
    Write-Host "  Starting Dashboard..." -ForegroundColor $C.Title

    if (-not $script:NpmCmd) {
        Write-Host "  [FAIL] npm not found!" -ForegroundColor $C.Error
        return $false
    }

    if (-not (Test-Path "$DashboardDir\package.json")) {
        Write-Host "  [FAIL] Dashboard not found at $DashboardDir" -ForegroundColor $C.Error
        return $false
    }

    Stop-ServiceProcesses -ServiceName "Dashboard" -Silent

    $logFile = Join-Path $ProjectPath "logs\dashboard.log"
    $errFile = Join-Path $ProjectPath "logs\dashboard_error.log"
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath "logs") | Out-Null

    try {
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c cd /d `"$DashboardDir`" && npm run dev" `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError $errFile `
            -WindowStyle Hidden

        Start-Sleep -Seconds 5

        $procs = Get-KKUProcesses
        if ($procs.Dash.Count -gt 0) {
            Write-Host "  [OK] Dashboard started successfully (PID: $($procs.Dash[0].Id))" -ForegroundColor $C.Success
            return $true
        } else {
            Write-Host "  [FAIL] Dashboard failed to start. Check logs\dashboard_error.log" -ForegroundColor $C.Error
            return $false
        }
    } catch {
        Write-Host "  [FAIL] $_" -ForegroundColor $C.Error
        return $false
    }
}

# ============================================================
#  MAIN ACTIONS
# ============================================================

function Invoke-StartAll {
    Write-Box "START ALL SERVICES"

    Stop-ServiceProcesses -ServiceName "All" -Silent
    Start-Sleep -Seconds 1

    $results = @()
    $results += Start-BotService
    $results += Start-APIService
    $results += Start-DashboardService

    Write-Separator
    $successCount = ($results | Where-Object { $_ -eq $true }).Count
    if ($successCount -eq 3) {
        Write-Host "  All 3 services started successfully!" -ForegroundColor $C.Success
    } elseif ($successCount -gt 0) {
        Write-Host "  $successCount of 3 services started." -ForegroundColor $C.Warning
    } else {
        Write-Host "  Failed to start services. Check logs for details." -ForegroundColor $C.Error
    }
    Write-Separator

    Write-Host ""
    Write-Host "  Endpoints:" -ForegroundColor $C.Accent
    Write-Host "    Bot       -> Telegram" -ForegroundColor $C.Info
    Write-Host "    API       -> http://localhost:8000" -ForegroundColor $C.Info
    Write-Host "    Dashboard -> http://localhost:5173" -ForegroundColor $C.Info
}

function Invoke-StopAll {
    Write-Box "STOP ALL SERVICES" -Color $C.Error

    if (-not (Confirm-Action "Stop all running services?")) {
        Write-Host "  Cancelled." -ForegroundColor $C.Dim
        return
    }

    Stop-ServiceProcesses -ServiceName "All"
    Write-Host ""
    Write-Host "  All services stopped." -ForegroundColor $C.Success
}

function Invoke-RestartAll {
    Write-Box "RESTART ALL SERVICES" -Color $C.Warning

    Stop-ServiceProcesses -ServiceName "All" -Silent
    Start-Sleep -Seconds 2
    Invoke-StartAll
}

function Invoke-ShowStatus {
    Write-Box "SERVICE STATUS" -Color $C.Accent

    $procs = Get-KKUProcesses

    # --- Bot ---
    if ($procs.Bot.Count -gt 0) {
        $pids = ($procs.Bot | ForEach-Object { $_.Id }) -join ", "
        Write-Status -Service "Bot (Telegram)" -State "RUNNING" -Detail "PID: $pids"
    } else {
        Write-Status -Service "Bot (Telegram)" -State "STOPPED"
    }

    # --- API ---
    if ($procs.API.Count -gt 0) {
        $pids = ($procs.API | ForEach-Object { $_.Id }) -join ", "
        Write-Status -Service "API Server" -State "RUNNING" -Detail "PID: $pids"
    } else {
        Write-Status -Service "API Server" -State "STOPPED"
    }

    # Port check for API
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 8000)
        $tcp.Close()
        Write-Status -Service "API (port 8000)" -State "RUNNING"
    } catch {
        Write-Status -Service "API (port 8000)" -State "STOPPED"
    }

    # --- Dashboard ---
    if ($procs.Dash.Count -gt 0) {
        $pids = ($procs.Dash | ForEach-Object { $_.Id }) -join ", "
        Write-Status -Service "Dashboard" -State "RUNNING" -Detail "PID: $pids"
    } else {
        Write-Status -Service "Dashboard" -State "STOPPED"
    }

    # Port check for Dashboard
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 5173)
        $tcp.Close()
        Write-Status -Service "Dashboard (port 5173)" -State "RUNNING"
    } catch {
        # Try port 3000 as well
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", 3000)
            $tcp.Close()
            Write-Status -Service "Dashboard (port 3000)" -State "RUNNING"
        } catch {
            Write-Status -Service "Dashboard (port 5173)" -State "STOPPED"
        }
    }

    Write-Separator
}

function Invoke-StartSingle {
    param([string]$Service)

    switch ($Service) {
        "Bot"       { Start-BotService }
        "API"       { Start-APIService }
        "Dashboard" { Start-DashboardService }
    }
}

# ============================================================
#  MENU
# ============================================================

function Show-Menu {
    Clear-Host

    $title = @"

  ============================================
       KKU Bot Management Console v2.0
  ============================================

"@
    Write-Host $title -ForegroundColor $C.Header

    $procs = Get-KKUProcesses
    $runningCount = 0
    if ($procs.Bot.Count -gt 0)  { $runningCount++ }
    if ($procs.API.Count -gt 0)  { $runningCount++ }
    if ($procs.Dash.Count -gt 0) { $runningCount++ }

    Write-Host "  Services running: " -ForegroundColor $C.Dim -NoNewline
    if ($runningCount -eq 3) {
        Write-Host "$runningCount/3" -ForegroundColor $C.Success
    } elseif ($runningCount -eq 0) {
        Write-Host "$runningCount/3" -ForegroundColor $C.Error
    } else {
        Write-Host "$runningCount/3" -ForegroundColor $C.Warning
    }

    Write-Host ""
    Write-Host "  [1] Start All Services"       -ForegroundColor $C.Menu
    Write-Host "  [2] Stop All Services"        -ForegroundColor $C.Menu
    Write-Host "  [3] Restart All Services"     -ForegroundColor $C.Menu
    Write-Host "  [4] Start Bot Only"           -ForegroundColor $C.Menu
    Write-Host "  [5] Start API Only"           -ForegroundColor $C.Menu
    Write-Host "  [6] Start Dashboard Only"     -ForegroundColor $C.Menu
    Write-Host "  [7] Show Status"              -ForegroundColor $C.Menu
    Write-Host "  [8] Exit"                     -ForegroundColor $C.Menu

    Write-Host ""
    Write-Host "  =========================================" -ForegroundColor $C.Dim
}

# ============================================================
#  MAIN LOOP
# ============================================================

function Start-ManagementConsole {
    Test-Dependencies

    do {
        Show-Menu
        $choice = Read-Host "  Enter your choice (1-8)"

        switch ($choice) {
            "1" { Invoke-StartAll }
            "2" { Invoke-StopAll }
            "3" { Invoke-RestartAll }
            "4" { Invoke-StartSingle -Service "Bot" }
            "5" { Invoke-StartSingle -Service "API" }
            "6" { Invoke-StartSingle -Service "Dashboard" }
            "7" { Invoke-ShowStatus }
            "8" {
                Write-Host ""
                Write-Host "  Goodbye!" -ForegroundColor $C.Warning
                Write-Host ""
                return
            }
            default {
                Write-Host ""
                Write-Host "  Invalid choice. Please enter 1-8." -ForegroundColor $C.Error
            }
        }

        Pause-Script
    } while ($true)
}

# Run
Start-ManagementConsole
