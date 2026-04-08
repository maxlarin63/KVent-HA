# KVent — Home Assistant Integration for Komfovent C4

A Home Assistant custom component for **Komfovent C4** ventilation units (HRV/ERV)
communicating over **Modbus TCP**.

---

## Features

| Entity | Type | Description |
|---|---|---|
| Komfovent C4 | `fan` | Power on/off + preset modes (Auto / Speed 1–3 / Boost / Standby) |
| Supply Air Temperature | `sensor` | REG 1200 — signed int16 / 10 → °C |
| Setpoint Temperature | `sensor` | REG 1201 — signed int16 / 10 → °C |
| Current Speed | `sensor` | REG 1101 — Standby / Level 1–3 / Override |
| Season | `select` | REG 1001 — Summer / Winter |
| Service Required | `binary_sensor` | REG 1007 — binary; bit **14** (`0x4000`) = service required |

No external Python dependencies — pure `asyncio` socket I/O.

---

## GitHub repository settings (HACS / validation)

HACS’ **topics** check reads your repository metadata on GitHub (not files in this repo).  
In the repo **Settings → General → Topics**, add for example:

`home-assistant`, `hacs-custom`, `custom-integration`, `komfovent`, `modbus`, `ventilation`

Also ensure the repo has a **short description** and **Issues** enabled (other HACS checks).

**Public repository:** HACS and `hacs/action` load `hacs.json` and `manifest.json` from
public `raw.githubusercontent.com` URLs. On a **private** repo those requests return 404, so validation
often reports an invalid `hacs.json` and `integration_manifest … got None` even when the files are
committed. The integration must stay **public** for HACS users; use a public fork if you need private
collaboration elsewhere.

---

## Installation

### HACS (recommended)
1. Add this repo as a custom HACS integration repository.
2. Install **KVent (Komfovent C4)**.
3. Restart Home Assistant.

### Manual
Copy `custom_components/kvent/` to your HA `config/custom_components/` directory,
then restart Home Assistant.

---

## Configuration

Go to **Settings → Devices & Services → Add Integration → KVent**.

| Field | Default | Description |
|---|---|---|
| IP Address | — | LAN address of the C4 unit |
| Port | `502` | Modbus TCP port |
| Polling interval | `5` s | How often registers are read (configurable 5–3600 s) |

---

## Fan Preset Modes

| Preset | Behaviour |
|---|---|
| **Auto** | REG 1102 = `1` — schedule / auto ventilation |
| **Speed 1–3** | REG 1102 = manual, REG **1100** = `1`..`3` (per Modbus table) |
| **Boost** | Manual mode + **OVR**: REG **1111** = `1`, REG **1112** = `30` (minutes, default) |
| **Standby** | REG **1000** = `0` (C4 stop) |

Presets and the fan UI use **REG 1101** (actual level) for the current speed: the unit can show **0** or **4** there when external logic or OVR applies, even though **1100** only accepts **1..3** for manual commands.

Selecting Speed / Auto / Boost while the unit is off powers it on first. **Standby** stops the AHU (same as fan off).

---

## Development

### One-time setup (Windows)

```powershell
cd kvent-ha
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pytest pytest-asyncio pytest-homeassistant-custom-component ruff

copy .env.ha.example .env.ha
# Edit .env.ha — set HA_HOST and HA_USER
```

### Daily loop

```
Edit in Cursor  →  Run Task: Deploy to HA  →  HA Quick Restart  →  verify
```

### Deploy tasks (VS Code / Cursor task runner)

| Task | Description |
|---|---|
| Deploy to HA (rsync / WSL) | rsync over SSH via WSL |
| Deploy to HA (scp, no WSL) | scp directly from PowerShell |
| Run Tests | pytest |
| Lint (ruff) | ruff check |
| Clean | remove `__pycache__`, `.pyc` |

### Run tests

```bash
pytest --tb=short
```

---

## Register Reference (Komfovent C4)

| Address | Name | R/W | Encoding |
|---|---|---|---|
| 1000 | Power status | R/W | 0=off, 1=on |
| 1001 | Season | R/W | 0=summer, 1=winter |
| 1007 | Alarm status (warnings) | R | binary; bit **14** (`0x4000`) = service required |
| 1100 | Manual ventilation level | R/W | **1..3** (commanded); actual **0..4** on **1101** |
| 1101 | Ventilation level (current) | R | 0..4 (standby / levels / override) |
| 1102 | Mode | R/W | 0=manual, 1=auto |
| 1111 | OVR enable | R/W | 1 = enabled (used for Boost preset) |
| 1112 | OVR time | R/W | 1..90 minutes |
| 1200 | Supply temp | R | signed int16 ÷ 10 → °C |
| 1201 | Setpoint temp | R/W | int16 ÷ 10 → °C; documented **0..30 °C** (0..300 tenths) |

All addresses are 1-based (as in the C4 manual); frames send `addr − 1`.

Detailed OCR of the manufacturer tables: `docs/komfovent_c4_modbus_ocr.md`.

---

## Reforged from FIBARO HC3 Quick App

Original QA: `KVent.fqa` (Komfovent C4, Modbus TCP, Lua).
Reforge playbook: `HC3-QA-to-HA-Reforge-Playbook.md`.
