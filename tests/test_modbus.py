"""Tests for the pure Modbus TCP layer (no HA imports)."""
from __future__ import annotations

import asyncio
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kvent.modbus import (
    KVentData,
    KVentModbusClient,
    _build_read_frame,
    _build_write_frame,
    _decode_signed16,
    encode_setpoint_register,
)


# ──────────────────────────────────────────────────────────────────────────────
# Frame builders
# ──────────────────────────────────────────────────────────────────────────────

def test_build_read_frame_address_is_zero_based():
    """Register address 1000 (1-based) must become 999 (0-based) on the wire."""
    frame = _build_read_frame(1, 1000, 2)
    # MBAP: TID(2) + PROTO(2) + LEN(2) + UNIT(1) = 7 bytes; then PDU func(1)+addr(2)+count(2)
    addr_hi, addr_lo = frame[8], frame[9]
    wire_addr = (addr_hi << 8) | addr_lo
    assert wire_addr == 999, f"expected 999, got {wire_addr}"


def test_build_write_frame_address_is_zero_based():
    """Register address 1100 (1-based) must become 1099 (0-based) on the wire."""
    frame = _build_write_frame(1, 1100, 0x0002)
    addr_hi, addr_lo = frame[8], frame[9]
    wire_addr = (addr_hi << 8) | addr_lo
    assert wire_addr == 1099, f"expected 1099, got {wire_addr}"


def test_build_read_frame_length():
    """MBAP length field must equal PDU length + 1 (unit id)."""
    frame = _build_read_frame(42, 1000, 3)
    mbap_length = struct.unpack(">H", frame[4:6])[0]
    # PDU = func(1) + addr(2) + count(2) = 5 bytes; +1 for unit_id
    assert mbap_length == 6


def test_build_write_frame_value():
    """Written value bytes must appear at positions 10–11 in the frame."""
    frame = _build_write_frame(1, 1100, 0x0003)
    val_hi, val_lo = frame[10], frame[11]
    assert (val_hi << 8) | val_lo == 3


# ──────────────────────────────────────────────────────────────────────────────
# Signed decode helper
# ──────────────────────────────────────────────────────────────────────────────

def test_decode_signed16_positive():
    assert _decode_signed16(0x00C8) == 200.0   # 200 → 20.0 °C when / 10

def test_decode_signed16_zero():
    assert _decode_signed16(0x0000) == 0.0

def test_decode_signed16_negative():
    # -50 in two's complement 16-bit = 0xFFCE
    assert _decode_signed16(0xFFCE) == -50.0


def test_encode_setpoint_round_trip():
    assert encode_setpoint_register(20.5) == 205
    assert encode_setpoint_register(0.0) == 0


def test_encode_setpoint_clamps_to_documented_range():
    """REG 1201 documented 0..300 tenths (0–30 °C); writes must not exceed."""
    assert encode_setpoint_register(35.0) == 300
    assert encode_setpoint_register(-2.5) == 0
    assert encode_setpoint_register(25.0) == 250


# ──────────────────────────────────────────────────────────────────────────────
# KVentData dataclass
# ──────────────────────────────────────────────────────────────────────────────

def test_kvent_data_fields():
    d = KVentData(
        power=True,
        season=1,
        service=False,
        speed_manual=2,
        speed=2,
        mode=0,
        supply_temp=18.5,
        setpoint=20.0,
    )
    assert d.power is True
    assert d.supply_temp == 18.5
    assert d.setpoint == 20.0
    assert d.service is False


# ──────────────────────────────────────────────────────────────────────────────
# KVentModbusClient – high-level read_all parsing
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_read_all_parses_blocks_correctly():
    """async_read_all must correctly combine five read_registers calls."""
    client = KVentModbusClient("127.0.0.1", 502)

    async def fake_read(addr, count):
        if addr == 1000:
            return [1, 1]                # power=ON, season=WINTER
        if addr == 1007:
            return [0x4000, 0x0020, 5]   # service bit 14; stop flags bit 5 (frost); stop code 5
        if addr == 1100:
            return [2, 3, 1]             # speed_manual=2, speed=3, mode=AUTO
        if addr == 1114:
            return [1]                   # fans operating
        if addr == 1200:
            return [0x00C8, 0x00FA]      # supply=200→20.0, setpoint=250→25.0
        return []

    client.read_registers = fake_read

    data = await client.async_read_all()

    assert data.power is True
    assert data.season == 1
    assert data.service is True
    assert data.speed_manual == 2
    assert data.speed == 3
    assert data.mode == 1
    assert data.supply_temp == pytest.approx(20.0)
    assert data.setpoint == pytest.approx(25.0)
    assert data.alarm_stop_flags == 0x0020
    assert data.alarm_stop_code == 5
    assert data.fans_running is True


@pytest.mark.asyncio
async def test_async_read_all_negative_temperature():
    """Signed temperatures below 0 °C must decode correctly."""
    client = KVentModbusClient("127.0.0.1", 502)

    async def fake_read(addr, count):
        if addr == 1000:
            return [0, 0]
        if addr == 1007:
            return [0, 0, 0]
        if addr == 1100:
            return [0, 0, 0]
        if addr == 1114:
            return [0]
        if addr == 1200:
            # -50 = 0xFFCE, -30 = 0xFFE2 (raw); /10 → -5.0, -3.0 °C
            return [0xFFCE, 0xFFE2]
        return []

    client.read_registers = fake_read
    data = await client.async_read_all()

    assert data.supply_temp == pytest.approx(-5.0)
    assert data.setpoint == pytest.approx(-3.0)
    assert data.fans_running is False
