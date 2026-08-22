# NZ-eBMR — Role-Based Flow Guide (ગુજરાતીમાં)

**આ ડોક્યુમેન્ટ શેના માટે છે**

આ ડોક્યુમેન્ટ Drug-Device Combination Product (DDCP) સેક્શનના નવા **role-based login**
ફ્લોને સ્ક્રીન-બાય-સ્ક્રીન, સ્ટેપ-બાય-સ્ટેપ સમજાવે છે — યુઝર જ્યારે સિસ્ટમમાં દાખલ થાય
ત્યારે શું થાય છે, **કેમ** એવું ડિઝાઇન કરેલું છે, અને દરેક વસ્તુ ચકાસવા માટે **real test
case** શું છે. હેતુ એ છે કે તમે, હું, અને client — ત્રણેય — એક જ ભાષામાં વાત કરી શકીએ.

આ ડોક્યુમેન્ટ `DDCP-GUIDE-GUJARATI.md` (સ્ક્રીન-બાય-સ્ક્રીન કેટલોગ) અને
`CLIENT-DEMO-SCRIPT.md` (English presentation script) ને complement કરે છે — replace
નથી કરતું. જો તમારે client સામે English માં પ્રેઝન્ટ કરવું હોય તો એ સ્ક્રિપ્ટ વાપરો; આ
ડોક્યુમેન્ટ તમારી પોતાની સમજણ અને internal training માટે છે.

**Server address:**
```
cd /home/hepin/mydata/eBMR/eBMR-ui
python3 -m http.server 8942
# પછી ખોલો: http://127.0.0.1:8942/screens/001-sign-in.html
```

**અત્યારે શું live છે, શું નહીં:** Medical Device અને Pharmaceutical screens sign-in
પરથી comment-out કરેલા છે — client ને ફક્ત Drug-Device Combination Product દેખાડવાનું
છે. આ ડોક્યુમેન્ટ ફક્ત DDCP ના role-based flow વિશે છે, કારણ કે role-selection feature
હાલ પૂરતું DDCP માટે જ બનાવેલું છે.

---

## ભાગ ૧ — શા માટે "role login" ઉમેર્યું

**સવાલ જે તમે પૂછ્યો હતો:** "reviewer has login, admin has login, another role has
enter in the system — this will be easy to explanation."

**જવાબ, ટૂંકમાં:** પહેલાં આખી સિસ્ટમમાં એક જ વ્યક્તિ (K. Verma) તરીકે લોગિન થતું હતું,
અને દરેક સ્ક્રીન પર બધું જ ખુલ્લું દેખાતું હતું. પણ eBMR નો સૌથી અગત્યનો મુદ્દો જ એ છે કે
**કોણ સહી કરે છે એ મહત્વનું છે** — જે વ્યક્તિએ કામ કર્યું એ જ વ્યક્તિ verify ન કરી શકે,
જે વ્યક્તિએ batch બનાવ્યો એ જ વ્યક્તિ release ન કરી શકે. આ નિયમ (segregation of duties)
`screens/setup/roles.html` પર ટેબલ તરીકે પહેલેથી લખેલો હતો, પણ interface માં ક્યાંય
**દેખાતો** નહોતો.

હવે sign-in કર્યા પછી DDCP પસંદ કરો ત્યારે **"Who are you signing in as?"** સ્ક્રીન
આવે છે — ૪ persona cards: Admin, Planner, Operator, Quality. જે પસંદ કરો એ પ્રમાણે
sidebar ના અમુક link greyed-out (લૉક) થઈ જાય છે, અને My Work પર તમને ફક્ત તમારું જ કામ
દેખાય છે. Client ને બતાવવા માટે આ સૌથી શક્તિશાળી ડેમો છે — કારણ કે "permission-based
access control" શબ્દો બોલવાને બદલે તમે **લાઈવ બતાવી શકો છો**.

**અગત્યની નોંધ:** આ demo-only simulation છે. Role પસંદગી ફક્ત browser ના
`sessionStorage` માં રહે છે (tab બંધ થાય એટલે જતી રહે, ક્યાંય મોકલાતી નથી). Real
system માં આ authorization server પર ચેક થાય, browser માં નહીં — એ વાત client ને
સ્પષ્ટ કહેવી (script ના Appendix A માં પણ છે).

