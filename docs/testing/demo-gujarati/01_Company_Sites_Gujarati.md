# ૧. કંપની (Organization) અને સાઇટ્સ (Sites) — Gujarati Demo Guide

> આ ડોક્યુમેન્ટ eBMR/eDHR પ્લેટફોર્મના **Company/Organization** અને **Sites** મોડ્યુલ માટે છે — ક્લાયન્ટ
> ડેમો દરમિયાન સમજાવવા માટે, real code (frontend + backend) વાંચીને લખેલ છે. બધા routes, API endpoints,
> permission codes અને roles વર્તમાન કોડ (`services/gxp-api/app/modules/iam/`,
> `frontend/src/app/admin/`) સામે ચકાસેલ છે.

---

## ૧.૧ આ મોડ્યુલ શું છે?

દરેક રેગ્યુલેટેડ મેન્યુફેક્ચરિંગ પ્લેટફોર્મમાં સૌથી ઉપર **Organization** (કંપની) હોય છે, અને તેની નીચે
એક કે વધુ **Sites** (મેન્યુફેક્ચરિંગ ફેસિલિટી/પ્લાન્ટ) હોય છે. આ સિસ્ટમમાં:

- **Organization** = કંપનીનું એક જ master record (નામ). ડેમો સિસ્ટમમાં હાલ **"Demo Manufacturing Co."**
  નામની એક જ Organization seed થયેલી છે.
- **Site** = એક ફિઝિકલ મેન્યુફેક્ચરિંગ લોકેશન, જેને `code` (દા.ત. `SITE1`) અને `name` (દા.ત.
  "Demo Site 1") હોય છે. ડેમોમાં હાલ **એક જ Site — `SITE1` / "Demo Site 1"** — seed થયેલ છે.
- દરેક **User ને Role**, **ચોક્કસ Site પર** assign કરવામાં આવે છે (site-scoped role assignment) —
  એટલે કે "આ user, આ site પર, આ role ધરાવે છે" — global role જેવી કોઈ વસ્તુ નથી.

> **ડેમો સ્ટોરી માટે:** ક્લાયન્ટને સમજાવતી વખતે તમે આ Organization ને તમારી પસંદગીના કાલ્પનિક નામે
> (દા.ત. "Meridian Therapeutics Inc.") role-play કરી શકો છો — સિસ્ટમમાં ખરેખર જે નામ સેવ થયેલું છે તે
> "Demo Manufacturing Co." જ દેખાશે, અને `/admin/company` પરથી Admin login વડે તમે લાઇવ એ નામ બદલી પણ
> શકો છો (નીચે જુઓ).

---

## ૧.૨ Frontend Routes

| પેજ | Route (URL) | શું કરે છે |
|---|---|---|
| Admin લેન્ડિંગ પેજ | `/admin` | Company, Sites, Users, Roles, Access Review — પાંચ સેક્શનની લિંક કાર્ડ્સ |
| Company | `/admin/company` | એક જ Organization record બતાવે છે; Admin એનું નામ એડિટ કરી શકે છે |
| Sites | `/admin/sites` | Site ની યાદી, નવી Site બનાવવી, એડિટ કરવી, ડિલીટ કરવી |

**અગત્યનું:** આ પેજ ફક્ત **Admin** role ધરાવતા user ને જ દેખાય છે (frontend hook `useRequireAdmin()`,
`frontend/src/lib/hooks.ts:51` — જે ચકાસે છે કે તમારા કોઈ પણ site પરના roles માં literally `"Admin"`
નામનો role છે કે નહીં).

---

## ૧.૩ Backend API

| Action | Method + Path | Request fields |
|---|---|---|
| Organization જોવી | `GET /organization` | — |
| Organization નું નામ બદલવું | `PATCH /organization` | `idempotency_key`, `name` |
| Sites ની યાદી | `GET /sites` | — |
| નવી Site બનાવવી | `POST /sites` | `code`, `name` |
| Site એડિટ કરવી | `PATCH /sites/{id}` | `name` |
| Site ડિલીટ કરવી | `DELETE /sites/{id}` | — (જો કોઈ user/record આ site ને reference કરતું હોય તો delete block થાય છે) |

