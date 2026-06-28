"""Constants for the KVent (Komfovent C4) integration."""

DOMAIN = "kvent"

# Integration version (also mirrored in manifest.json)
INTEGRATION_VERSION = "0.0.26"

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 5

# Consecutive failed polls tolerated before entities go `unavailable`. A single
# transient read/connect timeout otherwise flaps every entity to unavailable for
# one cycle; the recovery edge (unavailable→on) then fires users' "turned on"
# automations even though the C4 never changed state. We carry the last-good
# snapshot forward for up to this many consecutive failures (~grace × scan_interval
# seconds) and only surface UpdateFailed once the outage is sustained.
POLL_FAILURE_GRACE = 3

# ──────────────────────────────────────────────
# Modbus register addresses (1-based, as in Komfovent C4 manual)
# ──────────────────────────────────────────────
REG_STATUS = 1000        # R/W  0=off, 1=on
REG_SEASON = 1001        # R/W  0=summer, 1=winter
REG_SERVICE = 1007       # R    alarm warnings (binary) — bit 14 = 0x4000 ⇒ service required
REG_ALARM_STOP_FLAGS = 1008  # R  binary stop-condition bits (sensor / heater / frost / rotor / air-temp)
REG_ALARM_STOP_CODE = 1009   # R  integer stop reason code (0 = no stop)
REG_SPEED_MANUAL = 1100  # R/W  manual level 1–3 only (per table); 0/4 appear on 1101
REG_SPEED = 1101         # R    actual level 0–4 (standby / 1–3 / override)
REG_MODE = 1102          # R/W  0=manual, 1=auto
REG_FANS_STATUS = 1114   # R    1=operating, 0=stopped (independent of REG_STATUS)
REG_SUPPLY_TEMP = 1200   # R    signed int16 / 10 → °C
REG_SETPOINT = 1201      # R/W  signed int16 / 10 → °C; doc range 0..300 (0–30 °C)
REG_OVR_ENABLE = 1111    # R/W  OVR enable — 1 = enabled (Boost preset)
REG_OVR_TIME = 1112      # R/W  OVR duration 1..90 minutes

# 1007 is typed “binary” in the manual; bit 14 encodes service required
SERVICE_BIT_MASK = 0x4000

# Default OVR duration when activating Boost (register 1112, minutes)
DEFAULT_OVR_MINUTES = 30

# Setpoint on wire: tenths of °C, documented 0..300 (0–30 °C)
SETPOINT_TENTHS_MAX = 300

# Supply sensor B1 documented operating range (°C). Used by diagnostic logging
# when a decoded REG 1200 reading falls outside; values outside are wire/parse glitches.
SUPPLY_TEMP_MIN_C = -30.0
SUPPLY_TEMP_MAX_C = 75.0

# Physically implausible supply-air change between two consecutive 5 s polls.
# Used by the coordinator to suppress in-range glitches (e.g. a single sample
# of 0.0 °C amid steady 25 °C readings).
SUPPLY_TEMP_MAX_JUMP_C = 5.0

# ──────────────────────────────────────────────
# Mode values
# ──────────────────────────────────────────────
MODE_MANUAL = 0
MODE_AUTO = 1

# Season values
SEASON_SUMMER = 0
SEASON_WINTER = 1

# Speed / level values
SPEED_STANDBY = 0
SPEED_LEVEL_1 = 1
SPEED_LEVEL_2 = 2
SPEED_LEVEL_3 = 3
SPEED_BOOST = 4

SPEED_MAP: dict[int, str] = {
    SPEED_STANDBY: "Standby",
    SPEED_LEVEL_1: "Level 1",
    SPEED_LEVEL_2: "Level 2",
    SPEED_LEVEL_3: "Level 3",
    SPEED_BOOST: "Boost",
}

# ──────────────────────────────────────────────
# Fan preset mode labels (used by fan.py & const consumers)
# ──────────────────────────────────────────────
PRESET_AUTO = "Auto"
PRESET_SPEED_1 = "Speed 1"
PRESET_SPEED_2 = "Speed 2"
PRESET_SPEED_3 = "Speed 3"
PRESET_BOOST = "Boost"
PRESET_STANDBY = "Standby"

# Climate entity only: shown in Preset UI when REG_SERVICE reports maintenance.
PRESET_SERVICE_ALERT = "service_alert"

PRESET_MODES: list[str] = [
    PRESET_AUTO,
    PRESET_SPEED_1,
    PRESET_SPEED_2,
    PRESET_SPEED_3,
    PRESET_BOOST,
    PRESET_STANDBY,
]

# Map preset label → speed_manual register value (manual presets only)
PRESET_TO_SPEED: dict[str, int] = {
    PRESET_SPEED_1: SPEED_LEVEL_1,
    PRESET_SPEED_2: SPEED_LEVEL_2,
    PRESET_SPEED_3: SPEED_LEVEL_3,
    PRESET_BOOST: SPEED_BOOST,
    PRESET_STANDBY: SPEED_STANDBY,
}

# Reverse map: (REG_MODE, speed_manual) → preset label (manual uses speed_manual; auto key unused).
FAN_STATE_TO_PRESET: dict[tuple[int, int], str] = {
    (MODE_AUTO, -1): PRESET_AUTO,
    (MODE_MANUAL, SPEED_STANDBY): PRESET_STANDBY,
    (MODE_MANUAL, SPEED_LEVEL_1): PRESET_SPEED_1,
    (MODE_MANUAL, SPEED_LEVEL_2): PRESET_SPEED_2,
    (MODE_MANUAL, SPEED_LEVEL_3): PRESET_SPEED_3,
    (MODE_MANUAL, SPEED_BOOST): PRESET_BOOST,
}

# ──────────────────────────────────────────────
# Season select options
# ──────────────────────────────────────────────
SEASON_OPTION_SUMMER = "Summer"
SEASON_OPTION_WINTER = "Winter"
SEASON_OPTIONS: list[str] = [SEASON_OPTION_SUMMER, SEASON_OPTION_WINTER]

SEASON_OPTION_TO_VALUE: dict[str, int] = {
    SEASON_OPTION_SUMMER: SEASON_SUMMER,
    SEASON_OPTION_WINTER: SEASON_WINTER,
}

SEASON_VALUE_TO_OPTION: dict[int, str] = {
    SEASON_SUMMER: SEASON_OPTION_SUMMER,
    SEASON_WINTER: SEASON_OPTION_WINTER,
}
