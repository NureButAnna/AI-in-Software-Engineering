# PaperTrail - approved low-fidelity design brief v1.1

## Purpose and scope

Internal desktop web application "PaperTrail" for personal bureaucratic case and document management. Scope includes US-01 to US-10: authentication, managing cases, documents (with files), institution contacts, checklists, and reminders. One role: User (sees only their own data). No AI features are included in this release.

## Design constraints

Create editable native Figma layers on one page. Use grayscale, low-fidelity, readable hierarchy, reusable local components, and Auto Layout where practical. Keep annotations outside product frames. Do not add page icons, decorative square placeholders, or bulk actions. Do not build prototype interactions. Interface language should be Ukrainian.

## Canonical screens and states

Use the following exact IDs for product screens (S), states (ST), and modals (M):

- **S-01 Registration:** Email, Password, Register action. (Empty/Error state: MSG-01 to MSG-05 next to fields).
- **S-02 Login:** Email, Password, Login action. (Error state: ST-02 general login error MSG-06). ST-01: Success message "Акаунт створено. Увійдіть."
- **S-03 Dashboard:** Shows 3 blocks: "Прострочені" (Overdue cases), "Найближчі" (Upcoming cases), and Reminders (date <= today). ST-04: Empty state for blocks without relevant records (MSG-25, MSG-26, MSG-27).
- **S-04 Cases List:** Shows Case Title, Status, Deadline. Sorted by deadline (closest first), cases without deadline at the bottom. ST-03: Empty list (MSG-21). Action: Create case.
- **S-05 Case Details:** Title, Status (C-05), Deadline, Dates, related Documents, Institutions, Checklist (C-06 tasks). Actions: Edit case, Delete case, Change status, Add task.
- **S-06 Documents List:** Document Title, Date received. ST-06: Empty list (MSG-22).
- **S-07 Document Details:** Title, Number, Issuer, Date received, Expiration date, related cases, File status (C-01 to C-04). Action: Download file.
- **S-08 Institutions List:** Institution name and contacts. ST-07: Empty list (MSG-23).
- **S-09 Reminders List:** Text, Date, Related case. ST-08: Empty list (MSG-24).

### Overlays and Modals (M)

- **M-01 Case Form:** Title (required), Deadline (optional).
- **M-02 Document Form:** Title (required), Date received (required), Number, Issuer, Expiration date, File attachment (C-01 to C-04).
- **M-03 Institution Form:** Title (required), Email, Phone, Address.
- **M-04 Reminder Form:** Text (required), Date (required), related case.
- **M-05 Delete Confirmation:** Record name, consequences, "Cancel", "Delete" actions.
- **M-06 Attach Institution:** Select an existing institution.

## Controls, Permissions and File States

- **File States (C-01 to C-04):** C-01 "Немає файлу" (No file). C-02 "Завантажується" (Loading). C-03 "Прикріплено" (Attached) with file name and Download action. C-04 "Помилка" (Error) for format or >5MB limits.
- **Status Transitions (C-05):** Preparing, Submitted, In Review, Approved, Rejected, Cancelled. User can change from any status to any status.
- **Checklist Items (C-06):** Each checklist item consists of:
  - A checkbox showing completion state (unchecked = active/not done, checked = done).
  - Task title text (strike-through when checked).
  - A delete action/icon for each item.
  - Inline input field with an "Add" button (placeholder: "Назва задачі...") and error label MSG-11 below if empty.

## Exact UI Messages & Error Copy (MSG Catalog)

- **MSG-01 (Empty Email):** "Вкажіть email."
- **MSG-02 (Invalid Email):** "Вкажіть email у правильному форматі."
- **MSG-03 (Email Exists):** "Цей email уже зареєстровано."
- **MSG-04 (Empty Password):** "Вкажіть пароль."
- **MSG-05 (Short Password):** "Пароль має містити щонайменше 8 символів."
- **MSG-06 (Login Failed):** "Не вдалося увійти. Перевірте email і пароль."
- **MSG-11 (Empty Task):** "Вкажіть назву задачі."
- **MSG-14 (Invalid Format):** "Формат файлу не підтримується. Дозволені: PDF, JPG/JPEG, PNG, DOCX, TXT, XLSX, P7S."
- **MSG-15 (File > 5MB):** "Файл перевищує 5 МБ. Виберіть менший файл."
- **MSG-19 (Success Reg):** "Акаунт створено. Увійдіть."
- **MSG-20 (Success Save Toast):** "Збережено"

## Empty State Messages

- **MSG-21 (Cases Empty, S-04 / ST-03):** "Справ поки немає." (with CTA button: "Створити справу")
- **MSG-22 (Docs Empty, S-06 / ST-06):** "Документів поки немає." (with CTA button: "Створити документ")
- **MSG-23 (Institutions Empty, S-08 / ST-07):** "Установ поки немає." (with CTA button: "Створити установу")
- **MSG-24 (Reminders Empty, S-09 / ST-08):** "Нагадувань поки немає." (with CTA button: "Створити нагадування")
- **MSG-25 (Overdue Cases Empty, S-03):** "Прострочених справ немає."
- **MSG-26 (Upcoming Cases Empty, S-03):** "Найближчих справ немає."
- **MSG-27 (Reminders Empty, S-03):** "Актуальних нагадувань немає."

## Important Predicates (Urgent Rules)

- **Overdue:** Deadline < today AND Status is NOT (Approved, Rejected, Cancelled).
- **Upcoming:** Deadline between today and +14 days AND Status is NOT (Approved, Rejected, Cancelled).
- Note: Cases without a deadline are excluded from both blocks.

## Sample Data for Canonical Frames

- Case 1: "Оформлення візи", In Review, Deadline: Tomorrow. (Appears in Upcoming).
- Case 2: "Вступ до університету", Preparing, Deadline: Yesterday. (Appears in Overdue).
- Case 3: "Отримання довідки", Approved, Deadline: Yesterday. (Excluded from urgent blocks).
- Document 1: "Паспорт", File: "passport_scan.pdf" (Attached).
- Reminder 1: "Зателефонувати до посольства", Date: Today. (Appears on S-03).

## Exclusions

No file previews, no global search, no filters or sorting toggles. No custom statuses. No integrations, no mobile app screens. No AI recommendations.

## Acceptance Checklist

In your response report: list created frames, actual reusable components, and unrepresented rules. A static wireframe does not prove server permissions or file security.