---

## ભાગ ૨ — ફ્લો બાય ફ્લો

### Flow 0 — Sign-in

**સ્ક્રીન:** `screens/001-sign-in.html`

**શું થાય છે:** Organization નું નામ (Acme Life Sciences Group) fixed દેખાય છે, email
અને password ભરો, "Continue" દબાવો. પછી context પસંદ કરવાનું પેજ આવે — હાલ ફક્ત
"Drug-Device Combination" કાર્ડ દેખાય છે.

**કેમ:** 21 CFR Part 11 કહે છે કે દરેક વ્યક્તિનું પોતાનું, unique login હોવું જોઈએ —
shared login ન ચાલે. Email/password પછી "context" (કયા profile/site માં કામ કરવું છે)
અલગથી પૂછવું એ બતાવે છે કે "profile પસંદ કરવો" પોતે કોઈ પરમિશન નથી આપતું — સર્વર દરેક
action ને અલગથી authorize કરે છે.

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T0.1 | Email/password ખાલી રાખીને "Continue" દબાવો | Field level validation — demo layer માં હાલ block નથી કરતું, પણ context tab ખૂલે છે (design preview) |
| T0.2 | "Continue" દબાવો | Context selection tab ખૂલે, ફક્ત "Drug-Device Combination" કાર્ડ દેખાય, MD/PH દેખાય નહીં |
| T0.3 | "Drug-Device Combination" કાર્ડ પર ક્લિક કરો | `ddcp/role-select.html` પર જાય (પહેલાં સીધું `ddcp/menu.html` પર જતું હતું — હવે role પસંદ કરવાનું સ્ટેપ વચ્ચે ઉમેરાયું) |

---

### Flow 1 — Role પસંદગી (નવો ફ્લો)

**સ્ક્રીન:** `screens/ddcp/role-select.html`

**શું થાય છે:** "Who are you signing in as?" — ૪ કાર્ડ:

**અપડેટ (પછીથી ઉમેરાયું):** હવે ૪ નહીં, **૫ role card** છે — "Recipe Author" નવો
ઉમેરાયો, કારણ રેસીપી (Integrated Master) લખવાનું કામ Planner કે Quality નું નથી,
એક અલગ જ ટીમનું છે. વિગત `DDCP-REAL-WORLD-DEMO-GUJARATI.md` ના ભાગ ૧ માં.

| Role | નામ | શું કરી શકે (✓) | શું ન કરી શકે (✕) |
|---|---|---|---|
| Admin | L. Park — Configuration/Access Administrator | Organisation configure કરે: sites, users, roles, products, materials, equipment | Production step perform, verify કે release ન કરી શકે |
| **Recipe Author** | S. Bloom / T. Alvarez — Recipe Authoring Team | Integrated Master લખે: admission, compatibility, per-unit BOM, process steps | પોતાની રેસીપી પોતે approve કે issue ન કરી શકે |
| Planner | M. Chen — Planner | Approved Integrated Master સામે final assembly order બનાવે અને issue કરે | પોતે issue કરેલું fill, test, label કે release ન કરી શકે |
| Operator | M. Ortiz — Filling/Assembly Operator | Filling, assembly, testing, labeling — shop floor નું કામ | પોતાનો order issue કે પોતાનું કામ release ન કરી શકે |
| Quality | P. Nair — Final Release Authority | Recipe approve કરે, Cross-constituent issue તપાસે, final product release કરે | જે સ્ટેપ પોતે કર્યું હોય એની review પોતે ન કરી શકે |

જે કાર્ડ પર ક્લિક કરો એ role `sessionStorage` માં સેવ થાય છે અને તમને `My Work` પર લઈ
જાય છે. નીચે એક લિંક છે: **"See everything unlocked (no role)"** — role પસંદ કર્યા
વગર આખું interface unlocked જોવા માટે (તમારા dev/testing માટે ઉપયોગી).

