# ૪. Equipment, Calibration, Maintenance, Devices — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/{equipment,device}/**`,
> `frontend/src/app/{equipment,devices}/**`, `services/gxp-api/scripts/seed.py`.

---

## ૪.૧ Equipment Master

| Route | કરે છે |
|---|---|
| `/equipment` | Asset register + KPI dashboard (calibration due/maintenance open/out-of-service); asset create; equipment area create |
| `/equipment/[id]` | Detail: calibration/maintenance/use-log/eligibility tabs — qualify, calibrate, maintain, hold, return-to-service |

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Asset Create | `equipment_asset.create` | Admin, **Equipment Administrator** | ના |
| Area Create | `equipment_area.create` | Admin, Equipment Administrator | ના |
| Qualify | `equipment_asset.qualify` | Admin, Equipment Administrator | ના |
| Calibrate | `equipment_asset.calibrate` | Admin, **Calibration Technician** | ના |
| Maintain | `equipment_asset.maintain` | Admin, **Maintenance Technician** | ના |
| **Hold** | `equipment_asset.hold` | Admin, Operator, QA Reviewer, QA Releaser | **હા** — "Performed", reason required |
| Return to Service | `equipment_asset.return_to_service` | Admin, QA Reviewer, **Engineering Manager** | ના |

**Example:**

| Field | ઉદાહરણ |
|---|---|
| Equipment Code | `FILLER-01` |
| Area | `AREA-GRADE-C` |
| Calibration Due | 6 મહિના પછી |

**ડેમો Logins:** `equipment.admin` (create/qualify), `calibration.tech`, `maintenance.tech`,
`engineering.manager` (return-to-service).

> **નોંધ:** Equipment lifecycle ના ૫ actions માંથી **ફક્ત "Hold" signed છે** — qualify/calibrate/
> maintain/return-to-service RBAC-only.

---

## ૪.૨ Devices

**શું છે:** Serialized device-unit tracking (દા.ત. PFS ના components) — UDI, hold/release status,
lot-level release readiness.

| Route | કરે છે |
|---|---|
| `/devices` | Serial lookup (browsable list ઇરાદાપૂર્વક નથી — નીચે ૪.૪ જુઓ), unit hold, device-lot readiness check, (Admin/Supervisor) lot create + bulk unit create |

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Device Lot / Bulk Units Create | `device.create` | Admin, **Supervisor** | ના |
| Hold Unit | `device.execute` | બ્રોડ operational roles | ના |
| View/Lookup/Readiness | `device.view` | બ્રોડ operational roles | — |

**Example:** Serial `SN-000123` — Device Lot `DVC-LOT-2026-04`.

---

## ૪.૩ ડેમો વોકથ્રુ

**Login:** `equipment.admin` → `calibration.tech` → `admin`(Supervisor demo user ના હોય તો)

1. Equipment create → `FILLER-01`, Area `AREA-GRADE-C`.
2. Qualify → Equipment Administrator.
3. Calibrate → Calibration Technician, "Calibration due" 6 મહિના.
4. Device Lot create → Supervisor (અથવા Admin) → bulk serials `SN-000101` થી `SN-005100`.
5. Hold Equipment → e-signature સાથે, reason "Deviation investigation pending".

---

## ૪.૪ ધ્યાન રાખવા જેવી બાબતો

1. **Equipment lifecycle માં ફક્ત Hold signed છે**, બાકીના actions RBAC-only.
2. **`/devices` પર browsable list નથી — આ deliberate spec boundary છે, bug/gap નથી** (2026-09-19
   ચકાસાયેલ): Document 12 નું પોતાનું ૧૧-API list (`ebmr-edhr/docs/generated/06_API_CATALOGUE.yaml`)
   માં કોઈ `GET /devices/v1/units` (list) operation જ નથી — ફક્ત by-serial lookup
   (`GET .../units/by-serial/{serial}`), unit history, અને lot release-readiness. "Document ના own
   API list ની બહાર endpoint invent ના કરવું" — આ codebase ની throughout followed discipline પ્રમાણે,
   list endpoint ઉમેરવું ખોટું ગણાય.
3. ~~"Hold unit" બટન `canViewDevices` ચેક વાપરે છે, naming imprecise~~ **✅ Fixed** — હવે
   `canExecuteDevice()` (`device.execute`) વાપરે છે, backend ના `device.execute` gate સાથે
   1:1 match (`frontend/src/app/devices/page.tsx`, commit `f7a2899`).
