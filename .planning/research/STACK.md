# Technology Stack

**Project:** Egg Counter -- Real-time egg counting and size classification on Raspberry Pi 5
**Researched:** 2026-03-19
**Overall Confidence:** MEDIUM -- based on training data (web search/Context7 unavailable for live verification). This is a well-established ecosystem with stable, mature libraries.

---

## Recommended Stack

### Computer Vision / ML Inference

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Ultralytics (YOLO11) | >=8.3.x | Object detection + classification | The `ultralytics` pip package provides YOLO11 (their latest architecture as of late 2024/2025). YOLO11n (nano) is purpose-built for edge devices like RPi 5. The Ultralytics Python API handles training, export, and inference in a single library. YOLO11 supersedes YOLOv8 with better accuracy at similar speed. | HIGH |
| NCNN | latest | Inference runtime on RPi 5 | Ultralytics officially recommends NCNN export for Raspberry Pi. NCNN is Tencent's lightweight inference framework optimized for ARM CPUs. On RPi 5's Cortex-A76, NCNN consistently outperforms ONNX Runtime and raw PyTorch by 2-4x for YOLO inference. The Ultralytics guide specifically benchmarks NCNN as fastest on RPi. | HIGH |
| OpenCV (opencv-python-headless) | >=4.9 | Camera capture, image preprocessing | The standard for USB camera capture on Linux/RPi. Use `headless` variant -- no GUI needed on the Pi (saves ~200MB). Handles V4L2 USB cameras natively. | HIGH |

### Backend / API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| FastAPI | >=0.115 | HTTP API + WebSocket server | Native WebSocket support via Starlette. Async-first design means the detection loop and web server coexist cleanly in one process. Type hints + Pydantic validation make the API self-documenting. Significantly faster than Flask for async workloads. | HIGH |
| Uvicorn | >=0.32 | ASGI server | The standard production server for FastAPI. Lightweight, fast, handles WebSocket upgrades natively. Use `uvicorn[standard]` for uvloop on Linux (ARM64 compatible). | HIGH |
| Pydantic | >=2.9 | Data validation / serialization | Comes with FastAPI. Use for egg detection event schemas, configuration validation, API response models. v2 is significantly faster than v1. | HIGH |

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| SQLite | 3.x (system) | Egg count storage, historical data | Zero-config, file-based, survives power outages with WAL mode. Perfect for single-user IoT on RPi. Under 100 eggs/day means zero scaling concerns. No database server to manage or crash. Included in Python stdlib. | HIGH |
| aiosqlite | >=0.20 | Async SQLite access | Wraps SQLite for async/await compatibility with FastAPI. Prevents the detection loop from blocking on database writes. | HIGH |

### Frontend / Dashboard

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Vanilla HTML/CSS/JS | N/A | Dashboard UI | For a single-page dashboard showing counts and charts, a full framework (React/Vue) is overkill. Vanilla JS with native WebSocket API is simpler, has zero build step, and can be served as static files from FastAPI. Reduces complexity on the Pi. | HIGH |
| Chart.js | >=4.4 | Historical data charts | Lightweight charting library (~60KB gzipped). Renders trend charts for daily/weekly egg production. No build tools needed -- single script tag. Simpler than D3 for this use case, more capable than CSS-only charts. | MEDIUM |
| Native WebSocket API | N/A | Real-time updates | Browser-native `WebSocket` class. No library needed. Handles reconnection with a simple wrapper function. Socket.IO is unnecessary overhead for a single-connection dashboard. | HIGH |

### Infrastructure / Deployment

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| systemd | system | Process management | Native on Raspberry Pi OS. Auto-restart on crash, start on boot, log management via journald. More reliable than pm2/supervisor for single-service Linux deployments. | HIGH |
| Cloudflare Tunnel (cloudflared) | latest | Remote access | Exposes the local dashboard to the internet without port forwarding, dynamic DNS, or a VPS. Free tier is sufficient. Provides HTTPS automatically. The Pi initiates the outbound connection so no inbound firewall rules needed. | MEDIUM |
| Python venv | system | Dependency isolation | Standard Python virtual environment. Keeps system Python clean. No Docker needed on RPi for a single-service deployment -- Docker adds memory overhead and complexity. | HIGH |
| Raspberry Pi OS (64-bit, Bookworm) | latest | Operating system | 64-bit is required for NCNN performance on Cortex-A76. Bookworm (Debian 12 based) is the current stable release. Use Lite variant (no desktop) to maximize available RAM for inference. | HIGH |

