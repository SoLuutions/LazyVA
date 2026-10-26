# LazyVA ⚡

**Intelligent Keep-Awake, Productivity & Activity Assistant for Windows**  
*Built for Virtual Assistants, Freelancers, and Remote Professionals.*

---

## 🌟 Overview

**LazyVA** is a modern, commercial-ready Windows desktop SaaS application designed to prevent unexpected system idle timeouts, keep displays active during long downloads or presentations, and maintain healthy, natural work-rest rhythms.

Unlike crude mouse jigglers that trigger antivirus alarms or robotic straight-line detections, LazyVA uses:
- **Cubic Bezier Glide**: Organic human-like mouse trajectories with natural ease-in/ease-out acceleration, subtle micro-tremors, and randomized paths.
- **Micro-Jitter Nudge**: 1–4 pixel imperceptible movements for ultra-stealth operation.
- **Native Windows OS Keep-Alive**: Direct `kernel32.SetThreadExecutionState` calls to prevent sleep and display timeout without moving the cursor at all.
- **Auto-Pause on User Interaction**: Automatically yields when the user touches their mouse, avoiding pointer resistance.
- **Smart Pomodoro Breaks**: Automated 25m work / 5m rest cycles with desktop status alerts.
- **Global Hotkeys**: Instant control with **F9** (Start), **F10** (Stop), and **F11** (Exit).
- **System Tray Integration**: Dynamic status badge icons (Green for Active, Amber for Break, Gray for Idle) and quick context menu.
- **SaaS Licensing & Feature Gating**: Machine hardware fingerprinting (HWID), 7-day free trial, and encrypted offline token verification.
- **Soft Meadow / Twilight Meadow Themes**: Calm cream-and-sage day colors and a soft periwinkle night palette, with a saved theme toggle.

---

## 📁 Repository Structure

```
LazyVA/
├── lazyva/                     # Core Desktop Application Package
│   ├── app.py                  # Master application orchestrator
│   ├── config.py               # JSON settings manager (%APPDATA%/LazyVA)
│   ├── core/
│   │   ├── curves.py           # Cubic Bezier human curve math
│   │   ├── engine.py           # Simulation engine worker thread
│   │   ├── hotkeys.py          # Global hotkey listener (F9/F10/F11)
│   │   ├── keepalive.py        # Windows Win32 SetThreadExecutionState
│   │   └── scheduler.py        # Work/Break Pomodoro state machine
│   ├── licensing/
│   │   ├── hwid.py             # Anonymous Machine HWID fingerprint
│   │   ├── manager.py          # SaaS licensing & offline grace manager
│   │   └── validator.py        # Cryptographic HMAC token verification
│   ├── ui/
│   │   ├── main_window.py      # CustomTkinter Soft Meadow / Twilight Meadow UI
│   │   ├── theme.py            # Shared day/night pastel color tokens
│   │   └── tray.py             # Pystray notification area integration
│   └── updater/
│       └── auto_updater.py     # Background version checker & silent updater
├── server/                     # SaaS Licensing & Webhook Server
│   ├── main.py                 # FastAPI license server & webhooks
│   ├── schema.sql              # Supabase / PostgreSQL schema
│   └── requirements.txt        # Server dependencies
├── packaging/                  # Windows Build & Distribution
│   ├── build.bat               # 1-click Windows build script
│   ├── build_exe.py            # PyInstaller build automation
│   ├── LazyVA_Setup.iss        # Inno Setup Windows installer script
│   └── version_info.txt        # Windows PE executable metadata
├── assets/                     # App icons (PNG & multi-size ICO)
├── requirements.txt            # Client dependencies
├── run.py                      # Root development runner
└── SAAS_GUIDE.md               # Complete payment, launch, and marketing guide
```

---

## 🚀 Quickstart (Development)

### 1. Requirements
- Python 3.10+ (tested through Python 3.13 / 3.14)
- Windows 10/11 (or Linux/macOS for development)

### 2. Setup Virtual Environment
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run Application
```bash
python run.py
```
To start directly minimized to the system tray:
```bash
python run.py --minimized
```

---

## 📦 Building for Windows (.EXE & Installer)

### 1-Click Build (on Windows):
Double-click `packaging\build.bat` or run:
```cmd
packaging\build.bat
```
The script works from any current directory and rebuilds the output from the
checked-out source. Close any running LazyVA copy, including one in the system
tray, before rebuilding so Windows can replace its files. To preview the build
before installing it, run
`dist\LazyVA\LazyVA.exe` directly; an existing Start Menu shortcut may still
launch a previously installed copy.

The app follows the Windows appearance by default. Use the theme button in the
header to switch between Soft Meadow and Twilight Meadow; your choice is saved
for the next launch.

### Manual Build Steps:
1. **Compile Standalone Executable**:
   ```cmd
   python packaging\build_exe.py
   ```
   Outputs folder to `dist\LazyVA\LazyVA.exe`.

2. **Compile Windows Setup Wizard**:
   Open `packaging\LazyVA_Setup.iss` in [Inno Setup 6](https://jrsoftware.org/isdl.php) and click **Compile** (or run `ISCC.exe packaging\LazyVA_Setup.iss`).  
   Outputs `dist\LazyVA_Setup_v1.0.0.exe`.

---

## 🌐 SaaS Licensing Server

The server handles license activation, machine limit enforcement, auto-updates, and payment webhooks:

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Endpoints:
- `POST /api/v1/license/activate` — Binds license key to machine HWID and returns signed token.
- `POST /api/v1/license/validate` — Validates device activation status.
- `POST /api/v1/license/deactivate` — Releases activation slot for another PC.
- `GET /api/v1/version` — Checks for new versions (used by client auto-updater).
- `POST /api/v1/webhooks/paymongo` — Automated GCash/Maya license generation.
- `POST /api/v1/webhooks/lemonsqueezy` — Automated international credit card orders.

See **[SAAS_GUIDE.md](file:///home/soluutions/Projects/LazyVA/SAAS_GUIDE.md)** for detailed payment gateway configuration, Supabase setup, and pricing recommendations.