**કેમ:** ચાર જ role કેમ, દસ નહીં? — client ને સમજાવવા માટે ચાર personas પૂરતાં છે.
Data model માં ખરેખર ૧૦ roles છે (author, reviewer, approver, planner, supervisor,
operator, verifier, quality-investigator, release, admin) — પણ demo માટે ચાર main
buckets માં group કર્યા જેથી client ને ગૂંચવણ ન થાય. `roles.html` પર પૂરું ૯×૬ matrix
છે, જેની લિંક આ સ્ક્રીન પરથી જ મળે છે ("Roles & permissions").

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T1.1 | `role-select.html` પર fresh session માં જાવ | કોઈ role પહેલેથી selected ન દેખાય; પેજ પોતે load થતાં જ જૂનું stored role (જો હોય તો) clear કરી નાખે છે (`data-role-select-page` attribute દ્વારા) |
| T1.2 | "M. Ortiz" કાર્ડ પર ક્લિક કરો | `my-work/inbox.html` ખૂલે, sidebar-foot માં "SIGNED IN AS / M. Ortiz — Filling/Assembly Operator" દેખાય |
| T1.3 | "See everything unlocked" ક્લિક કરો | `menu.html` ખૂલે, કોઈ role set નથી, sidebar માં કંઈ locked ન દેખાય |

---

### Flow 2 — My Work: role પ્રમાણે અલગ દેખાવ

**સ્ક્રીન:** `screens/ddcp/my-work/inbox.html`

**શું થાય છે:** આ એક જ ફાઇલ છે, પણ role પ્રમાણે ચાર જુદા જુદા "view" બતાવે:

- **Role ન પસંદ કરેલું હોય** → "You haven't chosen who you are yet" કાર્ડ + "Choose
  a role" બટન. કોઈ task list દેખાતું નથી.
- **Admin** → "2 users invited, not yet signed in" અને "Setup checklist — 3 of 7
  done" — બે કાર્ડ, Setup screens ની સીધી લિંક સાથે.
- **Planner** → "Integrated Master EPIREL-03 v1.5 — draft, awaiting your review" અને
  "No open assembly orders on Line C — create the next one" — "Create a final
  assembly" ની લિંક સાથે.
- **Operator (M. Ortiz)** → મૂળ Ready/Waiting/Blocked/Returned/Completed tabs —
  Final assembly FA-33210 (Ready) અને Cross-constituent issue XC-0091 (Exceptions
  open).
- **Quality (P. Nair)** → "Cross-constituent issue XC-0091 — awaiting your impact
  assessment" અને "Final assembly FA-33210 — awaiting your release decision".

**કેમ:** "My Work" નો આખો મુદ્દો એ છે કે દરેક વ્યક્તિ પોતાનું જ કામ જુએ — Admin ને
production task ન દેખાય, Operator ને બીજાનું release-pending item ન દેખાય. જો બધા
roles ને એક જ list દેખાય તો "role-based access" ડેમો કરવાનો કોઈ મતલબ ન રહે.

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T2.1 | Role select કર્યા વગર સીધા `my-work/inbox.html` URL ખોલો | "You haven't chosen..." પ્રોમ્પ્ટ દેખાય, ૪ role blocks માંથી એકેય ન દેખાય |
| T2.2 | Admin તરીકે select કરો, My Work જુઓ | ફક્ત admin ના ૨ કાર્ડ દેખાય; operator ના tabs ન દેખાય |
| T2.3 | Admin થી Operator role માં switch કરો (sidebar-foot → "Switch role") | Operator ના Ready/Waiting/Blocked tabs દેખાય, admin ના કાર્ડ અદૃશ્ય |

---

### Flow 3 — Access control: sidebar link lock થવો

**સ્ક્રીન:** કોઈ પણ `combination/*.html` પેજ (દા.ત. `filling.html`)

**શું થાય છે:** Sidebar માં "Combination Product" સેક્શન નીચે ૧૧ links છે (પહેલા ૯
હતી — Recipe catalogue અને Recipe approval પછીથી ઉમેરાયા). Role પ્રમાણે અમુક links
**greyed out (અપારદર્શક) અને click-ન-થાય એવા** થઈ જાય છે, ને mouse hover કરો તો
tooltip માં કારણ દેખાય છે — દા.ત. *"Requires Planner/Batch Issuer — you're signed
in as M. Ortiz — Filling/Assembly Operator."*