### Development Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.11 or 3.12 | Runtime | 3.11+ has significant performance improvements. 3.12 is well-supported on Bookworm. Avoid 3.13 on RPi -- ecosystem compatibility may lag. | HIGH |
| Ruff | latest | Linting + formatting | Replaces flake8, black, isort in a single Rust-based tool. Extremely fast. The modern Python standard. | HIGH |
| pytest | >=8.0 | Testing | Standard Python testing. Use pytest-asyncio for testing FastAPI endpoints and WebSocket handlers. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| python-dotenv | >=1.0 | Environment config | Load camera settings, model path, tunnel config from .env file | HIGH |
| Pillow | >=10.0 | Image manipulation | Resize/crop images for model input if OpenCV alone is insufficient. YOLO/Ultralytics includes this as a dependency. | HIGH |
| numpy | >=1.26 | Array operations | Comes with OpenCV and Ultralytics. Used for detection result processing. | HIGH |
| jinja2 | >=3.1 | HTML templating | Render the dashboard HTML with server-side values (API URL, initial data). FastAPI supports Jinja2 templates natively. | HIGH |

---

## Alternatives Considered

### ML / Inference

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Model | YOLO11n (nano) | YOLOv8n | YOLO11 is the successor with better accuracy/speed ratio. Same API, same `ultralytics` package. No reason to use the older architecture for new projects. |
| Model | YOLO11n (nano) | YOLOv5 | Legacy. Separate repository, different API. YOLO11 via Ultralytics is the maintained path forward. |
| Model size | Nano (n) | Small (s) or Medium (m) | Nano runs at ~50-80ms per frame on RPi 5 with NCNN. Small doubles inference time for marginal accuracy gain. For egg detection (large, distinct objects), nano is more than sufficient. |
| Runtime | NCNN | ONNX Runtime | ONNX Runtime on ARM64 is 2-3x slower than NCNN for YOLO models according to Ultralytics benchmarks. NCNN was specifically designed for mobile/edge ARM devices. |
| Runtime | NCNN | TensorFlow Lite | TFLite support for YOLO models is less mature. Export pipeline has more friction. NCNN is the officially recommended path from Ultralytics for RPi. |
| Runtime | NCNN | OpenVINO | OpenVINO targets Intel hardware (CPU/iGPU/VPU). No benefit on ARM-based Raspberry Pi. |
| Camera | OpenCV VideoCapture | Picamera2 | Picamera2 is for the Raspberry Pi Camera Module (CSI). The project spec says USB camera. OpenCV handles USB cameras via V4L2 on Linux natively. If switching to CSI camera later, Picamera2 would be better. |

### Backend

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Framework | FastAPI | Flask | Flask lacks native async support and native WebSocket handling. Flask-SocketIO adds Socket.IO complexity. FastAPI handles both REST and WebSocket in the same async event loop as the detection pipeline. |
| Framework | FastAPI | Django | Massive overkill for a single-page dashboard API. Django's ORM, admin, auth, middleware are unnecessary weight for this project. |
| Framework | FastAPI | Node.js (Express) | Adds a second language. The ML pipeline is Python (Ultralytics), so keeping the backend in Python avoids IPC complexity between detection and web server. |
| WebSocket | Native FastAPI/Starlette | Socket.IO | Socket.IO adds a protocol layer, requires a client library, and is designed for features (rooms, namespaces, fallback polling) this project does not need. Native WebSocket is simpler and lighter. |

