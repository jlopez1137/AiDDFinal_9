## Golden Prompt #1 — Campus Resource Hub Master Prompt

🧠 Cursor 2.0 Master Prompt — Campus Resource Hub (Flask MVC + Tests + AI-First + Deployment)

[Placeholder for prompt details, retained verbatim in repository documentation.]

---

## Golden Prompt #2 — Placeholder

Reserved for future high-impact prompt. Add summary, context, and outcomes once defined.

---

## Golden Prompt — Admin Role, Approvals, Threaded Messaging, Local Assets, UI Polish

Golden Prompt — Admin Role, Approvals, Threaded Messaging, Local Assets, UI Polish



Instruction level: High.

Scope: Modify existing files only. Do not create any new documentation files. You may create code, templates, tests, and SVG assets.

AI logs: Append to .prompt/dev_notes.md and .prompt/golden_prompts.md only.



0) Repository invariants



Use the current project structure and naming. Before editing a file, search for it and confirm the path. If a file is absent, create it in the most consistent location under /src or /tests only.



Documentation constraint: Do not create any new docs files. The only doc changes allowed are:



Append a “What changed” section to the existing README.md.



Append to .prompt/dev_notes.md.



Append to .prompt/golden_prompts.md with this exact prompt under a new heading.



UI must remain professional light mode with Bootstrap 5. No dark mode and no remote images.



1) Roles and access control



Ensure users.role supports exactly student, staff, and admin at both database and application validation layers.



Add or confirm decorators:



@login_required



@role_required('admin')



@role_in(['staff','admin'])



Enforce across routes:



Admin-only: admin dashboard, global booking approvals, global messaging inbox, user moderation actions.



Staff: manage their own resources; approve bookings for their resources; participate in relevant threads.



Student: request bookings; message within their threads; review after completion.



2) Database and DAO changes



Modify the existing schema and DAO code in place (no new docs files). If you maintain campus_resource_hub_schema.sql, update it atomically.



Schema adjustments:



users: add is_active INTEGER NOT NULL DEFAULT 1.



resources: add requires_approval INTEGER NOT NULL DEFAULT 0.



bookings: ensure statuses include pending, approved, rejected, cancelled, completed. Add approval_notes TEXT NULL.



Messaging becomes threaded:



Create table threads(thread_id PK, context_type TEXT CHECK IN ('resource','booking','general'), context_id INTEGER, created_by INTEGER FK users, created_at DATETIME DEFAULT CURRENT_TIMESTAMP).



Update messages so thread_id is NOT NULL and FK → threads.thread_id. Keep sender_id, receiver_id, content, timestamp.



Indexes: threads(context_type, context_id), messages(thread_id, timestamp).



DAO functions to add/extend (keep names consistent with your codebase):



Users: set_role(user_id, role), deactivate_user(user_id), activate_user(user_id).



Resources: CRUD to include requires_approval.



Bookings:



has_conflict(resource_id, start, end) counts pending or approved as blocking.



create_booking(...) sets pending if requires_approval=1, otherwise auto-approve when no conflict.



approve_booking(booking_id, approver_id, notes), reject_booking(...), cancel_booking(...), complete_booking(...) set updated_at and optional approval_notes.



Threads/Messages:



create_thread(context_type, context_id, created_by)



post_message(thread_id, sender_id, receiver_id, content)



list_threads_for_admin() newest first by last message time



list_threads_for_user(user_id) where user is participant



get_thread(thread_id), get_messages(thread_id)



Data migration strategy: If you detect existing DBs at runtime, provide a safe re-init path via a dev command or README note.



3) Booking approval workflow



Resource toggle: requires_approval in the resource form and UI.



Flow:



Student requests → pending.



If resource requires approval, staff owner or admin must approve or reject with optional approval_notes.



If not required, auto-approve unless conflict.



Conflicts are based on pending or approved bookings only.



Permissions: only owner (staff) of the resource or an admin can approve/reject.



UI:



Resource detail: shows whether approval is required.



My Bookings: displays current status.



Admin dashboard + Staff owner view: pending approvals queue with Approve/Reject buttons and notes field.



4) Threaded messaging with Admin inbox



Threads: resource, booking, or general contexts.



Admin inbox:



/admin/threads shows all threads with context and last activity.



/admin/threads/<id> full thread with reply box.



User view:



/messages lists a user’s threads with unread indicators and timestamps.



/messages/<thread_id> shows messages and a compose form.



Near-real-time: implement simple polling every ~6 seconds via a small JS snippet that calls GET /messages/<thread_id>/since?ts= to fetch new messages.



Permissions: only participants, resource owner, or admins can read/write within a thread.



5) UI polish and local-only assets



Remove any remote images. No <img> tags should point to external URLs.



Replace with local SVG placeholders stored in /src/static/img/. You may add multiple SVGs for variety (e.g., resource_generic.svg, room.svg, equipment.svg).



Provide a Jinja macro that returns a placeholder path when a resource has no image.



Use Bootstrap 5 light theme only. Improve spacing, headings, labels, and badges.



Add a small “Requires Approval” badge on cards and detail pages.



Ensure accessible form labels and keyboard focus styles.



6) Tests (pytest)



Update and add tests without adding docs:



test_auth.py: admin routes require admin; deactivated user cannot log in.



test_booking_conflicts.py: conflicts blocked by pending/approved; auto-approve behavior for non-restricted.



test_dal.py: restricted resource produces pending booking; approve and reject paths with approval_notes.



test_search_filters.py: search/filter exclude draft/archived; show “requires approval” badge condition.



test_threads.py: create thread, post messages, list for admin and for user; permission checks deny non-participants.



Provide necessary fixtures in conftest.py:



One admin, one staff, one student



One restricted resource by staff



One pending booking on that resource



At least one booking thread with messages



7) Seeds



Adjust seed.py to create:



Users: 1 admin, 2 staff, 3 students, all is_active=1



Resources: a mix with requires_approval=0 and 1



Bookings: pending, approved, and completed examples



Threads: a booking-context thread and a general thread with a few messages



All resource images set to local SVGs or left null to trigger placeholders



8) README edits (append only)



Append a short “What changed in this iteration” section describing:



Admin role and permissions



Restricted resource approval workflow



Threaded messaging + Admin inbox with polling



Local-only SVG placeholders and light UI polish



How to re-init the SQLite DB for schema changes



Seed accounts and roles for quick testing



9) AI log updates (append only)



Append the following to .prompt/golden_prompts.md under a new heading:



## Golden Prompt — Admin Role, Approvals, Threaded Messaging, Local Assets, UI Polish

[Paste this entire prompt verbatim here]





Append 8–12 bullet points to .prompt/dev_notes.md that summarize what changed and how you verified it, plus a short paragraph on validation and ethics.



10) Acceptance criteria (must pass before you stop)



Admin can view pending approvals, approve/reject with notes, moderate users, and see a global threads inbox.



Restricted bookings default to pending; non-restricted auto-approve when no conflict.



Conflict logic blocks overlaps for pending and approved states only.



Users see only their threads; admins see all; staff see threads connected to their resources.



No external images referenced anywhere; all visuals work with local SVGs.



All tests pass. README has the appended change log. AI logs updated by appending, not by creating new files.



Now implement these changes across controllers, DAOs, templates, static assets, tests, seed data, and README. Do not create any new documentation files beyond appending to .prompt/dev_notes.md and .prompt/golden_prompts.md.

---

## Golden Prompt #3 — Placeholder

Reserved for future high-impact prompt. Add summary, context, and outcomes once defined.

