# AI Interaction Log: Design Review & Defect Triage for PaperTrail

## 1. Metadata and Session Context

- **Project:** PaperTrail (Desktop Web App for Personal Bureaucratic Case & Document Management)
- **Course / Assignment Module:** Practical Assignment, Steps 13–16 (F1 Generation, Manual Review, Defect Log & F2 Correction)
- **Primary AI Model:** Gemini 3 Flash (Web, Paid Tier)
- **Figma AI Agent:** Figma Agent (Native LLM/Design Agent in Figma Design Desktop)
- **Session Date:** October 21–22, 2026
- **Base Artifacts Evaluated:**
  - `05_Figma_Brief_v1.1.md` (Approved Canonical Design Brief v1.1)
  - `PaperTrail_Screen_Contracts_G3.docx` (Screen Contracts Specification for Release MVP)
  - `02_Screen_Map_v0.2.docx` (Screen Map v0.2)
  - `BEFORE_REVIEW.fig` (Pre-review raw export of F1 Agent canvas)
  - `Defect_Log_PaperTrail.docx` (Initial student defect log)
  - `Change_Report.docx` (Change report returned by Figma Agent)

---

## 2. Interactive Dialogue Log (Verbatim Sequence)

### Link to the chat:

- https://share.gemini.google/8MU83qv6pbxP

### User Prompt 1

> Привіт! Підкажи, у якому форматі краще оформити Defect Log, з пункту 14, для створеного дизайну проєкту PaperTrail ? Додаю design brief проєкта, пункт 14 та 13 методичних вказівок. 13. F1 — одна основна генерація... [додано текст методичних вказівок п. 13–14 та 05_Figma_Brief_v1.1.md]

### Assistant Response 1

- Recommended a structured 7-to-8 column table in Markdown/Word aligned with classification types (`DEF`, `UX`, `Q`) and priorities (P1, P2, P3).
- Provided concrete examples directly tracing PaperTrail constraints (Dashboard status predicates on `S-03`, removing square placeholder decoration on `S-04`, checklist strike-through in `C-06`, exact Ukrainian copy matching `MSG-06`, and isolating reviewer notes outside product frames).
- Emphasized preserving backup copy `BEFORE_REVIEW.fig` prior to any manual or automated edits.

---

### User Prompt 2

> Створіть, будь ласка, шаблон документа DefectLog у форматі .docx

### Assistant Response 2

- Generated `PaperTrail_Defect_Log_Template.docx` containing project metadata, classification guidelines, a prioritized defect register table with sample PaperTrail entries, and correction procedural rules.

---

### User Prompt 3

> Перевір та удоскональ виконання пункту 14, надаю дизайн згенерований Figma Agent та документи ( Screen Map, 05_Figma_Brief_v1.1.md /PaperTrail_Screen_Contracts_G3 ). [Вкладено BEFORE_REVIEW.fig, Defect_Log_PaperTrail.docx, PaperTrail_Screen_Contracts_G3.docx, 02_Screen_Map_v0.2.docx]

### Assistant Response 3

- Conducted deep audit of `Defect_Log_PaperTrail.docx` and identified critical issues:
  1. _Rule violation in `UX-02`:_ Proposing red color for error states violated the mandatory Grayscale Low-Fidelity constraint of the brief.
  2. _Defect in `UX-1`:_ Proposing removal of the "Змінити статус" button violated the core business requirement that status transitions (`C-05`) occur independently of the field editing form (`M-01`).
  3. _Unrepresented defects:_ Highlighted missing audit checks for overdue predicate violations on `S-03` (`Case 3: Approved` present), square icon placeholders, and checklist strike-through.
- Produced upgraded defect table aligning entries to P1/P2/P3 priority tiers.

---

### User Prompt 4

> Якщо це Error message, то потрібно виділяти червном кольором

### Assistant Response 4

