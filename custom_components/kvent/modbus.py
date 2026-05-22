"""Async Modbus TCP client for Komfovent C4.

No Home Assistant imports — independently testable.
Protocol: Modbus TCP (MBAP + PDU).
  Function 0x03 – Read Holding Registers
  Function 0x06 – Write Single Register

Register addresses are 1-based (as documented in the Komfovent C4 manual).
The PDU uses 0-based addressing, so every address sent on the wire is (addr - 1).
"""
from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass

from .const import SERVICE_BIT_MASK, SETPOINT_TENTHS_MAX

_LOGGER = logging.getLogger(__name__)

# Modbus exception 0x06 = Slave Device Busy (transient; device asks master to retry later).
_BUSY_EXCEPTION = 0x06
_BUSY_RETRIES = 4
_BUSY_BASE_DELAY_S = 0.25

_PROTOCOL_ID = 0x0000
_DEFAULT_UNIT = 1
_FUNC_READ = 0x03
_FUNC_WRITE = 0x06
_CONNECT_TIMEOUT = 10.0
_IO_TIMEOUT = 5.0


@dataclass
class KVentData:
    """Snapshot of all polled register values."""

    power: bool           # REG_STATUS  (1000)
    season: int           # REG_SEASON  (1001)  0=summer, 1=winter
    service: bool         # REG_SERVICE (1007)  binary: bit 14 set ⇒ service required
    speed_manual: int     # REG_SPEED_MANUAL (1100)  commanded 1–3 (table); read-back only
    speed: int            # REG_SPEED        (1101)  0–4 actual level
    mode: int             # REG_MODE         (1102)  0=manual, 1=auto
    supply_temp: float    # REG_SUPPLY_TEMP  (1200)  °C (signed / 10)
    setpoint: float       # REG_SETPOINT     (1201)  °C (signed / 10)
    alarm_stop_flags: int = 0  # REG 1008 — bitmask of active stop conditions
    alarm_stop_code: int = 0   # REG 1009 — most recent stop reason code
    fans_running: bool = True  # REG 1114 — actual fan state (1=operating)


# ──────────────────────────────────────────────────────────────────────────────
# Internal frame helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_read_frame(tid: int, addr: int, count: int, unit: int = _DEFAULT_UNIT) -> bytes:
    """Build Modbus TCP read-holding-registers frame (function 0x03)."""
    pdu = struct.pack(">BHH", _FUNC_READ, addr - 1, count)
    mbap = struct.pack(">HHHB", tid, _PROTOCOL_ID, len(pdu) + 1, unit)
    return mbap + pdu


def _build_write_frame(tid: int, addr: int, value: int, unit: int = _DEFAULT_UNIT) -> bytes:
    """Build Modbus TCP write-single-register frame (function 0x06)."""
    pdu = struct.pack(">BHH", _FUNC_WRITE, addr - 1, value)
    mbap = struct.pack(">HHHB", tid, _PROTOCOL_ID, len(pdu) + 1, unit)
    return mbap + pdu


def _decode_signed16(raw: int) -> float:
    """Two's-complement 16-bit → signed Python int."""
    return float(raw if raw < 0x8000 else raw - 0x10000)


def encode_setpoint_register(celsius: float) -> int:
    """Encode setpoint °C for holding register 1201 (tenths of °C; documented range 0..300)."""
    tenths = int(round(celsius * 10))
    tenths = max(0, min(SETPOINT_TENTHS_MAX, tenths))
    return tenths & 0xFFFF


class ModbusSlaveBusyError(Exception):
    """Raised when the unit responds with exception 0x06 (slave device busy)."""


def _parse_read_exception(addr: int, body: bytes) -> None:
    """Raise if the read response is a Modbus exception PDU."""
    func = body[1]
    if not func & 0x80:
        return
    code = body[2]
    if code == _BUSY_EXCEPTION:
        raise ModbusSlaveBusyError(addr)
    raise OSError(f"Modbus exception code {code:#x} for addr {addr}")


# ──────────────────────────────────────────────────────────────────────────────
# Client
# ──────────────────────────────────────────────────────────────────────────────

