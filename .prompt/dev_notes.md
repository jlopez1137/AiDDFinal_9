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

---

## C.7 Reflection Prompts

### 10. How did AI tools shape your design or coding decisions?

AI tools, particularly Cursor and similar AI-assisted development environments, significantly influenced our architectural and implementation decisions throughout the Campus Resource Hub project. 

**Architectural Patterns:** The AI tools helped us adopt and consistently apply the MVC (Model-View-Controller) pattern with a dedicated Data Access Layer (DAL). Through iterative prompting, we refined the separation of concerns—keeping controllers thin, DAOs focused on database interactions, and views handling presentation logic. This structure emerged from AI suggestions that consistently recommended this pattern for Flask applications, which led us to organize our codebase into `controllers/`, `data_access/`, `models/`, and `views/` directories.

**Security-First Approach:** AI tools reinforced security best practices early in the design phase. When we prompted for authentication, the AI consistently suggested bcrypt for password hashing, Flask-WTF for CSRF protection, and parameterized queries to prevent SQL injection. This influenced us to make security considerations foundational rather than afterthoughts, shaping decisions like strict file upload validation, role-based access control decorators, and session management strategies.

**Rapid Prototyping and Iteration:** The ability to generate boilerplate code—blueprint registrations, seed data structures, pytest fixtures—allowed us to iterate faster on core business logic. However, this speed also shaped our verification process, as we learned to be more systematic about reviewing AI-generated code rather than accepting it blindly.

**Testing Strategy:** AI suggestions about pytest structure and test coverage patterns influenced our decision to create comprehensive test suites for authentication, booking conflicts, DAL operations, and search filters. The AI helped us understand edge cases we might have missed initially, such as concurrent booking scenarios and role permission boundaries.

### 11. What did you learn about verifying and improving AI-generated outputs?

Verifying AI-generated code became a critical skill, and we developed a systematic approach through trial and error:

**Multi-Layer Verification:** We learned that AI code needs verification at multiple levels:
- **Syntactic correctness:** Running code to catch immediate errors (type hints, imports, syntax)
- **Functional correctness:** Executing pytest suites to verify behavior matches requirements
- **Security correctness:** Manual review of security-sensitive areas (authentication, SQL queries, file uploads)
- **Architectural consistency:** Ensuring new code follows established patterns (DAL usage, decorator application, error handling)

**Reviewing AI-Suggested Patterns:** Initially, we accepted AI suggestions for decorator implementations and database queries without deep review. This led to issues where some decorators didn't properly integrate with Flask-Login's session management. We learned to test decorators in isolation and verify they work correctly with the authentication flow before integration.

**Iterative Refinement:** We discovered that AI tools are better at generating initial implementations than perfect solutions. For example, the initial threaded messaging implementation required multiple refinement passes—first for basic functionality, then for admin inbox views, then for proper context metadata. Each iteration involved manual testing and prompting for improvements based on discovered edge cases.

**Documentation as Verification Tool:** Maintaining `.prompt/dev_notes.md` and marking `# AI Contribution` comments helped us track what was AI-generated, making it easier to review and verify later. This documentation practice became part of our verification workflow.

**Domain-Specific Knowledge:** We learned that AI tools excel at general patterns but sometimes miss domain-specific nuances. For booking conflict detection, the AI initially suggested simple date overlap checks, but we had to refine the logic to account for time boundaries and resource-specific approval workflows. This taught us that domain expertise remains essential for validating AI suggestions.

### 12. What ethical or managerial considerations emerged from using AI in your project?

Several ethical and managerial considerations emerged that are relevant to academic and professional contexts:

**Data Privacy and Sample Data:** We made deliberate choices to avoid using real student data in seed scripts, even though it would have been easier to use actual names and email addresses. This reflects ethical considerations around student privacy and FERPA compliance. The AI tools, while helpful in generating seed data structures, didn't inherently enforce these ethical boundaries—we had to consciously decide to sanitize all sample data.

