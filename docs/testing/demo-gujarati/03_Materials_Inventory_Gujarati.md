# ૩. Suppliers, Materials, Inventory & Dispensing

આ આખો flow manufacturing માં **સામગ્રી ક્યાંથી આવે છે, તેની quality કેવી રીતે check થાય છે, stock માં કેવી રીતે રાખવામાં આવે છે અને batch માટે કેવી રીતે issue/dispense થાય છે** તે manage કરે છે.

---

## ૩.૧ Supplier Management

### Supplier શું છે?

Supplier એટલે જે company પાસેથી આપણે **raw material અથવા અન્ય manufacturing material** ખરીદીએ છીએ.

Supplier ને system માં register કર્યા પછી તેની **qualification અને quality performance** manage કરી શકાય છે.

### Example

**Supplier:** Excipients Corp Ltd.
**Code:** `SUP-MERIDIAN-EXC`
**Type:** Manufacturer
**Country:** USA

### Supplier Qualification શું છે?

Supplier પાસેથી material લેતા પહેલાં આપણે check કરીએ કે:

* Supplier યોગ્ય અને approved છે?
* તેની quality સારી છે?
* જરૂરી documents/evidence છે?
* Quality agreement છે?
* Risk acceptable છે?

### Simple Flow

**Supplier Create → Qualification Request → QA Review → Qualification Approve**

Example:

`process.engineer` → Supplier બનાવે અને qualification request કરે
`qa.releaser` → Review કરીને qualification approve કરે

અહીં **એક જ વ્યક્તિ request અને approval કરી શકતી નથી**. આને **Segregation of Duties (SoD)** કહે છે.

---

# ૩.૨ Material Master

### Material શું છે?

Material એટલે manufacturing માં ઉપયોગ થતી actual વસ્તુ.

System માં દરેક material માટે એક unique record હોય છે.

### Example

**Code:** `MAT-EXCIPIENT-01`
**Name:** Sodium Chloride USP
**UOM:** kg

Material Master આપણને કહે છે:

> “આ કઈ material છે?”

પરંતુ તે material ની quality કેવી હોવી જોઈએ તે Material Specification માં આવે છે.

---

# ૩.૩ Material Specification

### Material Specification શું છે?

Specification એટલે material **કયા quality criteria પ્રમાણે acceptable છે** તે define કરતું controlled document.

તે version-controlled હોય છે.

### Example

**Material:** Sodium Chloride USP
**Specification ID:** `MATSPEC-PFS-BODY-001`
**Version:** 1

Example criteria:

* Purity કેટલી હોવી જોઈએ
* Appearance કેવી હોવી જોઈએ
* Moisture limit કેટલી હોવી જોઈએ

### Simple Flow

**Draft → QA Review → Release**

`process.engineer` → Specification બનાવે

`qa.releaser` → Review કરીને Release કરે

Release વખતે **e-signature જરૂરી છે** અને author તથા approver અલગ વ્યક્તિ હોવી જોઈએ.

---

# ૩.૪ Material Lot & Material Receipt

### Material Lot શું છે?

એક જ material ની **એક specific received quantity/batch** ને Lot કહેવાય.

Example:

Supplier પાસેથી:

> Sodium Chloride = 500 kg

આ shipment માટે system માં Lot બને:

`LOT-MJ-2026-014`

અટલે:

**Material = શું વસ્તુ છે**
**Lot = તે વસ્તુનો ચોક્કસ received batch/quantity**

---

## Material Receipt શું છે?

Supplier પાસેથી material company માં આવે ત્યારે તેની **receiving entry** બનાવવામાં આવે છે.

### Simple Flow

**Receive → Examine → Quarantine → Sample / Retest → Release / Reject**

Example:

Supplier 500 kg Sodium Chloride મોકલે છે.

1. Operator material receive કરે
2. System receipt બનાવે
3. Material examine થાય
4. બધું OK હોય → Lot બનાવાય
5. Lot શરૂઆતમાં **Quarantine** માં રહે
6. જરૂર પડે તો Sample લેવાય અથવા Retest માટે મોકલાય
7. QC/QA check પછી:

   * **Release** → Production માટે ઉપયોગ કરી શકાય
   * **Reject** → ઉપયોગ કરી શકાય નહીં

### Important

**Receipt અને Release અલગ વસ્તુ છે.**

Receipt એટલે:

> “Material આવી ગયું.”

Release એટલે:

> “QA એ કહ્યું કે હવે આ material ઉપયોગ કરી શકાય.”

---

## Lot ના Action Buttons (`/material-lots`)

Lot create થાય (receive) એટલે તે **Quarantine** status માં આવે છે, અને એ status માં તેની row પર આ action buttons દેખાય છે:

| Button | શું કરે છે | Permission | કોણ | Signed? |
|---|---|---|---|---|
| **Quality status** | Lot ની quality/disposition details જુએ (read-only) | — (view) | બધા | ના |
| **Sample** | Sampling order બનાવે (containers + sampler pick કરો), પછી collected sample ની quantity/UOM record કરે | `material_lot.sampling_order` (order બનાવવા), `material_lot.collect_sample` (collect કરવા) | Operator/Supervisor (order), **QC Reviewer** (collect) | ના |
| **Retest** | Final release/reject નક્કી કરવાને બદલે, lot ને ફરીથી examine/test માટે મોકલે — reason જરૂરી | `material_lot.retest` | QC Reviewer, QA Releaser | ના |
| **Disposition** | QC પોતે એક જ signed action માં **Release** અથવા **Reject** નક્કી કરે (જૂનો/simple single-step path) | `material_lot.disposition` | **QC Reviewer** | **હા** |
| **Release (QA)** | QA formally lot release કરે — નવો, બે role વાળો formal path (Document 19 v2) | `material_lot.release` | **QA Releaser** | **હા** |
| **Reject (QA)** | QA formally lot reject કરે — reason જરૂરી | `material_lot.reject` | **QA Releaser** | **હા** |