### Database

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Database | SQLite | PostgreSQL | Requires a separate server process. Uses RAM on a constrained device. Overkill for under 100 records/day from a single writer. |
| Database | SQLite | InfluxDB | Time-series database is conceptually nice but adds operational complexity. SQLite with timestamp columns handles simple time-series queries perfectly at this scale. |
| Database | SQLite | JSON files | No query capability. Concurrent read/write risk. No atomic writes. SQLite gives durability guarantees that flat files do not. |
| ORM | Raw SQL / aiosqlite | SQLAlchemy | The schema is trivially simple (1-2 tables). SQLAlchemy adds abstraction overhead for zero benefit at this scale. |

### Frontend

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Framework | Vanilla JS | React | Build tooling (Node.js, webpack/vite), bundle size, and development complexity for a single page with 3-4 dynamic elements. React's component model provides no benefit here. |
| Framework | Vanilla JS | Vue | Same reasoning as React. Vue is lighter but still requires build tooling for SFC components. |
| Framework | Vanilla JS | HTMX | Interesting option for server-rendered partials but WebSocket integration in HTMX is less mature. Native WebSocket + DOM manipulation is more straightforward for real-time counter updates. |
| Charts | Chart.js | D3.js | D3 is low-level and requires significant code for basic charts. Chart.js produces production-quality bar/line charts with ~10 lines of config. |
| Charts | Chart.js | Plotly.js | Plotly is ~3MB. Chart.js is ~60KB. The dashboard needs simple line/bar charts, not scientific visualization. |

### Remote Access

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Tunnel | Cloudflare Tunnel | Tailscale | Tailscale requires the client device to also run Tailscale. Cloudflare Tunnel exposes a public URL accessible from any browser. Better for "check from phone" use case. |
| Tunnel | Cloudflare Tunnel | ngrok | ngrok free tier has session limits and changing URLs. Cloudflare Tunnel free tier provides stable subdomains. |
| Tunnel | Cloudflare Tunnel | Port forwarding | Requires router config, dynamic DNS, self-managed TLS certificates. Cloudflare handles all of this automatically. |
| Tunnel | Cloudflare Tunnel | VPS reverse proxy | Adds a $5+/month server to manage. Cloudflare Tunnel is free and zero-maintenance. |

---

## Model Training Workflow

Training happens OFF the Raspberry Pi, on a machine with a GPU (or Google Colab).

| Step | Tool | Notes |
|------|------|-------|
| Dataset annotation | Roboflow or CVAT | Label eggs with bounding boxes + size class. Roboflow has a free tier and exports directly to YOLO format. |
| Training | Ultralytics CLI / Python API | `yolo train model=yolo11n.pt data=eggs.yaml epochs=100` on a GPU machine. Fine-tune from the pretrained nano model. |
| Export | Ultralytics CLI | `yolo export model=best.pt format=ncnn` produces NCNN model files. |
| Deploy | SCP / rsync | Copy the exported NCNN model to the Pi. |

---

## System Resource Budget (RPi 5, 8GB)

| Component | Estimated RAM | CPU Impact |
|-----------|--------------|------------|
| YOLO11n NCNN inference | ~150-250 MB | ~30-40% of one core per frame |
| FastAPI + Uvicorn | ~50-80 MB | Minimal (async, event-driven) |
| SQLite | ~5-10 MB | Negligible |
| OS (Bookworm Lite) | ~300-400 MB | Baseline |
| **Total** | **~550-750 MB** | Leaves 7+ GB free on 8GB model |

The 4GB RPi 5 model would also work comfortably.

---

## Installation

```bash
# On development machine (for training)
pip install ultralytics

# On Raspberry Pi 5 (production)
# System prerequisites
sudo apt update && sudo apt install -y python3-venv python3-pip libgl1-mesa-glx

# Create project
mkdir -p ~/egg-counter && cd ~/egg-counter
python3 -m venv venv
source venv/bin/activate

# Core dependencies
pip install ultralytics          # YOLO11 + OpenCV + numpy + Pillow
pip install ncnn                 # NCNN Python bindings (ARM64 wheel)
pip install fastapi              # Web framework
pip install "uvicorn[standard]"  # ASGI server with uvloop
pip install aiosqlite            # Async SQLite
pip install python-dotenv        # Config management
pip install jinja2               # Template rendering

# Dev dependencies (on dev machine, not Pi)
pip install ruff                 # Linting + formatting
pip install pytest               # Testing
pip install pytest-asyncio       # Async test support
pip install httpx                # Test client for FastAPI
```