**કઈ link કોના માટે unlock છે — પૂરું mapping (અપડેટેડ):**

| Sidebar link | Slug | કોના માટે unlock |
|---|---|---|
| Create a final assembly | `new-batch` | Planner |
| Admission & Part 4 | `admission` | **Recipe Author** |
| Compatibility & handoff | `compatibility` | **Recipe Author** |
| Integrated master | `integrated-master` | **Recipe Author** |
| Recipe catalogue *(નવું)* | `recipe-catalogue` | Recipe Author, Quality (બંને) |
| Recipe approval *(નવું)* | `recipe-approval` | Quality |
| Filling & assembly | `filling` | Operator |
| Integrated testing | `testing` | Operator, Quality (બંને) |
| Labeling & genealogy | `labeling` | Operator |
| Cross-constituent issue | `cross-constituent` | Quality |
| Complete review & release | `release` | Quality |
| Setup & masters | — | Admin |
| Authority, Interfaces, Support, Amendment (Admin area) | — | Admin |
| My Work, Records (explorer/timeline/export) | — | બધા roles (કોઈ lock નથી) |

**ફેરફારનું કારણ:** પહેલા admission/compatibility/integrated-master ને "Planner"
role મળતું હતું — પણ context bar પર ખરેખર દેખાતું નામ હંમેશા S. Bloom કે T. Alvarez
હતું, M. Chen ક્યારેય નહીં. એ ભૂલ હતી, હવે role અને real actor બંને એકસમાન છે.

**કેમ:** આ mapping `roles.html` ના segregation-of-duties નિયમો પ્રમાણે જ છે —
"જેણે batch બનાવ્યો એ release ન કરી શકે", "જેણે step કર્યું એ verify ન કરી શકે". Records
અને My Work બધા માટે ખુલ્લા છે કારણ કે **જોવું** (read access) એ **કરવું** (write/sign)
કરતાં અલગ પરમિશન છે — બધાને history જોવાનો હક છે, પણ બધા એ history બદલી ન શકે.

**ટેસ્ટ કેસ (automated Playwright દ્વારા ચકાસેલા — બધા pass):**
| # | Role | Screen | Link | અપેક્ષિત | પરિણામ |
|---|---|---|---|---|---|
| T3.1 | Operator | `combination/filling.html` | Filling & assembly (પોતાનું) | Unlocked | ✅ Pass |
| T3.2 | Operator | `combination/filling.html` | Create a final assembly | Locked | ✅ Pass |
| T3.3 | Operator | `combination/filling.html` | Admission & Part 4 | Locked | ✅ Pass |
| T3.4 | Operator | `combination/filling.html` | Complete review & release | Locked | ✅ Pass |
| T3.5 | Operator | `combination/filling.html` | Setup & masters | Locked | ✅ Pass |
| T3.6 | Operator | Locked link પર ક્લિક કરો | — | Navigate ન થાય (URL બદલાય નહીં) | ✅ Pass |
| T3.7 | Quality | `combination/release.html` | Complete review & release (પોતાનું) | Unlocked | ✅ Pass |
| T3.8 | Quality | `combination/release.html` | Filling & assembly | Locked | ✅ Pass |
| T3.9 | Admin | `my-work/inbox.html` | Setup & masters | Unlocked | ✅ Pass |
| T3.10 | Admin | `combination/filling.html` | Filling & assembly | Locked (Admin production માં કામ ન કરે) | ✅ Pass |
| T3.11 | Admin | `admin/authority.html` | Authority & training (પોતાનું area) | Unlocked | ✅ Pass |
| T3.12 | Operator | `admin/authority.html` (સીધું URL નાખીને) | Authority & training | Locked | ✅ Pass |
| T3.13 | No role ("See everything unlocked") | `combination/filling.html` | બધી links | Unlocked (0 locked links) | ✅ Pass |