class KVentModbusClient:
    """Minimal async Modbus TCP client scoped to the KVent register map."""

    def __init__(self, host: str, port: int = 502) -> None:
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._tid: int = 1
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open TCP connection. Raises OSError / TimeoutError on failure."""
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=_CONNECT_TIMEOUT,
        )
        _LOGGER.debug("KVent: connected to %s:%d", self.host, self.port)

    async def disconnect(self) -> None:
        """Close the TCP connection (idempotent)."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._writer = None
                self._reader = None

    async def _ensure_connected(self) -> None:
        if self._writer is None or self._writer.is_closing():
            await self.connect()

    def _next_tid(self) -> int:
        tid = self._tid
        self._tid = (tid % 65534) + 1
        return tid

    # ── Raw register access ───────────────────────────────────────────────────

    async def _read_registers_unlocked(self, addr: int, count: int) -> list[int]:
        """Single read attempt; caller must hold ``_lock``."""
        await self._ensure_connected()
        tid = self._next_tid()
        frame = _build_read_frame(tid, addr, count)

        assert self._writer is not None  # noqa: S101 (guaranteed by _ensure_connected)
        self._writer.write(frame)
        await self._writer.drain()

        assert self._reader is not None  # noqa: S101
        header = await asyncio.wait_for(self._reader.readexactly(6), timeout=_IO_TIMEOUT)
        resp_tid, _proto, length = struct.unpack(">HHH", header)

        body = await asyncio.wait_for(self._reader.readexactly(length), timeout=_IO_TIMEOUT)
        # Stale / out-of-order frames otherwise silently masquerade as the current
        # response (observed cause of spurious REG_STATUS=0 reads).
        if resp_tid != tid:
            _LOGGER.warning(
                "KVent: modbus TID mismatch on read addr %s: sent=%s got=%s header=%s body=%s",
                addr, tid, resp_tid, header.hex(), body.hex(),
            )
            raise OSError(f"Modbus TID mismatch: sent {tid}, got {resp_tid}")
        # body layout: [unit_id][func][byte_count][data...] or exception: [unit][func|0x80][ex_code]
        _parse_read_exception(addr, body)
        func = body[1]
        if func != _FUNC_READ:
            raise OSError(f"Unexpected function code {func:#x}, expected {_FUNC_READ:#x}")

        byte_count = body[2]
        expected = count * 2
        if byte_count != expected:
            _LOGGER.warning(
                "KVent: modbus byte_count mismatch on read addr %s: expected=%s got=%s body=%s",
                addr, expected, byte_count, body.hex(),
            )
            raise OSError(f"Modbus byte_count mismatch: expected {expected}, got {byte_count}")
        return [
            struct.unpack_from(">H", body, 3 + i * 2)[0]
            for i in range(byte_count // 2)
        ]

    async def read_registers(self, addr: int, count: int) -> list[int]:
        """Read `count` holding registers starting at 1-based `addr`.

        Retries a few times if the unit returns Modbus exception 0x06 (slave device busy).
        """
        last_busy: ModbusSlaveBusyError | None = None
        for attempt in range(_BUSY_RETRIES):
            async with self._lock:
                try:
                    return await self._read_registers_unlocked(addr, count)
                except ModbusSlaveBusyError as err:
                    last_busy = err
            if attempt < _BUSY_RETRIES - 1:
                delay = _BUSY_BASE_DELAY_S * (attempt + 1)
                _LOGGER.debug(
                    "KVent: slave busy at addr %s (attempt %s/%s), retry in %.2fs",
                    addr,
                    attempt + 1,
                    _BUSY_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)
        assert last_busy is not None
        raise OSError(
            f"Modbus slave device busy (exception 0x{_BUSY_EXCEPTION:x}) for addr {addr} "
            f"after {_BUSY_RETRIES} attempts"
        ) from last_busy

    async def write_register(self, addr: int, value: int) -> None:
        """Write a single holding register at 1-based `addr`."""
        async with self._lock:
            await self._ensure_connected()
            tid = self._next_tid()
            frame = _build_write_frame(tid, addr, value)

            assert self._writer is not None  # noqa: S101
            self._writer.write(frame)
            await self._writer.drain()

            assert self._reader is not None  # noqa: S101
            resp = await asyncio.wait_for(self._reader.readexactly(12), timeout=_IO_TIMEOUT)
            resp_tid = struct.unpack(">H", resp[0:2])[0]
            if resp_tid != tid:
                _LOGGER.warning(
                    "KVent: modbus TID mismatch on write addr %s: sent=%s got=%s frame=%s",
                    addr, tid, resp_tid, resp.hex(),
                )
                raise OSError(f"Modbus TID mismatch on write: sent {tid}, got {resp_tid}")
            func = resp[7]
            if func & 0x80:
                raise OSError(f"Modbus write exception code {resp[8]:#x} for addr {addr}")
            if func != _FUNC_WRITE:
                raise OSError(f"Unexpected write response func {func:#x}")

    # ── High-level poll ───────────────────────────────────────────────────────

    async def async_read_all(self) -> KVentData:
        """Read the full KVent register snapshot in five contiguous blocks."""
        # Block 1 – 1000..1001 (status, season)
        b1 = await self.read_registers(1000, 2)
        # Block 2 – 1007..1009 (service warnings, alarm stop flags, alarm stop code)
        b2 = await self.read_registers(1007, 3)
        # Block 3 – 1100..1102 (speed_manual, speed, mode)
        b3 = await self.read_registers(1100, 3)
        # Block 4 – 1114       (actual AHU fans status, independent of REG_STATUS)
        b4 = await self.read_registers(1114, 1)
        # Block 5 – 1200..1201 (supply_temp, setpoint)
        b5 = await self.read_registers(1200, 2)

        return KVentData(
            power=b1[0] == 1,
            season=b1[1],
            service=bool(b2[0] & SERVICE_BIT_MASK),
            speed_manual=b3[0],
            speed=b3[1],
            mode=b3[2],
            supply_temp=_decode_signed16(b5[0]) / 10.0,
            setpoint=_decode_signed16(b5[1]) / 10.0,
            alarm_stop_flags=b2[1],
            alarm_stop_code=b2[2],
            fans_running=b4[0] == 1,
        )
