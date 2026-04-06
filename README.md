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
| Current Speed | `sensor` | REG 1101 — Standby / Level 1–3 / Boost |
| Season | `select` | REG 1001 — Summer / Winter |
| Service Required | `binary_sensor` | REG 1007 bit 14 — PROBLEM class |

No external Python dependencies — pure `asyncio` socket I/O.

---

## GitHub repository settings (HACS / validation)

HACS’ **topics** check reads your repository metadata on GitHub (not files in this repo).  
In the repo **Settings → General → Topics**, add for example:

`home-assistant`, `hacs-custom`, `custom-integration`, `komfovent`, `modbus`, `ventilation`

Also ensure the repo has a **short description** and **Issues** enabled (other HACS checks).

**Public repository:** HACS and `hacs/action` load `hacs.json` and integration `manifest.json` from
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
| Polling interval | `15` s | How often registers are read |

---

## Fan Preset Modes

| Preset | Behaviour |
|---|---|
| **Auto** | Sets mode register (1102) to `1` — unit controls speed automatically |
| **Speed 1** | Manual mode, speed_manual (1100) = 1 |
| **Speed 2** | Manual mode, speed_manual (1100) = 2 |
| **Speed 3** | Manual mode, speed_manual (1100) = 3 |
| **Boost** | Manual mode, speed_manual (1100) = 4 |
| **Standby** | Manual mode, speed_manual (1100) = 0 |

Selecting any preset while the unit is off will power it on first.

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
| 1007 | Service flags | R | bit 14 = service required |
| 1100 | Manual speed | R/W | 0=standby, 1–3=levels, 4=boost |
| 1101 | Actual speed | R | same encoding |
| 1102 | Mode | R/W | 0=manual, 1=auto |
| 1200 | Supply temp | R | signed int16 ÷ 10 → °C |
| 1201 | Setpoint temp | R | signed int16 ÷ 10 → °C |

All addresses are 1-based (as in the C4 manual); frames send `addr − 1`.

---

## Reforged from FIBARO HC3 Quick App

Original QA: `KVent.fqa` (Komfovent C4, Modbus TCP, Lua).
Reforge playbook: `HC3-QA-to-HA-Reforge-Playbook.md`.
