# CampusFlow | Full Stack

CampusFlow is a full-stack college event management platform for organizing campus events, student registrations, attendance, certificates, announcements, and administration from one workspace.

Built as a TY BSc IT / CA academic project with a React frontend, FastAPI backend, JWT authentication, and MongoDB persistence.

- **Frontend:** React 19, React Router 7, Tailwind CSS, Shadcn UI, Axios
- **Backend:** FastAPI (Python 3.11), JWT authentication (HTTP-only cookies), bcrypt password hashing
- **Database:** MongoDB (accessed via Motor / PyMongo)

## Features

| Area | Admin | Student |
| --- | --- | --- |
| Authentication (register, login, logout, lockout after failed attempts) | ✔ | ✔ |
| Dashboard with statistics | ✔ | ✔ |
| Event CRUD (create / edit / delete / status) | ✔ | view only |
| Category CRUD | ✔ | view only |
| Event registration (no duplicates, capacity enforced, no past events) | – | ✔ |
| Attendance marking | ✔ | – |
| Certificate generation & download (for attended events) | ✔ | own only |
| Announcements | create / delete | read |
| Reports (event-wise registrations, attendance, certificates) | ✔ | – |
| User management (list / delete) | ✔ | – |
| Profile edit | ✔ | ✔ |

## Project Structure

```
.
├── backend/
│   ├── server.py            # FastAPI app: models, auth, routes, startup seed
│   ├── requirements.txt     # Python dependencies
│   ├── pytest.ini
│   ├── .env.example         # Backend environment template (copy to .env)
│   └── tests/backend_test.py
├── frontend/
│   ├── src/
│   │   ├── App.js           # All pages, routing and API calls
│   │   ├── components/ui/   # Shadcn UI components
│   │   └── index.js / index.css / App.css
│   ├── public/
│   ├── package.json         # Node dependencies
│   ├── tailwind.config.js, craco.config.js, postcss.config.js
│   └── .env.example         # Frontend environment template (copy to .env)
├── docs/
│   └── DATABASE_SCHEMA.md   # Collections, fields, indexes, relationships
├── memory/PRD.md            # Product requirements document
├── test_reports/            # Automated test reports
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 20+ and Yarn
- MongoDB 6+ (local or Atlas)

## Setup & Run

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit values (see below)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend environment variables (`backend/.env`):

| Variable | Description | Example |
| --- | --- | --- |
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `college_events` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `JWT_SECRET` | Long random string used to sign JWTs | *(generate your own)* |
| `ADMIN_EMAIL` | Seeded admin account email | `admin@campus.edu` |
| `ADMIN_PASSWORD` | Seeded admin account password | *(choose your own)* |

On first start the backend creates indexes and seeds: the admin account, one demo student (`student@campus.edu` / `student123`), four categories and three sample events.

API docs are available at `http://localhost:8001/docs`.

### 2. Frontend

```bash
cd frontend
yarn install
cp .env.example .env               # set REACT_APP_BACKEND_URL
yarn start                         # http://localhost:3000
```

Frontend environment variables (`frontend/.env`):

| Variable | Description | Example |
| --- | --- | --- |
| `REACT_APP_BACKEND_URL` | Base URL of the backend (no trailing slash) | `http://localhost:8001` |

All API calls are made to `${REACT_APP_BACKEND_URL}/api/...`.

### 3. Login

- Admin: the email/password you set in `ADMIN_EMAIL` / `ADMIN_PASSWORD`
- Student: `student@campus.edu` / `student123` (demo seed), or register a new account from the UI

## API Overview

| Method | Endpoint | Access |
| --- | --- | --- |
| POST | `/api/auth/register` | public |
| POST | `/api/auth/login` · `/api/auth/logout` | public / authenticated |
| GET | `/api/auth/me` · `/api/dashboard` | authenticated |
| GET / POST / PUT / DELETE | `/api/events`, `/api/events/{id}` | read: all · write: admin |
| GET / POST / DELETE | `/api/categories`, `/api/categories/{id}` | read: all · write: admin |
| POST / DELETE | `/api/events/{id}/register` | student |
| GET | `/api/registrations` | admin: all · student: own |
| POST | `/api/registrations/{id}/attendance` | admin |
| GET | `/api/certificates`, `/api/certificates/{registration_id}/download` | authenticated |
| GET / POST / DELETE | `/api/announcements`, `/api/announcements/{id}` | read: all · write: admin |
| GET / DELETE | `/api/users`, `/api/users/{id}` | admin |
| GET / PUT | `/api/profile` | authenticated |
| GET | `/api/reports/events` | admin |

## Testing

```bash
cd backend && pytest                 # backend API tests
cd frontend && yarn build            # production build check
```

## Security Notes

- Passwords are hashed with bcrypt; JWTs are stored in HTTP-only cookies.
- Accounts are temporarily locked after repeated failed logins (`login_attempts` collection).
- User-supplied announcement text is HTML-escaped before rendering in certificates/announcements.
- Never commit `.env` files. Use the provided `.env.example` templates.