*નોંધ:* T3.12 બતાવે છે કે URL સીધો ટાઈપ કરીને Admin ના પેજ પર જવાય તો પણ ખરું — પણ
sidebar navigation ત્યાં પણ locked જ રહે છે, કારણ કે lock JS-based છે, page-level નહીં
(static demo ની મર્યાદા — real system માં server આખું URL block કરી દેશે).

---

### Flow 4 — Admin: Setup & Masters

**Role:** Admin (L. Park)
**સ્ક્રીન:** `screens/setup/*.html` (૮ સ્ક્રીન)

**શું થાય છે:** Admin role select કરીને My Work → "Setup checklist — 3 of 7 done"
કાર્ડ → ક્લિક → `setup/checklist.html`. ત્યાંથી Company & sites, Users, Roles,
Products, Materials, BOM, Equipment — બધું edit કરી શકાય (forms કામ કરે છે, પણ કંઈ
save થતું નથી — demo marker "Demo preview — nothing is stored" દરેક પેજ પર દેખાય છે).

**કેમ:** Setup ડેટા બધા profiles વચ્ચે **shared** છે (એક જ Organisation, એક જ users
list) — એટલે એ કોઈ specific profile ના role માં નથી, અલગ "tenant-level" area છે. Admin
role એકલો જ ત્યાં પહોંચી શકે એ બતાવવા sidebar ની "Setup & masters" link ને
`data-role-allow="admin"` આપ્યું છે.

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T4.1 | Admin તરીકે `setup/bom.html` પર જાવ, "Add line" દબાવો, quantity ટાઈપ કરો | Total weight live update થાય (દા.ત. 178.200 → 181.700) |
| T4.2 | Admin તરીકે `setup/users.html` પર "Invite user" ખાલી form સાથે submit કરો | Validation error દેખાય, save ન થાય |
| T4.3 | Operator role select કરીને Setup ની link try કરો | Locked — ક્લિક કરવાથી કંઈ ન થાય |

---

### Flow 5 — Planner: Final Assembly Order બનાવવો

**Role:** Planner (M. Chen)
**સ્ક્રીન:** `screens/ddcp/combination/new-batch.html`

**શું થાય છે:** ૫-સ્ટેપ wizard — "Create a final assembly order":

1. **What to make** — Integrated Master v1.4 (approved) પસંદ કરો; v1.5 (draft) પસંદ
   કરી શકાય નહીં (radio button disabled).
2. **Order details** — FA-33211 (auto-assigned, edit ન થાય), quantity 4,000 units,
   site/line.
3. **Materials & lots** — દરેક material ને lot assign કરવો.
4. **Readiness** — **અહીં system ના-પાડે છે:** "Constituent batch not yet released
   by the Quality Unit." "Recheck readiness" દબાવો ત્યારે જ Cleared થાય.
5. **Review & issue** — સહી (PIN) વગર "Sign and issue" બટન કામ ન કરે.

**કેમ:** આ wizard client ને બતાવવા માટે સૌથી અગત્યનો ભાગ છે (English script ના Act 3
માં આ જ છે) — સિસ્ટમ **ના પાડે છે**, override કરવાનો કોઈ રસ્તો નથી.

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T5.1 | Step 2 માં quantity ખાલી કરીને "Continue" દબાવો | Error દેખાય, આગળ ન વધાય |
| T5.2 | Step 4 પર પહોંચો, કંઈ ન કરો, Step 5 પર જાવ | "Sign and issue" બટન locked (reason સાથે) |
| T5.3 | Step 4 પર "Recheck readiness" દબાવો | Blocker "Cleared" થાય, Step 5 નું બટન unlock થાય |
| T5.4 | PIN ખાલી રાખીને "Sign and issue" દબાવો | Save ન થાય |
| T5.5 | PIN ભરીને "Sign and issue" દબાવો | FA-33211 "Issued final assembly orders" ટેબલમાં ઉમેરાય, counter વધે |

---

### Flow 6 — Operator: Filling → Testing → Labeling

**Role:** Operator (M. Ortiz)
**સ્ક્રીન:** `combination/filling.html`, `testing.html`, `labeling.html`