- Explained the strict boundary between Low-Fidelity (Step 13–16) and High-Fidelity design phases.
- Cited `05_Figma_Brief_v1.1.md` (§Design constraints: _"Use grayscale, low-fidelity"_).
- Demonstrated how to highlight error states compliant with WCAG and Grayscale rules without color: 2px dark stroke (`#333333`), bold text (`#111111`), dedicated positioning under input (`C-07`), reserving semantic red for future High-Fi UI kits.

---

### User Prompt 5

> Перегляньте наступні пункти методичних вказівок для вирішення питання Error message. 5. F2 — перевірка + правки + звіт... [додано текст методичних вказівок п. 15–17]

### Assistant Response 5

- Verified clauses 15 (F2 prompt rules: _"Fix only evidence-backed noncompliance"_), 16 (Manual fallback without penalty), and 17 (Manual prototype wiring).
- Concluded that demanding red styling in F2 without brief support would be rejected by the automated agent and instructor as non-compliant.
- Recommended phrasing the defect as structural contrast enhancement (2px stroke / bold label in Grayscale) and logging colorization as an unresolved/future design item.

---

### User Prompt 6

> Таблиця Defect Log має містити такі поля: 1. Таблиця дефектів: ID | Тип / Severity | Локація (Screen / Frame / Layer) | Джерело (Source Rule / Brief ID) | Фактичний стан (Що згенеровано) | Очікуваний стан (Що має бути) | Необхідне виправлення

### Assistant Response 6

- Restructured the entire Defect Log into the requested 7-column schema across entries `DEF-01` to `DEF-08`, `Q-01`–`Q-02`, and `UX-01`–`UX-04`.
- Delivered `Defect_Log_PaperTrail_Upgraded.docx` containing fully populated evidence and precise corrective actions.

---

### User Prompt 7

> «Дій як UX/UI System Designer та експерт зі складання промтів для AI-інструментів у Figma. Перепиши англомовний текст промту F2 під мій новий проєкт PaperTrail...»

### Assistant Response 7

- Engineered an optimized, highly dense F2 prompt (~1900 chars) tailored strictly to PaperTrail rules (single user role, Ukrainian MSG copy, grayscale styling, S-03 predicates, S-05 status vs M-01 modal, checklist C-06 strike-through, row edit/delete actions, and automated Change Report generation).

---

### User Prompt 8

> Які сторінки потрібно обрати для редагування згідно створеного запиту?

### Assistant Response 8

- Specified exact target selection in Figma: product frames `S-01` through `S-09` plus `Local Components` (C-02, C-06, C-07, List Rows).
- Explicitly instructed to keep backup frame `BEFORE_REVIEW` and external annotations unselected.

---

### User Prompt 9

> Відповідь від Figma Agent: I stopped without making edits because the review checklist and the attached v1.1 contract have a blocking source mismatch... [Agent cited mismatch between brief v1.1 and references to G3/C-07]

### Assistant Response 9

- Analyzed Agent guardrail: Agent strictly enforces consistency with attached files. Because only `05_Figma_Brief_v1.1.md` was attached to Figma, the Agent flagged external document citations as unverified conflicts.
- Provided two execution routes:
  - _Option 1 (AI Retry):_ Direct confirmation prompt resolving source hierarchy and parameter values.
  - _Option 2 (Manual Fallback via Clause 16):_ Performing the 6 straightforward visual edits manually in 5 minutes without token waste or grade penalty.

---

### User Prompt 10

> Підкажи, як краще оформити Change Report + unresolved list з пункту 14

### Assistant Response 10

- Detailed the canonical structure required by Step 14:
  1. `Change Report Table` (`CHANGE-ID | Screen/layer | What changed | Why | Source rule`)
  2. `NOT REPRESENTED` (out-of-scope MVP items)
  3. `UNRESOLVED LIST` (architectural/relational ambiguities)
  4. `OUTSIDE STATIC-DESIGN VERIFICATION` (backend/runtime disclaimers).
- Provided complete populated sample for PaperTrail.

---

### User Prompt 11

> Як оформити unresolved list?

### Assistant Response 11

- Outlined both narrative and tabular formats for the Unresolved List, breaking down items `UNRES-01` to `UNRES-06` (unlink vs cascade delete, document linking modal, institution cardinality, initial task status, file re-upload semantics, list failure handling).