> **નોંધ ૧:** "Disposition" (QC પોતે release/reject બંને કરી શકે, એક જ પગલામાં) અને "Release (QA)"/"Reject (QA)"
> (QA દ્વારા formal, અલગ-અલગ path) — બંને હજી UI માં સાથે ઉપલબ્ધ છે. Real deployment માં client સાથે નક્કી
> કરવાનું રહેશે કે કયો path વાપરવો.
>
> **નોંધ ૨ (SoD):** "Release (QA)"/"Reject (QA)" સહી કરનાર વ્યક્તિ, આ lot ના **receiver અથવા sampler કરતાં
> અલગ** હોવી જોઈએ — આ independence check server-side enforced છે.
>
> **નોંધ ૩:** "Sample" અને "Retest" પર frontend માં કોઈ role-based button hide નથી (દરેક logged-in
> user ને Quarantine lot પર આ buttons દેખાય છે) — પણ permission ના હોય તો click કરવાથી server action
> reject કરે છે.

**ડેમો Logins:** `operator1` / `supervisor1` (receive, sampling order બનાવે), `qc.reviewer` (disposition,
sample collect, retest), `qa.releaser` (Release (QA) / Reject (QA), retest).

---

# ૩.૫ Inventory

Inventory એટલે હાલમાં company પાસે **કેટલી material ઉપલબ્ધ છે અને ક્યાં રાખેલી છે** તેની માહિતી.

### Example

**Warehouse:** `WH1`
**Location:** `QUARANTINE-02`
**Lot:** `LOT-MJ-2026-014`

System માં આપણે જોઈ શકીએ:

* કેટલું material available છે
* કેટલું reserved છે
* ક્યાં stored છે
* batch માટે કેટલું issue/dispense થયું

Inventory માં:

* Reservation
* Transfer
* Split / Merge
* Cycle Count
* Warehouse Location
* Exceptional Adjustment

જેવા operations પણ છે.

### Exceptional Adjustment Example

System માં 100 kg દેખાય છે, પરંતુ physical count 98 kg છે.

આવા exceptional correction માટે:

**Create Adjustment → QA/Admin Review → Approve/Reject**

Approval signed હોય છે અને adjustment બનાવનાર વ્યક્તિ પોતાનું adjustment approve કરી શકતી નથી.

---

# ૩.૬ Dispensing

### Dispensing શું છે?

Dispensing એટલે batch માટે જરૂરી material ને **ચોક્કસ quantity માં weigh કરીને issue કરવું**.

આ production પહેલાંનું controlled weighing step છે.

### Example

Batch:

`MJ-2026-0142`

Material:

`MAT-EXCIPIENT-01`

Required Quantity:

**2.5 kg ± 0.1 kg**

### Flow

**Create Order → Select Lot → Weigh → Record Reading → Complete → Verify**

Example:

`operator1` material weigh કરે:

> Actual reading = 2.48 kg

આ target tolerance માં છે.

પછી:

`qc.reviewer` reading verify કરે.

અહીં પણ **weigher અને verifier અલગ વ્યક્તિ હોવી જોઈએ.**

---

# ૩.૭ આખો Flow એક Example સાથે

ધારો કે production માટે **Sodium Chloride** જોઈએ છે.

### Step 1 — Supplier

`Excipients Corp Ltd.` supplier તરીકે register થાય.

↓

### Step 2 — Supplier Qualification

QA supplier ની qualification approve કરે.

↓

### Step 3 — Material

`MAT-EXCIPIENT-01 – Sodium Chloride USP` material master માં છે.

↓

### Step 4 — Specification

Sodium Chloride માટે approved specification છે.

↓

### Step 5 — Material Receipt

Supplier પાસેથી **500 kg** material આવે.

↓

### Step 6 — Lot

System માં:

`LOT-MJ-2026-014`

બને છે.

↓

### Step 7 — Quarantine

Lot શરૂઆતમાં quarantine માં રહે છે.

↓

### Step 8 — QA Release

જરૂર પડે **Sample**/**Retest** કર્યા પછી, `qa.releaser` **Release (QA)** button થી lot **Released** કરે છે
(અથવા `qc.reviewer` **Disposition** button થી એક જ પગલામાં).

↓

### Step 9 — Inventory

Released lot inventory માં available થાય છે.

↓

### Step 10 — Dispensing

Batch `MJ-2026-0142` માટે:

**2.5 kg** material dispense થાય છે.

Operator weigh કરે છે અને QC Reviewer verify કરે છે.

---

# ૩.૮ એક મહત્વની Current Limitation

હાલ system માં **Batch Execution નો `material_consume` step automatic રીતે Inventory માંથી quantity deduct કરતો નથી.**

અટલે demo માં:

**Batch Step → Automatic Inventory Deduction**

હાલ ઉપલબ્ધ નથી.

Inventory movement બતાવવી હોય તો **Dispensing flow અલગથી ચલાવવો પડે છે.**

આ future implementation માટે client સાથે નક્કી કરવાનું રહેશે કે batch consumption પછી inventory અને material lot બંને કેવી રીતે synchronize કરવા.

---

## એક Line માં આખું સમજવું હોય તો

**Supplier → Qualification → Material → Specification → Receipt → Lot → Quarantine → QA Release → Inventory → Dispensing → Batch**

અર્થાત:

> **ક્યાંથી material આવ્યું → material શું છે → quality कैसी હોવી જોઈએ → material આવ્યું છે કે નહીં → QA એ release કર્યું કે નહીં → stock માં કેટલું છે → batch માટે કેટલું weigh કર્યું.**