**શું થાય છે:** Filling સ્ક્રીન પર destination device (scan), fill volume (0.30 mL,
limit 0.29–0.31 — within range), અને **independent verification** — "Cannot be
satisfied by a checkbox; a second qualified person must independently confirm on
their own session." Operator પોતે verify ન કરી શકે.

**કેમ:** બે-વ્યક્તિ નિયમ (two-person rule) નું આ practical ઉદાહરણ છે. Operator ને
verification field દેખાય છે ખરું, પણ "Awaiting a second identity" કહીને lock રહે છે —
Operator role માં હોવા છતાં પોતાનું જ કામ પોતે sign-off ન કરી શકે.

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T6.1 | Operator role માં `filling.html` ખોલો | "Independently verified by — Awaiting a second identity" દેખાય |
| T6.2 | Operator role માં `testing.html` ખોલો | Unlocked (sidebar), પેજ ખૂલે — testing operator + quality બંને માટે unlock છે |
| T6.3 | Operator role માં sidebar પરથી "Cross-constituent issue" try કરો | Locked |

---

### Flow 7 — Quality: Cross-constituent Issue → Release

**Role:** Quality (P. Nair)
**સ્ક્રીન:** `combination/cross-constituent.html`, `release.html`

**શું થાય છે:** XC-0091 (device-side assembly torque 40 units પર spec બહાર) ની impact
assessment કરવાની, પછી `release.html` પર final review — executed record, yield
reconciliation, બધા deviations closed, બધા lab results reviewed — ત્યારે જ "Release"
બટન unlock થાય.

**કેમ:** Quality role જ એકલો final release કરી શકે — Planner કે Operator ને એ બટન
sidebar માંય locked દેખાય. આ ડેમો client ને direct બતાવે છે કે "release authority"
કોઈ UI permission નહીં, પણ role-level guarantee છે.

**ટેસ્ટ કેસ:**
| # | Step | અપેક્ષિત પરિણામ |
|---|---|---|
| T7.1 | Quality role માં `release.html` ખોલો | Sidebar માં "Complete review & release" unlocked, "Create a final assembly" locked |
| T7.2 | Planner role માં `release.html` સીધું URL થી ખોલો | પેજ ખૂલે (static demo ની મર્યાદા) પણ sidebar link locked રહે |

---

## ભાગ ૩ — સંપૂર્ણ Test Case Matrix (client ને બતાવવા માટે ready)

નીચેનું ટેબલ presentation માં "proof" તરીકે વાપરી શકાય — દરેક role x action ચકાસેલી છે:

| Role → | Admin | Author | Planner | Operator | Quality |
|---|---|---|---|---|---|
| Setup & masters | ✅ Unlock | 🔒 Lock | 🔒 Lock | 🔒 Lock | 🔒 Lock |
| Create a final assembly | 🔒 Lock | 🔒 Lock | ✅ Unlock | 🔒 Lock | 🔒 Lock |
| Admission / Compatibility / Integrated master | 🔒 Lock | ✅ Unlock | 🔒 Lock | 🔒 Lock | 🔒 Lock |
| Recipe catalogue | 🔒 Lock | ✅ Unlock | 🔒 Lock | 🔒 Lock | ✅ Unlock |
| Recipe approval | 🔒 Lock | 🔒 Lock | 🔒 Lock | 🔒 Lock | ✅ Unlock |
| Filling & assembly | 🔒 Lock | 🔒 Lock | 🔒 Lock | ✅ Unlock | 🔒 Lock |
| Labeling & genealogy | 🔒 Lock | 🔒 Lock | 🔒 Lock | ✅ Unlock | 🔒 Lock |
| Integrated testing | 🔒 Lock | 🔒 Lock | 🔒 Lock | ✅ Unlock | ✅ Unlock |
| Cross-constituent issue | 🔒 Lock | 🔒 Lock | 🔒 Lock | 🔒 Lock | ✅ Unlock |
| Complete review & release | 🔒 Lock | 🔒 Lock | 🔒 Lock | 🔒 Lock | ✅ Unlock |
| Admin area (Authority/Interfaces/Support/Amendment) | ✅ Unlock | 🔒 Lock | 🔒 Lock | 🔒 Lock | 🔒 Lock |
| My Work, Records (read) | ✅ Unlock | ✅ Unlock | ✅ Unlock | ✅ Unlock | ✅ Unlock |

