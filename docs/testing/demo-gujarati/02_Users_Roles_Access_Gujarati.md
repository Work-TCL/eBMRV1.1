# ૨. Users, Roles અને Access Review — Gujarati Demo Guide

> Source: `frontend/src/app/admin/users/`, `frontend/src/app/admin/roles/`,
> `frontend/src/app/admin/access-review/`, backend `services/gxp-api/app/modules/iam/`,
> `services/gxp-api/scripts/seed.py`.

---

## ૨.૧ આ મોડ્યુલ શું છે?

- **User** = સિસ્ટમમાં login કરી શકતું એક account (username, email, full name, password, active/inactive
  status).
- **Role** = permissions નો એક સમૂહ (દા.ત. "QA Releaser" role પાસે batch release કરવાની permission છે).
- **User-Site-Role assignment** = "આ user, આ specific site પર, આ role ધરાવે છે." એક user ને એક site પર
  multiple roles પણ મળી શકે, અને અલગ-અલગ sites પર અલગ-અલગ roles પણ મળી શકે.
- **Access Review** = live રિપોર્ટ — કોણ, ક્યાં, કયો role ધરાવે છે — વત્તા "જો હું આ action કરવાની કોશિશ
  કરું તો સિસ્ટમ ALLOW કરશે કે DENY?" એ live ચકાસવાનું ટૂલ.

---

## ૨.૨ કુલ ૩૬ Roles — શું માટે છે (સિસ્ટમમાં પહેલેથી seed થયેલ)

| Role | કામ શું છે | Demo Login છે? |
|---|---|---|
| Admin | બધું જ કરી શકે — બ્રેક-ગ્લાસ સુપરયુઝર; `platform.administer` ધરાવતો એકમાત્ર role | `admin` |
| Operator | શોપ-ફ્લોર પર batch/step execution, dispensing, cleaning | `operator1` |
| Supervisor | batch issue, step-start authorize, deviation triage | **નથી** |
| QA Reviewer | પૂરા થયેલા batch/deviation/CAPA વગેરે રિવ્યુ કરે | `qa.reviewer` |
| QA Releaser | batch/product/recipe release, deviation close, change approve | `qa.releaser` |
| QC Reviewer | લેબ: material lot disposition, OOS/OOT review | `qc.reviewer` |
| Equipment Administrator | Equipment/area બનાવવા, qualify કરવા | `equipment.admin` |
| Engineering Manager | Equipment ને service માં પાછું લાવવું | `engineering.manager` |
| Calibration Technician | Calibration કરવું | `calibration.tech` |
| Maintenance Technician | Maintenance કરવું | `maintenance.tech` |
| Sanitation Operator | Cleaning execution, line clearance | `sanitation.operator` |
| EM Technician | Environmental monitoring પ્રોગ્રામ/સેમ્પલ સેટઅપ | `em.technician` |
| Microbiology Analyst | EM સેમ્પલ result રેકોર્ડ | `microbiology.analyst` |
| Sterilization Operator | Sterilization/sterile-filter cycle ચલાવે | `sterilization.operator` |
| Aseptic Operator | Aseptic fill operation/intervention કરે | `aseptic.operator` |
| Aseptic Supervisor | Aseptic operation start authorize કરે | `aseptic.supervisor` |
| Process Engineer | Product/material-spec/recipe author કરે (release નહીં) | `process.engineer` |
| Integration Administrator | ERP/edge integration gateway admin | `integration.admin` |
| DDCP Engineer | DDCP device-combination profile author/release કરે | `ddcp.engineer` |
| DDCP Operator | DDCP handoff/fill/assembly/verify/release execute કરે | `ddcp.operator`, `ddcp.operator2` |
| Postmarket Safety Reviewer | Safety case intake/classify/assess | **નથી** |
| Postmarket Regulatory Affairs | Regulatory report submission | **નથી** |
| Security Architect | Threat-model authoring, control mapping, risk calc | `security.architect` |
| Security Risk Approver | Accepts residual risk, approves exceptions (independent of requester) | `security.risk.approver` |
| Security Admin | IdP/session/service-identity/secret/certificate/incident ops | `security.admin` |
| Platform Admin | JIT/break-glass privileged access requester/executor | `platform.admin` |
| Vendor Support Engineer | Read-only privileged support sessions | `vendor.support` |

> **2026-09-18 ઉમેરો:** ઉપરના ૫ security roles માટે હવે demo users seed થયેલ છે (`scripts/sync_demo_
> users.py`) — અગાઉ role/permission તરીકે અસ્તિત્વમાં હતા પણ કોઈ login નહોતું.

> ડેમો માટે ઉપલબ્ધ **૨૫ demo users** છે (કુલ ૩૬ roles માંથી ૩૩ role માટે). **Supervisor** જેવો core
> production role માટે પણ કોઈ demo user નથી — જો ક્લાયન્ટ ડેમોમાં એ role જોવો હોય તો live બનાવવો પડશે
> (નીચે ૨.૫ જુઓ).

