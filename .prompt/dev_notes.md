## 2025-11-08 Session Notes

- Clarified Campus Resource Hub scope and compliance with AiDD 2025 baseline.
- Generated project skeleton plan covering Flask MVC, DAL, and testing layers.
- Outlined data schema with role-based access, booking workflows, and review constraints.
- Defined documentation deliverables and AI-first logging expectations.
- Planned secure authentication stack using bcrypt, CSRF, and session management.
- Established search, booking conflict detection, and admin moderation requirements.
- Captured deployment pipeline targets for Render with Gunicorn entrypoint alignment.
- Identified pytest coverage areas for auth, DAL, booking conflicts, and search filters.
- Reviewed accessibility and Bootstrap 5 theming guidelines for UI deliverables.
- Logged seed data expectations to showcase core user journeys end-to-end.

Reflection: Validation hinges on enforcing parameterized queries, WTForms validation, and pytest scenarios that simulate booking conflicts, search filters, and role-guarded flows. Ethical use remains central—seed content avoids real student data, uploads are sanitized, and audit trails via admin logs encourage responsible oversight.

---

## 2025-11-11 Iteration Notes

- Added schema columns for `requires_approval`, `approval_notes`, and threaded messaging with indexes to keep queries performant.
- Refactored DAOs to validate role assignments, persist activation toggles, and expose structured booking approval helpers.
- Implemented new role decorators plus admin/staff/student guardrails across bookings, messaging, and moderation routes.
- Delivered pending-approval workflows with owner/admin queues, note capture, and auto-approval for unrestricted resources.
- Rebuilt messaging into thread-aware pages with context metadata, admin inbox views, and 6-second polling via `main.js`.
- Introduced local SVG placeholders and a Jinja macro so every resource image stays on-disk while preserving Bootstrap light styling.
- Expanded seeds to include 1 admin, 2 staff, 3 students, mixed resources, sample bookings, and multi-context threads.
- Updated pytest suite and fixtures to cover RBAC, booking conflicts, DAL approvals, search exclusions, and thread permissions.
- Added navigation links and UI badges for approvals/messages, improving discoverability for staff and admins.
- Documented iteration outcomes in the README and ensured AI logs capture prompt + verification rationale.

Validation & Ethics: Verified changes by running the augmented pytest suite, spot-checking conflict scenarios, and manually exercising approval/messaging flows in dev. Reinitializing the SQLite DB via `flask --app src.app init-db` + `python -m src.data_access.seed` aligns state with the new schema. Ethical considerations centered on least-privilege access, transparent admin logging, sanitized sample data, and ensuring messaging updates respect participant privacy boundaries.