આ ટેબલ code માં `shell.py` ના `ROLE_SCOPE` dictionary માંથી સીધું જ generate થાય છે —
એટલે UI અને આ ડોક્યુમેન્ટ ક્યારેય એકબીજાથી અલગ (out of sync) નહીં પડે, જ્યાં સુધી
`ROLE_SCOPE` બદલાય નહીં.

---

## ભાગ ૪ — Client સામે કેવી રીતે demo કરવું (ટૂંકમાં)

1. Sign-in → Drug-Device Combination → role-select સ્ક્રીન બતાવો, ૪ કાર્ડ સમજાવો.
2. **Operator** તરીકે login કરો → sidebar બતાવો → "Create a final assembly" locked
   છે એ hover કરીને tooltip વંચાવો.
3. **Switch role** કરીને **Planner** બનો → એ જ link હવે unlock છે એ બતાવો → Create
   a final assembly wizard ખોલો, Step 4 પર system ના પાડે એ બતાવો.
4. **Switch role** કરીને **Quality** બનો → Release સ્ક્રીન ખોલો → "Filling &
   assembly" હવે locked છે એ બતાવો.
5. છેલ્લે: "આ જ પેટર્ન real system માં લાગુ પડે છે — ફર્ક એટલો કે ત્યાં આ ચેક server
   પર થાય, browser માં નહીં, અને કોઈ પણ રીતે bypass ન થઈ શકે."

**એક લાઈન જે સૌથી વધુ અસર કરે છે:**
> "તમે જુઓ છો — Operator તરીકે હું Release બટન સુધી પહોંચી જ નથી શકતો. આ કોઈ 'hide
> button' ટ્રીક નથી; આ ડિઝાઇન છે — જે વ્યક્તિએ કામ કર્યું, એ જ વ્યક્તિ પોતાનું કામ
> mark-as-done ન કરી શકે. Inspector પણ આ જ સવાલ પૂછશે, અને સિસ્ટમ પાસે જવાબ તૈયાર છે."

---

## Appendix — Screen ↔ Role ↔ File સંદર્ભ

| Role | Landing (My Work) | Setup access | Combination pages unlocked |
|---|---|---|---|
| Admin — L. Park | `ddcp/my-work/inbox.html` (admin view) | `setup/*.html` (બધા ૮ + asset-detail) | કોઈ નહીં |
| Recipe Author — S. Bloom / T. Alvarez | `ddcp/my-work/inbox.html` (author view) | નહીં | admission, compatibility, integrated-master, recipe-catalogue |
| Planner — M. Chen | `ddcp/my-work/inbox.html` (planner view) | નહીં | new-batch |
| Operator — M. Ortiz | `ddcp/my-work/inbox.html` (operator view, default tabs) | નહીં | filling, testing, labeling |
| Quality — P. Nair | `ddcp/my-work/inbox.html` (quality view) | નહીં | recipe-catalogue, recipe-approval, testing, cross-constituent, release |

**રેસીપીના real numbers, batch ના real numbers, અને asset ના real numbers જોઈતા
હોય તો:** `DDCP-REAL-WORLD-DEMO-GUJARATI.md` જુઓ — એ ડોક્યુમેન્ટ 0.30 mL થી શરૂ
કરીને 4,000 યુનિટના batch સુધીની આખી ગણતરી, real screen numbers સાથે બતાવે છે.

**Role picker:** `screens/ddcp/role-select.html`
**Role engine (JS):** `assets/js/ebmr-ui.js` → `initRoleView()`
**Sidebar lock rules (source of truth):** `ROLE_SCOPE` dictionary, `shell.py` ના
`sidebar()` function માં — આ Python generator સ્ક્રિપ્ટ છે જે દરેક `.html` ફાઇલ
compile કરે છે. તેની current copy session ના scratchpad માં છે, repo માં નથી —
ભવિષ્યમાં આ ડિઝાઇન ફરી generate કરવી હોય તો generator scripts repo માં લાવવા જરૂરી
છે (અલગથી પૂછો તો કરી આપીશ).