(Source: `frontend/src/app/admin/company/page.tsx`, `frontend/src/app/admin/sites/page.tsx`,
backend `services/gxp-api/app/modules/iam/router.py`.)

---

## ૧.૪ Permission (Role) મેટ્રિક્સ

| Action | જરૂરી Permission Code | કયો Role ધરાવે છે | E-signature જરૂરી? |
|---|---|---|---|
| Organization નું નામ બદલવું | `platform.administer` | **ફક્ત Admin** | ના (RBAC-only) |
| Site બનાવવી / એડિટ / ડિલીટ | `platform.administer` | **ફક્ત Admin** | ના (RBAC-only) |

આ બંને actions **`evaluate_policy()`** થી RBAC-ચેક થાય છે (`app/modules/policy/service.py:41`) — પણ
**કોઈ password re-entry / e-signature ceremony નથી**, કારણ કે Company/Site લેવલનાં ફેરફાર Document 106ના
signature-floor list માં નથી (code comment: `commands.py:34`). સરખામણી માટે — batch release જેવી regulated
GxP actions માં password re-entry ફરજિયાત છે, પણ કંપની/સાઇટ સેટઅપ actions માં નથી, કારણ કે એ
administrative setup છે, regulated production decision નથી.

**અગત્યનું — ડેમોમાં ફક્ત `admin` login જ Company/Sites બદલી શકે છે.** આખા સિસ્ટમમાં `platform.administer`
permission **માત્ર Admin role ને જ** આપેલ છે (36માંથી બીજા કોઈ role ને નહીં) — તો ડેમો દરમિયાન આ સેક્શન
`admin` / `ChangeMe123!` login થી જ બતાવવું.

---

## ૧.૫ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `admin` / `ChangeMe123!`

### Step 1 — Company જોવી/બદલવી (`/admin/company`)
- હાલનું નામ: **Demo Manufacturing Co.**
- (વૈકલ્પિક) ડેમો માટે નામ બદલી શકાય, દા.ત. **"Meridian Therapeutics Inc."** — `PATCH /organization`
  call થશે અને તરત જ audit trail માં entry બનશે (જુઓ ડોક્યુમેન્ટ ૧૪ — Platform/Audit).

### Step 2 — નવી Site બનાવવી (`/admin/sites`)
Example ફોર્મ ડેટા:

| Field | Example Value |
|---|---|
| `code` | `SITE2` |
| `name` | `Durham Manufacturing Facility` |

Submit કરતા `POST /sites` call થાય છે → નવો Site record બને છે → Users & Roles ડોક્યુમેન્ટ (૦૨) માં
બતાવેલ પ્રમાણે, હવે આ નવી site પર users ને roles assign કરી શકાશે.

---

## ૧.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

> આ મુદ્દા client demo દરમિયાન honest રીતે જણાવવા — આ bugs નથી, પણ હાલની baseline ની જાણીતી મર્યાદાઓ છે.

1. **Read endpoints પર authentication check નથી.** `GET /organization` અને `GET /sites` — બંને backend
   endpoints કોઈ પણ authenticated actor વગર જ કામ કરે છે (કોડમાં કોઈ `actor` પેરામીટર જ નથી, અને
   `app/main.py` માં કોઈ global auth middleware પણ નથી). મતલબ frontend UI ભલે Admin-only દેખાડે, પણ
   કોઈ પણ વ્યક્તિ સીધું API call કરીને Organization/Sites ની માહિતી વાંચી શકે છે. આ frontend-only gate
   છે, backend-level access control નથી — future hardening માટે નોંધવા જેવો મુદ્દો.
2. **ડેમોમાં ફક્ત ૧ Organization અને ૧ Site seed થયેલ છે** — multi-site behavior (દા.ત. same user, અલગ
   sites પર અલગ roles) બતાવવા માટે ઉપર Step 2 પ્રમાણે live બીજી site બનાવવી પડશે.
