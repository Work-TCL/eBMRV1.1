# NZ-eBMR — Client Demonstration Script

**Purpose.** A word-for-word walkthrough you can present to a client, in order, without
preparation. Each act tells you which screen to open, what to click, what will happen,
and what to say while it happens.

**Duration.** 55–70 minutes for the full script. A 20-minute version is marked with ⚡.

---

> ## ⚠ CURRENT MODE: Combination Product only
>
> Medical Device and Pharmaceutical are **commented out** of the sign-in screen and the
> Setup sidebar. A client cannot reach those 67 screens — verified by walking every link
> from sign-in. Only Combination Product, Setup and Onboarding are live (30 screens).
>
> **This means Acts 3 and 4 below name Pharmaceutical paths that are currently hidden.**
> Use these substitutions:
>
> | Script says | Open instead |
> |---|---|
> | `ph/production/new-batch.html` | `ddcp/combination/new-batch.html` |
> | `ph/production/execution.html` | `ddcp/combination/filling.html` |
> | `ph/production/dispensing.html` | `ddcp/combination/filling.html` |
> | `ph/production/verification.html` | `ddcp/combination/compatibility.html` |
> | `ph/production/inspection.html` | `ddcp/combination/testing.html` |
> | `ph/quality/deviation.html` | `ddcp/combination/cross-constituent.html` |
> | `ph/quality/release.html` | `ddcp/combination/release.html` |
> | `ph/records/timeline.html` | `ddcp/records/timeline.html` |
>
> And the vocabulary changes with it: a **batch** becomes a **final assembly order**
> (FA-33211), a **deviation** becomes a **cross-constituent issue** (XC-0091), and the
> **Quality Unit** becomes the **Final Release Authority**. Step 4's blocker is that the
> drug constituent batch has not been released yet, rather than a line clearance.
>
> **Skip section 3.6** ("the same wizard in the other two profiles") entirely — it opens
> the hidden profiles.
>
> To restore all three profiles, uncomment the marked blocks in
> `screens/001-sign-in.html` and in the Setup sidebar, then re-run the setup generator.

---

