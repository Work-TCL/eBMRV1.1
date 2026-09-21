# ૫. Line Clearance — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/equipment/cleaning_router.py`,
> `frontend/src/app/line-clearance/`, `services/gxp-api/scripts/seed.py`.

---

## ૫.૧ Line Clearance એટલે શું?

**Equipment Area** (batch/equipment નહીં, area) સાથે જોડાયેલ ચેક — પાછલા batch ની ઓળખ/material ને
area માંથી સંપૂર્ણપણે clear કર્યા વગર આગલો batch શરૂ ના થઈ શકે. Previous/next batch reference (traceability
માટે) optional રાખી શકાય. **DDCP readiness check** area ના real clearance status ને lookup કરે છે
(`cleaning_commands.get_area_line_clearance_status()`) — line clearance ના થાય ત્યાં સુધી DDCP blocked
રહી શકે.

> ⚠️ **સુધારો (2026-09-19):** આ doc ની જૂની આવૃત્તિ કહેતી હતી કે "Packaging પણ" area clearance status
> lookup કરે છે — એ ખોટું છે. **Packaging નું પોતાનું, અલગ, self-attested `line_clearance_completed`
> flag છે** (`packaging_run` ટેબલ પર) જે operator જાતે "true" set કરે છે — તે ક્યારેય real
> `LineClearance`/`EquipmentArea` status query નથી કરતું (`packaging/commands.py`). એટલે real line
> clearance ના થયું હોય તો પણ Packaging run આગળ વધી શકે — genuine integration gap, ડોક્યુમેન્ટ ૦૮ ના
> Packaging row માં પણ નોંધેલ.

## ૫.૨ Checklist Types

| Type | ઓટો-ચેક થાય છે? |
|---|---|
| `material` | ના — manual verify |
| `label` | ના — manual verify |
| `equipment` | **હા** — listed equipment asset qualified + calibrated + clean ના હોય તો "Pass" complete જ ના થાય |

---

## ૫.૩ Frontend Route

| Route | કરે છે |
|---|---|
| `/line-clearance` | List, Start Clearance (area, prev/next batch, checklist version, items, critical flag), Complete (pass/fail + optional expiry + reason) |

---

## ૫.૪ Permission મેટ્રિક્સ

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Start (Create) | `line_clearance.create` | broad operational roles | ના |
| **Complete** | `line_clearance.complete` | Admin, Operator, Supervisor, **Sanitation Operator** | **હા** — "Performed" |

**Demo Login:** `sanitation.operator` / `ChangeMe123!`

**Critical flag:** clearance item "critical" mark કરેલ હોય તો fail થાય ત્યારે reason ફરજિયાત.

---

## ૫.૫ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `sanitation.operator`

| Field | ઉદાહરણ |
|---|---|
| Area | `AREA-GRADE-C` |
| Previous Batch | `MJ-2026-0141` |
| Next Batch | `MJ-2026-0142` |
| Checklist Items | Material removed (✓), Label removed (✓), Filler-01 equipment clean+calibrated (✓ auto-check) |
| Result | `Pass` |
| Expiry | 4 કલાક |

Complete → e-signature (password re-entry) → Area હવે "cleared" status માં → DDCP/Packaging readiness
check હવે આ area ને eligible ગણશે.

---

## ૫.૬ ધ્યાન રાખવા જેવી બાબતો

1. **Equipment items જ auto-verify થાય છે** — material/label items પર માનવ verification પર આધાર
   રાખવો પડે.
2. Line Clearance area-level છે, ચોક્કસ batch-level નથી — same area પર multiple batch વચ્ચે clearance
   history traceable રહે છે prev/next batch reference થી.
3. **Packaging, real line clearance status સાથે wired નથી** (ઉપર ૫.૧ ની 2026-09-19 સુધારા-નોંધ જુઓ) —
   `packaging_run.line_clearance_completed` self-attested flag છે, `LineClearance`/`EquipmentArea` ને
   query નથી કરતું. મૂળ કારણ: `PackagingRun.line_ref` free-text field છે, `EquipmentArea` ને real FK
   નથી (SG-050/055) — સાચું fix schema change (migration) માંગે, honestly ખુલ્લું નોંધેલ.