---

### User Prompt 12

> Сформуй, будь ласка, шаблони документів у форматі docx для Change Report та unresolved list

### Assistant Response 12

- Generated `PaperTrail_Change_Report_and_Unresolved_List.docx` with landscape A4 formatting, full tables, and compliance metadata.

---

### User Prompt 13

> Надаю change report від Figma Agent та defect report. Зафіксуйте, які дефекти залишились в uresolved list. [Вкладено Change_Report.docx з CH-01..CH-06 та Defect_Log_PaperTrail_Upgraded_2.docx]

### Assistant Response 13

- Cross-compared Agent edits against Defect Log:
  - _Resolved by Agent:_ `DEF-01`, `DEF-02` (links), `DEF-04`, `DEF-05`, `DEF-06` (edit/delete buttons & date formatting), `UX-02` (grayscale error stroke).
  - _Unresolved/Missed by Agent:_ `DEF-03` (Approved case remained in Overdue), `DEF-08` (C-06 strikethrough missing), `Q-01`/`Q-02` (linking/unlinking controls on S-05), `UX-01` (metadata card layout), `UX-03` (C-02 loading progress indicator).
- Drafted targeted `UNRESOLVED LIST` capturing residual items.

---

### User Prompt 14

> напишіть додатковий пункт для UNRESOLVED LIST, де показуєте (де і які) і вказуєте, хто і як (який запит або вручну) проблему виправляв і доказ виправлення - посилання на виправлений артефакт (документ) - макет фігми.

### Assistant Response 14

- Formulated subsection `3.1. Реєстр усунення залишкових дефектів через резервний маршрут (Manual Resolution)`.
- Documented manual fixes executed by reviewer (Бут Анна) under Clause 16:
  - `UNRES-01 (DEF-03)` resolved manually on `S-03` (removing Case 3);
  - `UNRES-02 (DEF-08)` resolved in master component `C-06` (setting text decoration to Strikethrough);
  - `UNRES-05 (UX-01)` resolved on `S-05` (Auto Layout card wrapper);
  - `UNRES-06 (UX-03)` resolved in component `C-02` (grayscale progress indicator).
- Linked proof of correction directly to `Wireframes_v2.fig` audited against `BEFORE_REVIEW.fig`.

---

### User Prompt 15

> напиши, будь ласка, промт для figma agent, щоб вирішити цю проблему: UNRES-05 Помилки списків (Copy)...

### Assistant Response 15

- Drafted a prompt instructing Figma Agent to build an explicit load error component (`List / Load Error State`) with retry actions, preventing the masking of read errors as empty lists.

---

### User Prompt 16

> додай будь ласка про додаткові екрани для помилок 404 та 500, також прибери з промта посилання на UNRES-05 і тд, бо окрім figma_brief ніяких більше документів не додавла до чату

### Assistant Response 16

- Cleaned the prompt of internal spec codes (`UNRES`, `G3`) to avoid agent rejection.
- Expanded the prompt scope to generate two dedicated desktop error screens:
  - `S-10 Not Found (404)` with primary action "На головну";
  - `S-11 Server Error (500)` with primary action "Оновити сторінку";
  - Preserved low-fidelity grayscale styling and strict annotation isolation on Canvas.

---

## 3. Audit Summary & Reproducibility Verification

1. **Model Reproducibility:** Every prompt and agent response sequence above details the progression from initial low-fidelity generation (F1) through defect triage (Clause 14), agent iteration (F2), and manual resolution fallback (Clause 16).
2. **Key Engineering Findings:**
   - LLM agents in design tools require explicit source hierarchy; referencing documents not attached in the agent context triggers safety halts.
   - Design constraints (e.g., Grayscale Low-Fidelity) must override generic UI intuitions (e.g., red text for errors) during initial wireframing stages.
   - The hybrid workflow (Agent iteration + Clause 16 manual spot correction) provides optimal token efficiency and 100% compliance with academic rubrics.