**Note on Ultralytics + NCNN:** The `ultralytics` package handles NCNN export and inference natively. When you call `model.export(format='ncnn')`, it installs/uses NCNN automatically. You may not need to `pip install ncnn` separately -- Ultralytics manages this dependency. Verify on the Pi after installing ultralytics.

---

## Key Version Constraints

| Constraint | Reason |
|------------|--------|
| Python >= 3.11, <= 3.12 | 3.11+ for performance. 3.13 may have ARM64 ecosystem gaps. RPi OS Bookworm ships 3.11. |
| 64-bit OS required | NCNN and modern numpy require 64-bit. 32-bit RPi OS will not work for this stack. |
| YOLO11n specifically | Larger models (s/m/l/x) will be too slow for real-time on RPi 5 CPU. Nano is the ceiling. |
| OpenCV headless | `opencv-python-headless` not `opencv-python`. The Pi has no display. Headless avoids Qt/GTK dependencies. Ultralytics installs this by default. |

---

## What NOT to Use

| Technology | Why Not | Common Trap |
|------------|---------|-------------|
| Docker on RPi | Adds 200-500MB RAM overhead, complicates camera access (device passthrough), unnecessary for single-service deployment | "Containerize everything" mentality from cloud dev |
| TensorRT | NVIDIA-only. RPi 5 has no NVIDIA GPU. | Guides for Jetson Nano do not apply to Raspberry Pi |
| Coral TPU / Hailo-8L | Hardware accelerator not in project spec. Adds cost and driver complexity. YOLO11n on CPU is fast enough (~15-20 FPS). Revisit only if CPU inference proves too slow. | Premature optimization |
| React/Vue/Angular | Over-engineered for a single dashboard page. Adds Node.js build dependency on or for the Pi. | Frontend developer habits |
| Socket.IO | Adds protocol overhead, requires client library, designed for features (rooms, reconnection fallback to polling) not needed here | Common recommendation in tutorials, but native WebSocket is simpler |
| PostgreSQL/MySQL | Resource-heavy server processes on constrained hardware for a trivially simple data model | Database habit from server-side development |
| Celery / Redis | Task queue is unnecessary. The detection loop IS the task. No need for distributed task processing on a single Pi. | Over-architecture from web development patterns |
| Nginx reverse proxy | Uvicorn serves static files and handles the single-user load directly. Nginx adds config complexity for zero benefit at this scale. | Server deployment habit |

---

## Sources and Confidence Notes

| Claim | Source | Confidence |
|-------|--------|------------|
| YOLO11 is the latest Ultralytics architecture | Ultralytics released YOLO11 in late 2024, documented at docs.ultralytics.com | HIGH -- well-known release, widely covered |
| NCNN is fastest on RPi 5 | Ultralytics official RPi guide benchmarks NCNN as fastest format | HIGH -- official documentation |
| YOLO11n runs ~50-80ms/frame on RPi 5 NCNN | Ultralytics benchmark data for RPi 5 | MEDIUM -- based on training data, exact numbers should be verified on actual hardware |
| FastAPI native WebSocket support | Core Starlette feature, well-documented | HIGH -- established, stable API |
| Cloudflare Tunnel free tier | Cloudflare Zero Trust free tier includes tunnels | MEDIUM -- free tier terms could change, verify current offering |
| RPi OS Bookworm ships Python 3.11 | Debian 12 / Bookworm default Python version | HIGH -- stable release fact |
| NCNN ARM64 wheels available via pip | Ultralytics handles NCNN installation on RPi | MEDIUM -- pip wheel availability can vary, may need build from source |

**Research limitation:** WebSearch, WebFetch, Context7, and Bash tools were unavailable during this research session. All recommendations are based on training data knowledge of this ecosystem through early-to-mid 2025. This is a mature, well-established stack (Ultralytics YOLO + FastAPI + RPi deployment), so training data staleness risk is LOW. However, exact version numbers and benchmark figures should be verified against current documentation before implementation.
