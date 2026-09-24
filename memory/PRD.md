# College Event Management System — Product Requirements

## Original problem statement
Build a production-ready College Event Management System for a TY BSc IT/CA academic project with Admin and Student roles, secure authentication, full event lifecycle (categories, registrations, attendance, certificates), announcements, reports, profile, search/filters and database-backed APIs.

## Architecture
- **Backend**: FastAPI (`/app/backend/server.py`) — single file with clear module sections (auth, events, categories, registrations/attendance, certificates, announcements, users, profile, reports).
- **Frontend**: React (`/app/frontend/src/App.js`) with routed sidebar navigation, screens per module, and a shared Layout.
- **Database**: MongoDB via Motor (async). Collections model the relational schema described in `server.py` docstring; unique indexes replicate SQL constraints (`users.email`, `categories.name`, `registrations(event_id,user_id)`, `attendance.registration_id`).
- **Auth**: bcrypt password hashing, JWT in an HttpOnly cookie, 5-attempt / 15-min soft lockout.

## Personas
- Admin: manages events, categories, users/roles, registrations, attendance, announcements and reports.
- Student: browses events, registers/unregisters, updates profile, downloads participation certificates.

## Implemented (2026-09-23)
- Auth: register/login/logout/me with cookie sessions, role checks, seeded demo accounts, failed-login lockout.
- Events: CRUD (create/edit/delete), search + category + status filters, capacity + duplicate + past-event validation.
- Categories: CRUD (admin) with unique-name index.
- Registrations: create/cancel, admin approve/reject.
- Attendance: admin-only marking; only approved registrations eligible.
- Certificates: eligibility list (per role) and printable HTML certificate download.
- Announcements: admin create/delete; students view.
- People/Users: admin list, change role, delete (with cascade of their registrations).
- Profile: student/admin edit name/department/phone.
- Reports: event-wise registration, approved, pending, attended counts with date-range filter.
- UI: sidebar nav, topbar, cards, tables, modals, filters, empty/loading/error states, `data-testid` on interactive controls.

## Business rules
- No duplicate registration (unique index + explicit check).
- No registration for past events (server compares ISO date strings).
- Capacity enforced.
- Attendance only for approved registrations.
- Certificate available only when attendance = present.
- Admin routes protected via `admin_only` dependency.

## Backlog (P1/P2)
- P1: Event image upload using object storage instead of URL.
- P1: Email notification when a registration is approved.
- P2: Chart-based analytics on Reports page.
- P2: Bulk attendance import for large events.

## Remaining next tasks
1. Add object-storage-backed image upload.
2. Add email/SMS notifications.
3. Deployment health-check when the user is ready to publish.
