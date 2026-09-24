# Database Schema

Database: **MongoDB** (database name from `DB_NAME`). Collections and indexes are created automatically on backend startup (`server.py` → `startup()`); there are no separate migration files.

All documents have an auto-generated `_id` (ObjectId) which is exposed to the API as a string `id`. Timestamps are ISO-8601 UTC strings.

## Collections

### users
| Field | Type | Notes |
| --- | --- | --- |
| name | string | |
| email | string | **unique index** |
| password_hash | string | bcrypt |
| role | string | `admin` \| `student` |
| department | string | |
| phone | string | |
| created_at | datetime | |

### categories
| Field | Type | Notes |
| --- | --- | --- |
| name | string | **unique index** |
| description | string | |
| created_at | datetime | |

### events
| Field | Type | Notes |
| --- | --- | --- |
| title | string | |
| description | string | |
| category | string | references `categories.name` |
| date | string (YYYY-MM-DD) | |
| time | string (HH:MM) | |
| venue | string | |
| capacity | int | max registrations |
| image | string (URL) | optional |
| status | string | `upcoming` \| `ongoing` \| `completed` \| `cancelled` |
| created_at | datetime | |

### registrations
| Field | Type | Notes |
| --- | --- | --- |
| event_id | string | → `events._id` |
| user_id | string | → `users._id` |
| status | string | `registered` |
| registered_at | datetime | |

Index: **unique (event_id, user_id)** – prevents duplicate registration.

### attendance
| Field | Type | Notes |
| --- | --- | --- |
| registration_id | string | → `registrations._id`, **unique index** |
| present | bool | |
| marked_at | datetime | |

*Note: Certificates are dynamically derived and issued when an attendance record has `present: true`. Certificates join `attendance` → `registrations` → `events` & `users`.*

### announcements
| Field | Type | Notes |
| --- | --- | --- |
| title | string | |
| message | string | HTML-escaped |
| event_id | string \| null | → `events._id` |
| author | string | admin name |
| created_at | datetime | |

### login_attempts
| Field | Type | Notes |
| --- | --- | --- |
| identifier | string | `<client_ip>:<email>` (login) or `reg_limit:<ip>` (register), **unique index** |
| failed | int | consecutive attempts |
| locked_until | datetime \| null | lockout expiry |
| updated_at | datetime | |

## Relationships (logical)

```
users 1 ──< registrations >── 1 events >── 1 categories (by name)
registrations 1 ── 1 attendance (present: true -> certificate)
events 1 ──< announcements
```

## Business Rules Enforced

- One registration per user per event (unique index).
- Registration count must be below `events.capacity`.
- Registration is rejected for events whose date is in the past.
- Certificates are issued only when attendance is marked `present`.
- Account locks after repeated failed logins for a cooling period.