**Transparency and Attribution:** We implemented `# AI Contribution` comments to maintain transparency about which code was AI-assisted versus manually written. However, this raised questions about how to balance attribution without over-complicating code comments. In a team environment, this transparency is crucial for code review and knowledge transfer.

**Audit Trails and Accountability:** The admin logging and audit trail features took on added importance because we recognized that AI-generated code could introduce subtle bugs or security vulnerabilities. Having clear audit logs helps identify when AI-generated features behave unexpectedly in production. Managerially, this suggests that projects using AI tools should invest more heavily in observability and logging.

**Intellectual Property and Academic Integrity:** Using AI tools raised questions about what constitutes "original work" in an academic context. We addressed this by treating AI as a collaborative tool rather than a replacement for learning, ensuring we understood every line of AI-generated code before accepting it. This aligns with academic integrity expectations while recognizing that AI tools are becoming standard in professional development.

**Bias and Fairness:** When implementing role-based access control, we had to carefully review AI-suggested permission structures to ensure they didn't inadvertently create barriers or biases. For example, initial AI suggestions for admin dashboards assumed single-owner approval workflows; we refined these to support multi-staff resource management scenarios.

**Skill Development Concerns:** There's a managerial risk that over-reliance on AI tools could erode fundamental programming skills. We balanced this by ensuring team members could explain every component, even if initially AI-generated, and by maintaining comprehensive test coverage that required understanding the underlying logic.

### 13. How might these tools change the role of a business technologist or product manager in the next five years?

AI-assisted development tools will fundamentally shift the responsibilities and required skills of business technologists and product managers:

**From Specification to Validation:** Product managers will spend less time on detailed technical specifications that AI can infer from high-level requirements. Instead, they'll focus more on validation—ensuring AI-generated solutions actually solve the right problems and meet user needs. The emphasis shifts from "how to build" to "what to validate and when to reject AI suggestions."

**Rapid Prototyping and Market Testing:** Business technologists can prototype and test ideas much faster, potentially reducing the time from concept to MVP from weeks to days. This means PMs will need to be more agile in gathering user feedback and making pivot decisions. The feedback loop becomes shorter, requiring faster decision-making and more iterative product thinking.

**Domain Expertise as Differentiator:** As AI tools handle more implementation details, product managers with deep domain expertise (understanding user workflows, business constraints, regulatory requirements) will become more valuable. The PM's role shifts toward being a domain expert who can guide AI tools toward the right solutions rather than a technical generalist.

**Quality Assurance and Risk Management:** With AI generating code quickly, the PM role will emphasize risk assessment and quality assurance. Product managers will need to develop frameworks for evaluating AI-generated features—understanding what requires thorough testing, what needs human review, and how to balance speed with quality. This includes security reviews, compliance checks, and user experience validation.

**Prompt Engineering as Core Skill:** Business technologists and PMs will need to become proficient in prompt engineering—articulating requirements in ways that guide AI tools effectively. This is different from traditional requirements writing; it requires understanding how AI tools interpret context and being able to structure prompts that lead to better outcomes.

**Ethical Oversight and Governance:** Product managers will increasingly serve as ethical gatekeepers, ensuring AI-generated features don't introduce bias, privacy violations, or other ethical concerns. This requires staying current on AI ethics, regulatory requirements, and organizational policies around AI use.

**Strategic Thinking Over Tactical Execution:** With AI handling more implementation details, PMs will focus more on strategic product vision, market analysis, and long-term roadmapping. The tactical coordination of development sprints becomes less critical when AI can generate implementations quickly; the strategic questions of "what should we build and why" become more central.

**Collaboration with AI as a Team Member:** PMs will need to learn to work with AI as a collaborative team member—knowing when to trust AI suggestions, when to push back, and how to integrate AI-generated features into coherent product experiences. This is similar to learning to work with new team members, but with the added complexity that AI tools can generate code faster than humans but lack context awareness.