> ## 🔑 NEW: role-based sign-in
>
> Clicking "Drug-Device Combination" on sign-in no longer goes straight to the work-area
> menu. It now stops at **`ddcp/role-select.html`** — "Who are you signing in as?" — with
> four persona cards: **Admin (L. Park)**, **Planner (M. Chen)**, **Operator (M. Ortiz)**,
> **Quality (P. Nair)**. Picking one greys out sidebar links that persona shouldn't reach,
> with a tooltip explaining why, and scopes the My Work landing to that person's own tasks.
> A **"Switch role"** link sits in the sidebar footer on every DDCP screen from then on.
>
> This is a strong addition to Act 0 and Act 3 below — it makes segregation-of-duties
> *visible* instead of described. Suggested insert, right after Act 0:
>
> 1. Click Drug-Device Combination → land on role-select. Read the four cards aloud.
> 2. Pick **Operator**. Open the Combination Product sidebar — point out
>    *Create a final assembly*, *Admission & Part 4* and *Complete review & release* are
>    greyed out. Hover one: the tooltip states which role is required.
> 3. Click **Switch role** → pick **Planner**. Same sidebar, same client — now
>    *Create a final assembly* is live and the production/quality screens are locked.
> 4. Say: *"That's not a hidden button — it's the same rule an inspector checks: whoever
>    performs a step cannot be the one who releases it."*
> 5. Continue into Act 3 already signed in as **Planner** (needed for step 5's issue
>    signature) or **Quality** (needed for Act 4's release) — switch role again as each
>    act requires the matching persona, and narrate the switch each time.
>
> Full flow-by-flow detail, the complete lock/unlock matrix, and Gujarati test cases:
> **`DDCP-ROLE-FLOW-GUJARATI.md`**.

**Before you start.** Serve the folder and open the first screen:

```bash
cd /home/hepin/mydata/eBMR/eBMR-ui
python3 -m http.server 8942
# then open http://127.0.0.1:8942/screens/001-sign-in.html
```

**One thing to say up front, once.** There is a small badge in the bottom-right of every
screen reading *"Demo preview — nothing is stored."* Point at it in Act 0 and say it
plainly: this is a working picture of the interface, not a running system. Forms
validate, tables update, the wizard refuses to advance — but nothing is written to a
database. Saying this once, early, buys you credibility for the whole hour. Do not let
a client discover it themselves at minute 40.

---

## The story you are telling

The demo follows one organisation, **Acme Life Sciences Group**, from the day they
switch the system on to the day they release a batch. It has four movements:

| Act | Question the client is really asking | Screens |
|---|---|---|
| 1 | *What do I get on day one?* | Onboarding — 3 screens |
| 2 | *How much work is it to set up?* | Setup — 8 screens |
| 3 | *What does my team actually do all day?* | Batch creation + execution |
| 4 | *What happens when something goes wrong?* | Exceptions, quality, release |

Resist the temptation to open screens in any other order. The setup screens are dull in
isolation and meaningful once the client has seen the empty system in Act 1.

---

# ACT 0 — Framing (2 minutes)

**Screen:** `screens/001-sign-in.html`

**Do:** Nothing yet. Leave the sign-in screen up while you talk.

**Say:**

> "What you're looking at is the whole interface of an electronic batch record system.
> Before I click anything, three things about the shape of it.
>
> First, this one system covers three different regulated worlds — medical devices,
> pharmaceuticals, and combination products where a drug and a device ship as one item.
> Those are genuinely different rule-sets, and the system keeps them separate rather
> than averaging them into something vague.
>
> Second, everything you'll see is designed around one idea: the record has to be
> defensible to an inspector two years from now, when nobody remembers the batch. That
> shapes every screen.
>
> Third — see the badge in the corner? Nothing here is stored. This is the interface,
> working, with realistic data. It is not a live system."

**Then:** Point out the three profile cards, and the *Administration and onboarding*
section below them.

> "We're going to start at the very bottom — day one, before anything exists."

---

# ACT 1 — Day one: an empty system (8 minutes) ⚡

### 1.1 The welcome screen

**Screen:** `screens/onboarding/welcome.html`
**Click:** *Day one — a brand-new organisation*

**Say:**

> "This is what Acme sees the first time they log in. Read the headline: **your workspace
> is empty, and that is correct.**
>
> Most software ships with sample data so the demo looks impressive. This deliberately
> doesn't. In a regulated system, every value has to have been put there on purpose by a
> named person. If the system pre-loaded a product called 'Sample Product', someone would
> eventually build a batch against it."

**Do:** Scroll to the seven-step list.

> "Seven things have to exist before anyone can run a batch. Company and sites, users,
> roles, products, materials, bills of materials, equipment. Roughly half a day of work
> for one site, done once."

**Do:** Point at the order.

> "The order isn't arbitrary. You can't assign a user to a site that doesn't exist. You
> can't write a bill of materials before the materials exist. The system enforces the
> dependency rather than letting you create orphans and clean up later."

**Do:** Scroll to the three profile cards.

> "And the first real decision: which of these worlds each product lives in. This choice
> decides what a batch is called, what a problem is called, and who's allowed to release
> it. Acme runs all three — one site each."

### 1.2 What an unconfigured system looks like

**Click:** *See what the app looks like before setup*
**Screen:** `screens/onboarding/first-run.html`

**Say:**

> "This is the honest answer to 'what do I get on day one'. My Work, and it's empty."

**Do:** Point at the greyed-out sidebar items.

> "Look at the sidebar. Batch execution, dispensing, in-process control, deviations —
> all visible, all disabled. The system doesn't hide what it can do. It shows you the
> whole shape and tells you why each part isn't available yet."

**Do:** Scroll to the *Why the sidebar items are greyed out* table.

> "And here's the table that explains it. Dispensing needs materials and a bill of
> materials. Batch execution needs a product, a recipe and released equipment. Each row
> tells the administrator exactly which setup step unlocks it.
>
> This matters more than it looks. A half-configured system that lets an operator start
> a batch is more dangerous than one that refuses — because the record would be missing
> the controls that make it worth anything."

### 1.3 A new person's first sign-in

**Click:** *See a new person's first sign-in*
**Screen:** `screens/onboarding/new-user.html`

**Say:**

> "Different scenario. The organisation is already set up, and a new operator, N. Shah,
> joins. Four steps, about three minutes."

**Do — Step 1:** Click **Continue** with the password fields empty.

> "Watch — it refuses. Both fields turn red. That's the behaviour you'll see all
> afternoon: the system doesn't accept incomplete input and sort it out later."

**Do:** Fill both password fields. Click **Continue**.

**Do — Step 2:** Read the panel out loud.

> "This is the part clients underestimate. The password gets you in. The **PIN** is what
> you use to sign a step — and they're deliberately different things.
>
> When N. Shah signs a step, the system records her name, the exact time, which step, and
> the *meaning* — performed, verified, or approved. Nobody can edit or delete that,
> including an administrator. It carries the same legal weight as her initials on a paper
> batch record.
>
> She'll be asked for this PIN dozens of times a shift, and that friction is the point.
> Signing should be a conscious act, not a click."

**Do:** Fill both PIN fields. Click **Continue**.

**Do — Step 3:** Point at SOP-045, showing *Not trained*.

> "Her training record. Three qualifications current, one missing — compression
> operation. Note what the system does *not* do: it doesn't block her account. She can
> dispense and weigh from her first shift. But if she opens a compression step, it will
> refuse and show her this exact row as the reason."

**Do:** Click **Confirm and finish** without ticking the box.

> "And the acknowledgement is enforced too."

**Do:** Tick the box, click **Confirm and finish**.

> "She's active, her supervisor has been notified, and her first assignment is already
> waiting — batch B-2026-0142, dispensing, booth D-101, due at 09:30."

---

# ACT 2 — Setting up the organisation (18 minutes)

> **⚡ Short version:** show only **Products**, **Bill of materials** and **Users**.
> Skip company, roles, materials and equipment.

**Screen:** `screens/setup/checklist.html`

**Say:**

> "Now we're the administrator, L. Park, doing that half-day of setup. Progress bar says
> three of seven. Let me show you what each one actually asks for."

### 2.1 Company & sites

**Click:** *Company & sites*

> "The legal entity, and every site that manufactures. Acme has three plus a warehouse —
> Ahmedabad runs pharmaceutical, Pune runs devices, Bengaluru runs combination products.
>
> The FEI number and the registered address aren't decoration. They print on records that
> go to a regulator."

**Do:** Click **Add site**, fill it in, save.

> "Every list you'll see today works this way — a form, validation, and the row appears."

### 2.2 Users

**Click:** *Users* in the sidebar.

**Say:**

> "Eight people. Note the columns: role, site, and status. And note that two of them are
> *Invited — not yet signed in* — that's the state N. Shah was in before Act 1."

**Do:** Click **Invite user**, then click **Send invitation** with everything blank.

> "Same behaviour. Required fields, enforced."

**Do:** Fill in a name, email, pick a role and a site, save. Point at the new row.

**Say — this is the important line:**

> "Three things a person needs before they can do regulated work: an account, a role,
> and a training record. Miss any one and the system will stop them at the point of use
> and tell them which one is missing."

### 2.3 Roles & permissions

**Click:** *Roles & permissions*

**Say:**

> "Nine roles, six permission types. Read across the row: a Production Operator can
> record and sign as performer, but cannot verify, approve or release."

**Do:** Scroll to the segregation-of-duties table.

> "This is the part that a Quality director will care about most. Five rules the system
> enforces structurally — not by policy, by refusal.
>
> The first one: the person who performs a step cannot be the person who verifies it.
> Not 'shouldn't' — *cannot*. If K. Verma dispenses, the system will not offer K. Verma
> as the independent check, even if she has the role, even if she's the only person on
> shift. That's the control that makes a two-person check mean something."

### 2.4 Products

**Click:** *Products*

**Say:**

> "Five products across the three profiles. And here's where that profile decision from
> Act 1 becomes concrete."

**Do:** Point at the *What the profile choice actually changes* table.

> "Same system, three vocabularies. Pharmaceutical: you make a **batch**, a problem is a
> **deviation**, and the **Quality Unit** releases it. Medical device: you make **serialised
> units**, a problem is a **nonconformance**, and **Device Quality** releases it. Combination:
> a **final assembly**, a **cross-constituent issue**, and a single **Final Release Authority**.
>
> These aren't labels. They're different records and different signatures."

**Do:** Read the line under the table.

> "And this cannot be changed once the first batch is issued. The records would become
> ambiguous. It's a deliberate one-way door."

**Do:** Click **Add product**, create one, save.

### 2.5 Materials

**Click:** *Materials & items*

**Say:**

> "Nine materials — actives, excipients, components, packaging. Note MAT-1003 has a
> supplier and a shelf life; COMP-4471, a moulded component, has neither."

**Do:** Point at the *Material vs lot* panel.

> "This distinction confuses people, so I'll be explicit. 'Magnesium stearate, MAT-1003'
> is the **material** — the kind of thing, defined once. 'LOT-A2291, received 12 July,
> expires March 2028' is a **lot** — one specific delivery, with its own status and test
> results.
>
> An approved material can still have a rejected lot. And the link from a finished batch
> back to the exact lots used is what turns a supplier recall from a two-week panic into
> a two-minute query."

**Do:** Type "connector" into the search box.

> "Live filter. Nine records down to one."

### 2.6 Bill of materials — the one to slow down on

**Click:** *Bill of materials*

**Say:**

> "This is the recipe. Paracetamol 500mg, batch size 250,000 tablets, version 3.2, four
> material lines, total charged weight 178.2 kg."

**Do:** Click **Add line**. A new row appears. Type `3.500` into the quantity.

> "Watch the total — 178.2 becomes 181.7 as I type."

**Do:** Click the **×** to remove the row.

> "And back to 178.2."

**Do:** Point at the **Tolerance %** column, then the panel below it.

**Say — this is the single most persuasive moment in the demo:**

> "Now, the tolerance column. This is what makes the whole thing enforceable.
>
> Magnesium stearate: 1.800 kg, plus or minus 5 percent. So the operator has to land
> between 1.710 and 1.890 kg. If they weigh 1.895, the system will not accept it. Not a
> warning, not a supervisor override — it refuses the value and opens an exception.
>
> There is no 'close enough' path. And you'll see that exact failure in a few minutes."

**Do:** Scroll to *All BOM versions*.

> "And it's versioned. v3.2 is effective, v3.1 is obsolete. Changing a quantity creates a
> new version — it never edits the one that past batches were made against. Otherwise
> you'd be rewriting history, which is the thing this software exists to prevent."

### 2.7 Equipment & rooms

**Click:** *Equipment & rooms*

**Say:**

> "Seven machines, four rooms. Look at the status column — EQ-7710, the leak tester, is
> **overdue**."

> "Leave that one in your memory. We're going to meet it again in about five minutes, and
> it's going to stop a production order."

**Do:** Point at the *Why equipment lives in setup* panel.

> "One design note. The recipe says 'use a balance accurate to 0.001 kg'. It does not
> name SC-4402. The specific instrument is chosen at execution and recorded then — so
> when SC-4402 goes for calibration, every recipe keeps working, and the record still
> shows exactly which balance weighed that batch."

---

# ACT 3 — Making a batch (20 minutes) ⚡

> This is the centre of the demo. If you have 20 minutes total, do only this act.

**Navigate:** Sign-in → **Pharmaceutical** → **Production** → **Create a batch**
**Screen:** `screens/ph/production/new-batch.html`

**Say:**

> "Setup is done. Now the daily work. M. Chen, the planner, is going to create a batch —
> and I'm going to walk all five steps, because the fourth one is where this system earns
> its money."

### Step 1 — What to make

**Say:**

> "Choose the approved Master Batch Record. Paracetamol 500mg, version 3.2, effective
> from 15 July."

**Do:** Point at the v3.3 row, which shows *Under review* and *Cannot be used*.

> "Version 3.3 exists — it's under review. It is **not selectable**. Issuing work against
> an unapproved master is one of the most common inspection findings there is, so the
> system doesn't offer it and then warn you. It simply doesn't offer it."

**Do:** Click **Continue**.

### Step 2 — Batch details

**Say:**

> "Batch number B-2026-0143. Note it's greyed out — assigned by the system in sequence.
> You cannot type it, reuse it or skip it. A gap in that sequence is a question you'd
> have to answer to an inspector."

**Do:** Clear the **Batch size** field and click **Continue**.

> "Refused, as always."

**Do:** Put `250,000` back. Open the **Site and line** dropdown.

> "One thing worth noticing — Line D is in the list, and it's flagged as not qualified
> for this product. It appears because it physically exists. If I pick it, step 4 will
> refuse the order and name the missing qualification. The system doesn't hide options.
> It explains refusals."

**Do:** Leave Line A selected. Click **Continue**.

### Step 3 — Materials & lots

**Say:**

> "Four material lines, each getting a specific lot. This screen is where **genealogy** is
> created — the permanent link between this batch and these physical lots. Written now,
> never changed."

**Do:** Point at the checks list at the bottom.

> "And four things get checked on every lot before it can be allocated: approved status,
> expiry valid through the *end* of the run rather than just today, sufficient quantity,
> and that the lot is actually the material the BOM names."

**Do:** Click **Continue**.

### Step 4 — Readiness (the moment)

**Say — slow down here:**

> "And this is it. Everything is filled in correctly, and the system will not issue the
> batch."

**Do:** Read the red banner aloud, verbatim.

> "*This batch cannot be issued — Line A: no line clearance recorded since the previous
> product.*
>
> There is no override. There is no 'proceed anyway'. There is no supervisor password
> that skips this. If the previous product hasn't been cleared off that line, you cannot
> start the next one on it — because that's how cross-contamination happens, and because
> it's what 211.130 requires.
>
> This is the difference between software that documents your process and software that
> enforces it. Almost every eBMR you'll be shown does the first. Ask specifically about
> the second."

**Do:** Click **Recheck readiness**. The status flips to *Cleared*.

> "A. Desai performed and signed the line clearance at 08:52 — previous product removed,
> line inspected, documented. Rechecking reads **that signed record**. It doesn't take
> anyone's word for it, and it doesn't just clear because someone clicked a button."

**Do:** Point at the panel below.

> "And everything on this list gets checked twice — once now, and again when an operator
> opens each step. A balance that goes out of calibration overnight stops the work in the
> morning, even though this screen passed yesterday."

**Do:** Click **Continue**.

### Step 5 — Review & issue

**Do:** Before touching anything, point at the **Sign and issue batch** button — greyed
out, with a lock icon and a reason beneath it.

> "Notice it was locked until readiness cleared, and it told you why."

**Do:** Point at the summary grid, then the signature block.

> "Everything about to be committed, on one screen. Then the signature — and note the
> **meaning** dropdown. A signature without a stated meaning is worthless; the record has
> to say what the person was attesting to."

**Do:** Click **Sign and issue batch** with the PIN field empty.

> "No PIN, no signature."

**Do:** Enter a PIN. Click **Sign and issue batch**.

**Say:**

> "And there it is. B-2026-0143, 250,000 tablets, issued by M. Chen, ready to execute.
> It's now on the control board and in the operator's task inbox.
>
> From this moment it's a live regulated record. It can be executed, paused, held or
> cancelled — but never deleted."

**Do:** Scroll to the five-step table at the bottom.

> "If you take one screen away from today, take this table. Each step, the question it
> answers, and what goes wrong without it. That last column is essentially a list of
> inspection findings."

### 3.6 The same wizard in the other two profiles

> **Skip if short on time — but mention it exists.**

**Do:** Open `screens/md/production/new-batch.html`.

> "Same five steps, medical device. It's a **build order**, not a batch. It produces a
> serial range, SN-88500 to 88999. The master is a **Device Master Record revision**, and
> each unit gets its own Device History Record.
>
> And the blocker is different — remember EQ-7710, the overdue leak tester from setup?
> That's what stops this one."

**Do:** Open `screens/ddcp/combination/new-batch.html`.

> "And combination products. A **final assembly order** that consumes a finished drug
> batch *and* a finished device lot, each already released under its own rules. Part 4
> requires both rule-sets satisfied — you can't release on the strength of one.
>
> Here the blocker is that the drug constituent batch hasn't been released by the Quality
> Unit yet. You cannot assemble a product around a batch that's still under review."

---

# ACT 4 — When things go wrong (12 minutes)

**Say:**

> "Any system can handle the happy path. Here's the part that actually decides whether
> your team will use it."

### 4.1 Guided execution

**Screen:** `screens/ph/production/execution.html`

> "This is the operator's view — the batch record itself, step by step. Dispensing is
> complete and independently checked. Granulation is in progress. The rest are locked
> until the ones above them are done. You cannot skip ahead."

### 4.2 Dispensing — the tolerance failure

**Screen:** `screens/ph/production/dispensing.html`

**Say:**

> "Remember the tolerance column from the BOM? Magnesium stearate, 1.800 kg ±5%.
> The operator weighed **1.895 kg**. That's +5.3%.
>
> Look at what the system does. The value is shown — it isn't thrown away, because
> discarding an inconvenient measurement is itself a data-integrity problem. But it's
> marked over tolerance, and the step will not accept it."

### 4.3 The independent check

**Screen:** `screens/ph/production/verification.html`

> "The two-person rule from the roles matrix, in practice. J. Rao dispensed. The system
> requires a different person, with the checker role, to verify — and it will not offer
> J. Rao's name."

### 4.4 An out-of-spec result

**Screen:** `screens/ph/production/inspection.html`

> "In-process testing. Friability came back 1.34% against a limit of 1.0%. Three other
> tests passed. This one result opens a deviation and holds the batch."

### 4.5 The deviation

**Screen:** `screens/ph/quality/deviation.html`

> "DEV-0517. Every deviation carries the same structure: what happened, what the impact
> is, what the root cause was, and what's being done about it. The batch cannot be
> released while it's open."

### 4.6 Release

**Screen:** `screens/ph/quality/release.html`

**Say:**

> "And the last signature. Priya Nair, QA Approver, Quality Unit — release under
> 211.22.
>
> Look at what she has to have in front of her: the executed record, the yield
> reconciliation, every deviation closed, every lab result reviewed. If any one of those
> is outstanding, the release button stays locked with the reason shown — the same
> pattern as step 4 of the wizard."

### 4.7 The audit trail

**Screen:** `screens/ph/records/timeline.html`

**Say — good closing note:**

> "And this is what an inspector actually asks for. Every entry, every signature, every
> correction, in order, with who and when.
>
> Note that corrections appear as *new entries with a reason* — nothing is ever
> overwritten. If someone recorded a wrong value at 10:14 and fixed it at 10:16, both are
> here, and so is why.
>
> That's the whole argument for the system in one screen."

---

# Closing (3 minutes)

**Screen:** back to `screens/001-sign-in.html`

**Say:**

> "So — three regulated profiles that never blend, an organisation you configure once in
> about half a day, and a system that refuses work it shouldn't allow rather than
> recording that you did it anyway.
>
> What you've seen today is the complete interface. It's a design preview — nothing is
> stored — but every screen, every state and every refusal is exactly what the built
> system does."

---

# Appendix A — Handling the questions you will get

**"Can we override the blocks?"**
> Some, with authority and a recorded reason — those appear as exceptions in the record.
> Others, never: an unapproved master, an uncalibrated instrument, an untrained operator,
> the same person performing and verifying. If those were overridable they wouldn't be
> controls.

**"What if the system is down mid-batch?"**
> Beyond today's scope — that's the business continuity and paper-fallback procedure. Note
> it and come back to it; don't improvise an answer.

**"Can we change the screens?"**
> Layout, terminology and which fields appear, yes. The control behaviour — what the
> system refuses — is not configurable per site, deliberately.

**"How long to implement?"**
> Don't answer from this demo. Setup is half a day per site; implementation, validation
> and training are a separate conversation.

**"Is this validated / 21 CFR Part 11 compliant?"**
> The design is built to those requirements. Compliance is a property of a validated
> installation, not of software in the abstract — say exactly that, and don't claim more.

**"It's a mockup, so how do I know it works?"**
> Fair question and worth answering directly: everything you clicked today — the
> validation, the refusals, the locked button, the totals — is real behaviour in the
> interface. What's absent is the database behind it.

---

# Appendix B — Screen index

**Onboarding** — `screens/onboarding/`
`welcome.html` · `first-run.html` · `new-user.html`

**Setup** — `screens/setup/`
`checklist.html` · `company.html` · `users.html` · `roles.html` ·
`products.html` · `materials.html` · `bom.html` · `equipment.html`

**Pharmaceutical** — `screens/ph/` — 33 screens
`menu.html`, `my-work/`, `masters/` (6), `production/` (16), `quality/` (3),
`records/` (3), `admin/` (4)

**Medical Device** — `screens/md/` — 32 screens
same structure; `quality/` is Device Quality with nonconformance in place of deviation

**Combination Product** — `screens/ddcp/` — 17 screens
`menu.html`, `my-work/`, `combination/` (9), `records/` (3), `admin/` (4)

**Deeper reference:** `MD-GUIDE-GUJARATI.md`, `PH-GUIDE-GUJARATI.md`,
`DDCP-GUIDE-GUJARATI.md`, `DDCP-GUIDE.md`, `SYSTEM-WALKTHROUGH.md`,
and `dev-catalogue.html` for a clickable index of every screen.

---

# Appendix C — Ninety-second version

If you get cut to two minutes, open exactly two screens:

1. `screens/setup/bom.html` — point at the tolerance column.
   *"1.800 kg, ±5%. Weigh 1.895 and the system refuses it."*
2. `screens/ph/production/new-batch.html`, step 4 — point at the red banner.
   *"Everything is filled in correctly and it still won't issue the batch, because the
   line clearance isn't recorded. No override exists."*

That is the entire product argument.