Password બધા demo users માટે સરખો: **`ChangeMe123!`**

---

## ૨.૩ Frontend Routes અને શું કરે છે

| પેજ | Route | શું કરે છે | Backend calls |
|---|---|---|---|
| Users | `/admin/users` | List (search/page), નવો user બનાવવો, એડિટ (email/full name — username બદલી ન શકાય), activate/deactivate ટોગલ, અલગ "Assign Role" form (user + site + role) | `GET/POST/PATCH /users`, `POST /users/{id}/deactivate\|reactivate`, `POST /users/{id}/roles` |
| Roles | `/admin/roles` | List, નવો role બનાવવો (name + description), એડિટ, permission checkbox list (આખો set એકસાથે replace થાય), delete (જો કોઈ user/SoD-rule/signature-policy એને reference કરે તો block) | `GET/POST/PATCH/DELETE /roles`, `GET /roles/{id}/permissions`, `POST /roles/{id}/permissions` |
| Access Review | `/admin/access-review` | Read-only role-assignment મેટ્રિક્સ (username/status/site-wise roles) + live "Authorization Decision Check" ફોર્મ: action code + site નાખો → ALLOW/DENY + કારણ + તમારા roles બતાવે | `GET /users`, `POST /policy/v1/decisions` |

આ પાંચેય પેજ ફક્ત **Admin** login ને જ દેખાય છે (`useRequireAdmin()`).

**નોંધ:** Role ની permissions બદલવી એટલે "આખો set ફરીથી define કરવો" — add/remove નહીં.
`POST /roles/{id}/permissions` હંમેશા સંપૂર્ણ `permission_ids` list મોકલે છે, જે જૂનો set replace કરે
છે (`commands.py:901-993`).

---

## ૨.૪ Permission મેટ્રિક્સ

| Action | Permission Code | કોણ ધરાવે છે | E-signature? |
|---|---|---|---|
| User બનાવવો/એડિટ/deactivate/reactivate | `platform.administer` | ફક્ત Admin | ના |
| User ને role assign કરવો (chosen site પર) | `platform.administer` (site-scoped ચેક) | ફક્ત Admin | ના |
| Role બનાવવો/એડિટ/ડિલીટ/permissions સેટ કરવા | `platform.administer` | ફક્ત Admin | ના |
| Access Review જોવી / Decision Check ચલાવવી | `platform.administer` (page gate) | ફક્ત Admin | — (live check, કોઈ audit trail entry બનતી નથી — SPEC_GAP કોડમાં જ નોંધેલ) |

આ બધું RBAC-only છે — company/sites ની જેમ, કોઈ e-signature ceremony નથી.

---

## ૨.૫ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `admin` / `ChangeMe123!`

### Step 1 — ખૂટતો "Supervisor" user બનાવવો (`/admin/users`)

| Field | Example Value |
|---|---|
| Username | `supervisor1` |
| Email | `supervisor1@example.com` |
| Full name | `Sara Supervisor` |
| Password | `ChangeMe123!` (અથવા કોઈ પણ 8+ char) |

Submit → `POST /users` → user બને છે.

### Step 2 — Role Assign કરવો (`/admin/users`, "Assign Role" form)

| Field | Example Value |
|---|---|
| User | `supervisor1` |
| Site | `SITE1` — Demo Site 1 |
| Role | `Supervisor` |

Submit → `POST /users/{id}/roles` → હવે `supervisor1` / `ChangeMe123!` login કરીને Supervisor role ની
actions (batch issue, step-start authorize, deviation triage) બતાવી શકાય.

### Step 3 — Access Review Decision Check (`/admin/access-review`)

Example: `supervisor1` ખરેખર batch issue કરી શકે કે નહીં — તે live ચકાસવા:

| Field | Example Value |
|---|---|
| Action code | `batch.issue` (ઉદાહરણ — actual code batch module ડોક્યુમેન્ટ ૦૮ માં) |
| Site | `SITE1` |

Result: ALLOW/DENY + કારણ સ્ક્રીન પર બતાવાશે — આ પોલિસી એન્જિન ને live "explain" કરવા માટે બહુ સરસ
ડેમો મોમેન્ટ છે.

---

## ૨.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. ~~`/security` frontend gate backend સાથે mismatch~~ **✅ Fixed (2026-09-18)** — gate હવે
   `canOperateSecurity()` વાપરે છે (5 security roles + Admin), Admin-only નથી. ૫ demo users પણ
   seed થયેલ (ઉપર ૨.૨ જુઓ) — હવે `security.architect` વગેરે login થી real console બતાવી શકાય.
2. **Access Review નું Decision Check કોઈ audit trail entry બનાવતું નથી** — એ ફક્ત live "what-if"
   ચેક છે, permanent record નથી.
3. **`Supervisor` જેવો core role ડેમોમાં હજુ કોઈ user ધરાવતો નથી** — ડેમો પહેલાં ઉપર ૨.૫
   પ્રમાણે જરૂરી user બનાવી લેવો.
