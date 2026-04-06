"""Constants for the KVent (Komfovent C4) integration."""

DOMAIN = "kvent"

# Integration version (also mirrored in manifest.json)
INTEGRATION_VERSION = "0.0.12"

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 5

# ──────────────────────────────────────────────
# Modbus register addresses (1-based, as in Komfovent C4 manual)
# ──────────────────────────────────────────────
REG_STATUS = 1000        # R/W  0=off, 1=on
REG_SEASON = 1001        # R/W  0=summer, 1=winter
REG_SERVICE = 1007       # R    bitfield – bit 14 (0x4000) = service required
REG_SPEED_MANUAL = 1100  # R/W  0=standby, 1–3=levels, 4=boost (manual mode target)
REG_SPEED = 1101         # R    actual current speed (same encoding)
REG_MODE = 1102          # R/W  0=manual, 1=auto
REG_SUPPLY_TEMP = 1200   # R    signed int16 / 10 → °C
REG_SETPOINT = 1201      # R/W  signed int16 / 10 → °C

# Service register bitmask
SERVICE_BIT_MASK = 0x4000  # bit 14

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
