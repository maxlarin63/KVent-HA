# Komfovent C4 — Modbus registers (OCR from manufacturer tables)

Transcription of the **“Modbus registers of C4 controller”** and **Schedule** tables for cross-check with this integration. Register numbers are **1-based** as in the documentation; Modbus PDU addressing typically uses **register − 1**.

**KVent integration (1007):** The table lists **binary** type and symbolic codes such as “14-Service”. The integration treats **service required** as **bit 14 set** (`value & 0x4000`), consistent with a bitwise interpretation of that binary field.

---

## General

| Register | Description | Data type | Access | Data range / values |
|:--:|---|---|:---:|---|
| 1000 | C4 Start/Stop | integer | R/W | 1-Start, 0-Stop |
| 1001 | Season | integer | R/W | 1-Winter, 0-Summer |
| 1002 | Time | 2× char | R/W | e.g. 8:05 → 0x0805 |
| 1003 | Day of the week | integer | R/W | 1-Mon … 7-Sun |
| 1004 | Month-day | 2× char | R/W | e.g. 9 May → 0x0509 |
| 1005 | Year | integer | R/W | *(range not shown on source table)* |
| 1006 | Modbus address | integer | R/W | 1..100 |
| 1007 | Alarm status (warnings) | binary | R | 14-Service, 13-Heater off, 11-Rotor stop |
| 1008 | Alarm status (stop flags) | binary | R | 1-Supply sensor B1; 2-Heater overheating; 3-Water temp low; 4-Rotor stop; 5-Frost possibility; 6-Air temp high; 7-Air temp low |
| 1009 | Alarm status (stop code) | integer | R | 3-Rotor stop; 4-Heater overheating; 9-Supply sensor B1; 19-Air temp low; 20-Air temp high; 27-Water temp low; 28-Frost possibility |
| 1010 | Recuperator level | integer | R | 0..100% |
| 1011 | Electric heater level | integer | R | 0..100% |
| 1012 | Water heating level | integer | R | 0..100% |
| 1013 | Water cooling level | integer | R | 0..100% |

---

## Ventilation

| Register | Description | Data type | Access | Data range / values |
|:--:|---|---|:---:|---|
| 1100 | Ventilation level (manual) | integer | R/W | 1..3 |
| 1101 | Ventilation level (current) | integer | R | 0..4 |
| 1102 | Mode (Auto/Manual) | integer | R/W | 0-Manual, 1-Auto |
| 1103 | Intake ventilation intensity level 1 (EC) | integer | R/W | 20..100 / 0 |
| 1104 | Intake ventilation intensity level 2 (EC/AC) | integer | R/W | 20..100 / 0..2 |
| 1105 | Intake ventilation intensity level 3 (EC) | integer | R/W | 20..100 / 0 |
| 1106 | Intake ventilation intensity level 4 (EC) | integer | R/W | 20..100 / 0 |
| 1107 | Exhaust ventilation intensity level 1 (EC) | integer | R/W | 20..100 / 0 |
| 1108 | Exhaust ventilation intensity level 2 (EC/AC) | integer | R/W | 20..100 / 0..2 |
| 1109 | Exhaust ventilation intensity level 3 (EC) | integer | R/W | 20..100 / 0 |
| 1110 | Exhaust ventilation intensity level 4 (EC) | integer | R/W | 20..100 / 0 |
| 1111 | "OVR" enable | integer | R/W | 1 = OVR enabled |
| 1112 | "OVR" time | integer | R/W | 1..90 |
| 1113 | "OVR" time (current) | integer | R | 0..90 |
| 1114 | AHU fans status | binary | R | 1-Operating, 0-Stopped |
| 1115 | Supply fan level (current) | integer | R | 0..100 |
| 1116 | Exhaust fan level (current) | integer | R | 0..100 |

---

## Temperature

| Register | Description | Data type | Access | Data range / values |
|:--:|---|---|:---:|---|
| 1200 | Supply air temp, °C | integer | R | −30..75 (10× °C, e.g. 25.0°C → 250) |
| 1201 | Setpoint temp, °C | integer | R/W | 0..300 (10× °C, e.g. 25.0°C → 250) |
| 1202 | Temp. correction, °C | integer | R/W | −90..+90 (10× °C, e.g. +5°C → 50) |
| 1203 | Temp. correction start time | 2× char | R/W | e.g. 8:05 → 0x0805 |
| 1204 | Temp. correction stop time | 2× char | R/W | e.g. 8:05 → 0x0805 |
| 1205 | Water temp, °C | integer | R | −10..110 (10× °C, e.g. 25.0°C → 250) |

---

## Schedule — times (1300–1341)

**Data type:** 2× char · **Access:** R/W · **Range (per source table):** 0x0000..0x1800 (0:00..24:00)

| Reg | Description | Reg | Description |
|:--:|---|:--:|---|
| 1300 | Mo1 start | 1321 | Th2 stop |
| 1301 | Mo1 stop | 1322 | Th3 start |
| 1302 | Mo2 start | 1323 | Th3 stop |
| 1303 | Mo2 stop | 1324 | Fr1 start |
| 1304 | Mo3 start | 1325 | Fr1 stop |
| 1305 | Mo3 stop | 1326 | Fr2 start |
| 1306 | Tu1 start | 1327 | Fr2 stop |
| 1307 | Tu1 stop | 1328 | Fr3 start |
| 1308 | Tu2 start | 1329 | Fr3 stop |
| 1309 | Tu2 stop | 1330 | Sa1 start |
| 1310 | Tu3 start | 1331 | Sa1 stop |
| 1311 | Tu3 stop | 1332 | Sa2 start |
| 1312 | We1 start | 1333 | Sa2 stop |
| 1313 | We1 stop | 1334 | Sa3 start |
| 1314 | We2 start | 1335 | Sa3 stop |
| 1315 | We2 stop | 1336 | Su1 start |
| 1316 | We3 start | 1337 | Su1 stop |
| 1317 | We3 stop | 1338 | Su2 start |
| 1318 | Th1 start | 1339 | Su2 stop |
| 1319 | Th1 stop | 1340 | Su3 start |
| 1320 | Th2 start | 1341 | Su3 stop |

---

## Schedule — ventilation levels (1342–1362)

**Data type:** integer · **Access:** R/W · **Range:** 0..3

| Reg | Description | Reg | Description |
|:--:|---|:--:|---|
| 1342 | Mo1 ventilation level | 1353 | Th3 ventilation level |
| 1343 | Mo2 ventilation level | 1354 | Fr1 ventilation level |
| 1344 | Mo3 ventilation level | 1355 | Fr2 ventilation level |
| 1345 | Tu1 ventilation level | 1356 | Fr3 ventilation level |
| 1346 | Tu2 ventilation level | 1357 | Sa1 ventilation level |
| 1347 | Tu3 ventilation level | 1358 | Sa2 ventilation level |
| 1348 | We1 ventilation level | 1359 | Sa3 ventilation level |
| 1349 | We2 ventilation level | 1360 | Su1 ventilation level |
| 1350 | We3 ventilation level | 1361 | Su2 ventilation level |
| 1351 | Th1 ventilation level | 1362 | Su3 ventilation level |
| 1352 | Th2 ventilation level | | |
