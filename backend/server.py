"""College Event Management System - FastAPI backend.

Modules:
- Auth: register/login/logout/me with bcrypt + JWT (cookie based).
- Events + Categories: CRUD, search, filters, capacity + duplicate prevention.
- Registrations + Attendance + Certificates: business rules enforced in code.
- Announcements: admin creates campus-wide notices.
- Users + Profiles: admin manages roles; students edit their own profile.
- Reports: event-wise counts for admin dashboards.

Data model (MongoDB collections with normalized structure and unique indexes,
mirroring the relational schema shown in the project report):
  users(_id, name, email UNIQUE, password_hash, role, department, phone, created_at)
  categories(_id, name, description, created_at)
  events(_id, title, description, category, date, time, venue, capacity, image, status,
         created_at, created_by -> users._id)
  registrations(_id, event_id -> events._id, user_id -> users._id, status,
                registered_at)  UNIQUE(event_id, user_id)
  attendance(_id, registration_id -> registrations._id UNIQUE, present, marked_at)
  announcements(_id, title, message, event_id?, author, created_at)
  login_attempts(_id, identifier UNIQUE, failed, locked_until, updated_at)
"""
import html
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import bcrypt
import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI(title="College Event Management System")
api = APIRouter(prefix="/api")
JWT_ALGORITHM = "HS256"


# ---------- Pydantic input schemas ----------
class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    department: str = "BSc IT"


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class EventInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    category: str
    date: str
    time: str
    venue: str
    capacity: int = Field(gt=0, le=10000)
    image: str = "https://images.unsplash.com/photo-1515187029135-18ee286d815b?auto=format&fit=crop&w=1200&q=80"
    status: str = "upcoming"


class CategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: str = ""


class AnnouncementInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=5, max_length=1000)
    event_id: Optional[str] = None


class ProfileInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    department: str = Field(min_length=2, max_length=80)
    phone: str = ""


# ---------- Helpers ----------
def now():
    return datetime.now(timezone.utc).isoformat()


def clean(doc):
    """Convert Mongo document to JSON safe dict (id string, no password)."""
    if not doc:
        return None
    result = dict(doc)
    result["id"] = str(result.pop("_id", result.get("id", "")))
    result.pop("password_hash", None)
    return result


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def token_for(user):
    payload = {
        "sub": str(user["_id"]),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Please log in to continue")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Your session has expired")


async def admin_only(user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def set_session(response, user):
    response.set_cookie(
        "access_token", token_for(user), httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
        samesite=os.environ.get("COOKIE_SAMESITE", "lax"),
        max_age=28800, path="/",
    )


# ---------- Auth ----------
@api.get("/")
async def root():
    return {"message": "College Event Management System API"}


@api.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    email = data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists")
    doc = {
        "name": data.name, "email": email,
        "password_hash": hash_password(data.password),
        "department": data.department, "phone": "",
        "role": "student", "created_at": now(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    set_session(response, doc)
    return clean(doc)


@api.post("/auth/login")
async def login(data: LoginInput, response: Response, request: Request):
    """Login with bcrypt check and a soft-lock after 5 failed attempts / 15 minutes."""
    user = await db.users.find_one({"email": data.email.lower()})
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{data.email.lower()}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("locked_until", "") > now():
        raise HTTPException(429, "Too many attempts. Please try again in 15 minutes")
    if not user or not verify_password(data.password, user["password_hash"]):
        failed = (attempt.get("failed", 0) if attempt else 0) + 1
        update = {"identifier": identifier, "failed": failed, "updated_at": now()}
        if failed >= 5:
            update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    set_session(response, user)
    return clean(user)


@api.post("/auth/logout")
async def logout(response: Response, user=Depends(current_user)):
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out successfully"}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return clean(user)


# ---------- Dashboard ----------
@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    return {
        "total_events": await db.events.count_documents({}),
        "total_participants": await db.users.count_documents({"role": "student"}),
        "total_registrations": await db.registrations.count_documents({}),
        "upcoming_events": await db.events.count_documents({"status": "upcoming"}),
        "my_registrations": await db.registrations.count_documents({"user_id": str(user["_id"])}),
        "role": user["role"],
    }


# ---------- Events + Categories ----------
@api.get("/events")
async def events(search: str = "", category: str = "", status: str = "",
                 user=Depends(current_user)):
    query = {}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    docs = await db.events.find(query).sort("date", 1).to_list(200)
    output = []
    for event in docs:
        item = clean(event)
        item["registered"] = bool(await db.registrations.find_one(
            {"event_id": item["id"], "user_id": str(user["_id"])}))
        item["registration_count"] = await db.registrations.count_documents(
            {"event_id": item["id"]})
        output.append(item)
    return output


@api.get("/events/{event_id}")
async def event_detail(event_id: str, user=Depends(current_user)):
    event = await db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(404, "Event not found")
    item = clean(event)
    item["registered"] = bool(await db.registrations.find_one(
        {"event_id": event_id, "user_id": str(user["_id"])}))
    item["registration_count"] = await db.registrations.count_documents({"event_id": event_id})
    return item


@api.post("/events")
async def create_event(data: EventInput, user=Depends(admin_only)):
    doc = data.model_dump()
    doc.update({"created_at": now(), "created_by": str(user["_id"])})
    result = await db.events.insert_one(doc)
    doc["_id"] = result.inserted_id
    return clean(doc)


@api.put("/events/{event_id}")
async def update_event(event_id: str, data: EventInput, user=Depends(admin_only)):
    existing = await db.events.find_one({"_id": ObjectId(event_id)})
    if not existing:
        raise HTTPException(404, "Event not found")
    if data.status == "upcoming" and data.date < datetime.now().date().isoformat():
        raise HTTPException(400, "Upcoming events cannot be scheduled in the past")
    current_regs = await db.registrations.count_documents({"event_id": event_id})
    if data.capacity < current_regs:
        raise HTTPException(400, f"Capacity cannot be less than existing registrations ({current_regs})")
    await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": data.model_dump()})
    return clean(await db.events.find_one({"_id": ObjectId(event_id)}))


@api.delete("/events/{event_id}")
async def delete_event(event_id: str, user=Depends(admin_only)):
    await db.events.delete_one({"_id": ObjectId(event_id)})
    await db.registrations.delete_many({"event_id": event_id})
    return {"message": "Event deleted"}


@api.get("/categories")
async def categories(user=Depends(current_user)):
    return [clean(x) for x in await db.categories.find().sort("name", 1).to_list(100)]


@api.post("/categories")
async def create_category(data: CategoryInput, user=Depends(admin_only)):
    if await db.categories.find_one({"name": data.name}):
        raise HTTPException(409, "Category with this name already exists")
    doc = data.model_dump()
    doc["created_at"] = now()
    result = await db.categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return clean(doc)


@api.delete("/categories/{category_id}")
async def delete_category(category_id: str, user=Depends(admin_only)):
    await db.categories.delete_one({"_id": ObjectId(category_id)})
    return {"message": "Category deleted"}


# ---------- Registrations + Attendance ----------
@api.post("/events/{event_id}/register")
async def register_event(event_id: str, user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Only students can register")
    event = await db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(404, "Event not found")
    if event["date"] < datetime.now().date().isoformat():
        raise HTTPException(400, "Registration is closed for past events")
    if await db.registrations.find_one({"event_id": event_id, "user_id": str(user["_id"])}):
        raise HTTPException(409, "You are already registered")
    if await db.registrations.count_documents({"event_id": event_id}) >= event["capacity"]:
        raise HTTPException(400, "This event has reached capacity")
    doc = {"event_id": event_id, "user_id": str(user["_id"]),
           "status": "pending", "registered_at": now()}
    await db.registrations.insert_one(doc)
    return {"message": "Registration submitted"}


@api.delete("/events/{event_id}/register")
async def unregister_event(event_id: str, user=Depends(current_user)):
    result = await db.registrations.delete_one(
        {"event_id": event_id, "user_id": str(user["_id"])})
    if not result.deleted_count:
        raise HTTPException(404, "You are not registered for this event")
    return {"message": "Registration cancelled"}


async def _decorate_registration(row):
    event = await db.events.find_one({"_id": ObjectId(row["event_id"])})
    student = await db.users.find_one({"_id": ObjectId(row["user_id"])})
    attendance = await db.attendance.find_one({"registration_id": str(row["_id"])})
    item = clean(row)
    item.update({
        "event_title": event.get("title", "Deleted event") if event else "Deleted event",
        "event_date": event.get("date", "") if event else "",
        "student_name": student.get("name", "Unknown") if student else "Unknown",
        "student_email": student.get("email", "") if student else "",
        "attendance": attendance.get("present") if attendance else None,
    })
    return item


@api.get("/registrations")
async def registrations(event_id: str = "", user=Depends(current_user)):
    query = {} if user["role"] == "admin" else {"user_id": str(user["_id"])}
    if event_id:
        query["event_id"] = event_id
    rows = await db.registrations.find(query).sort("registered_at", -1).to_list(500)
    return [await _decorate_registration(row) for row in rows]


@api.patch("/registrations/{registration_id}")
async def registration_status(registration_id: str, status: str, user=Depends(admin_only)):
    if status not in ["approved", "rejected", "pending"]:
        raise HTTPException(400, "Invalid status")
    result = await db.registrations.update_one(
        {"_id": ObjectId(registration_id)}, {"$set": {"status": status}})
    if not result.matched_count:
        raise HTTPException(404, "Registration not found")
    return {"message": "Registration updated"}


@api.post("/registrations/{registration_id}/attendance")
async def attendance(registration_id: str, present: bool, user=Depends(admin_only)):
    registration = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not registration:
        raise HTTPException(404, "Registration not found")
    if registration.get("status") != "approved":
        raise HTTPException(400, "Only approved registrations can be marked present")
    await db.attendance.update_one(
        {"registration_id": registration_id},
        {"$set": {"registration_id": registration_id, "present": present, "marked_at": now()}},
        upsert=True,
    )
    return {"message": "Attendance saved"}


# ---------- Certificates ----------
@api.get("/certificates")
async def certificates(user=Depends(current_user)):
    """Return certificates the caller is allowed to see (admin: all, student: own)."""
    rows = await db.attendance.find({"present": True}).to_list(1000)
    output = []
    for row in rows:
        reg_query = {"_id": ObjectId(row["registration_id"])}
        if user["role"] != "admin":
            reg_query["user_id"] = str(user["_id"])
        registration = await db.registrations.find_one(reg_query)
        if not registration:
            continue
        event = await db.events.find_one({"_id": ObjectId(registration["event_id"])})
        student = await db.users.find_one({"_id": ObjectId(registration["user_id"])})
        output.append({
            "id": str(row["_id"]),
            "registration_id": row["registration_id"],
            "event_title": event["title"] if event else "Event",
            "event_date": event.get("date", "") if event else "",
            "student_name": student.get("name", "Participant") if student else "Participant",
            "issued_at": row.get("marked_at"),
        })
    return output


@api.get("/certificates/{registration_id}/download", response_class=HTMLResponse)
async def download_certificate(registration_id: str, user=Depends(current_user)):
    """Return a printable HTML certificate for an eligible participant."""
    registration = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not registration:
        raise HTTPException(404, "Registration not found")
    if user["role"] != "admin" and registration["user_id"] != str(user["_id"]):
        raise HTTPException(403, "You can only download your own certificate")
    attendance = await db.attendance.find_one(
        {"registration_id": registration_id, "present": True})
    if not attendance:
        raise HTTPException(400, "Certificate is available only after attendance is marked")
    event = await db.events.find_one({"_id": ObjectId(registration["event_id"])})
    student = await db.users.find_one({"_id": ObjectId(registration["user_id"])})
    # Escape user-provided strings to prevent HTML injection in certificate output.
    safe_name = html.escape(student["name"])
    safe_dept = html.escape(student.get("department", ""))
    safe_title = html.escape(event["title"])
    safe_venue = html.escape(event["venue"])
    safe_date = html.escape(event["date"])
    cert_html = f"""<!doctype html><html><head><meta charset='utf-8'>
<title>Certificate - {safe_title}</title>
<style>
  body{{font-family:Georgia,serif;background:#f6f5ef;margin:0;padding:40px;}}
  .cert{{max-width:900px;margin:auto;background:#fff;padding:70px 60px;
    border:12px double #b8860b;text-align:center;box-shadow:0 20px 40px #0002;}}
  h1{{font-size:44px;color:#1a365d;margin:0 0 8px;letter-spacing:2px;}}
  .sub{{color:#8a6d1a;letter-spacing:6px;font-size:12px;}}
  .name{{font-size:40px;color:#1a365d;margin:30px 0 10px;border-bottom:1px solid #ccc;
    display:inline-block;padding:0 40px 8px;}}
  p{{color:#334155;font-size:16px;line-height:1.7;}}
  .event{{font-weight:700;color:#0f172a;}}
  .foot{{display:flex;justify-content:space-between;margin-top:60px;color:#64748b;font-size:12px;}}
  .sig{{border-top:1px solid #999;padding-top:6px;width:200px;}}
  @media print{{body{{background:#fff;padding:0;}}}}
</style></head><body>
<div class='cert'>
  <div class='sub'>CAMPUS EVENTS · CERTIFICATE OF PARTICIPATION</div>
  <h1>Certificate of Participation</h1>
  <p>This is to certify that</p>
  <div class='name'>{safe_name}</div>
  <p>from <b>{safe_dept}</b> has successfully participated in</p>
  <p class='event'>{safe_title}</p>
  <p>held on <b>{safe_date}</b> at <b>{safe_venue}</b>.</p>
  <p>We appreciate your active involvement and commitment.</p>
  <div class='foot'>
    <div class='sig'>Event Coordinator</div>
    <div class='sig'>Principal</div>
  </div>
  <p style='margin-top:40px;font-size:11px;color:#94a3b8;'>Certificate ID: {registration_id}</p>
</div>
<script>window.onload=function(){{setTimeout(window.print,400)}}</script>
</body></html>"""
    return HTMLResponse(content=cert_html)


# ---------- Announcements ----------
@api.get("/announcements")
async def announcements(user=Depends(current_user)):
    return [clean(x) for x in
            await db.announcements.find().sort("created_at", -1).to_list(100)]


@api.post("/announcements")
async def create_announcement(data: AnnouncementInput, user=Depends(admin_only)):
    doc = data.model_dump()
    doc.update({"created_at": now(), "author": user["name"]})
    result = await db.announcements.insert_one(doc)
    doc["_id"] = result.inserted_id
    return clean(doc)


@api.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, user=Depends(admin_only)):
    await db.announcements.delete_one({"_id": ObjectId(announcement_id)})
    return {"message": "Announcement deleted"}


# ---------- Users + Profile ----------
@api.get("/users")
async def users(user=Depends(admin_only)):
    docs = await db.users.find({}, {"password_hash": 0}).sort("name", 1).to_list(500)
    return [clean(x) for x in docs]


@api.patch("/users/{user_id}/role")
async def change_role(user_id: str, role: str, user=Depends(admin_only)):
    if role not in ["admin", "student"]:
        raise HTTPException(400, "Invalid role")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": role}})
    return {"message": "Role updated"}


@api.delete("/users/{user_id}")
async def delete_user(user_id: str, user=Depends(admin_only)):
    if str(user["_id"]) == user_id:
        raise HTTPException(400, "You cannot delete your own account")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    await db.registrations.delete_many({"user_id": user_id})
    return {"message": "User deleted"}


@api.get("/profile")
async def profile(user=Depends(current_user)):
    return clean(user)


@api.put("/profile")
async def update_profile(data: ProfileInput, user=Depends(current_user)):
    await db.users.update_one({"_id": user["_id"]}, {"$set": data.model_dump()})
    return clean(await db.users.find_one({"_id": user["_id"]}))


# ---------- Reports ----------
@api.get("/reports/events")
async def report_events(user=Depends(admin_only)):
    """Event-wise counts: registrations, approved, attended, capacity."""
    events_list = await db.events.find().sort("date", -1).to_list(500)
    report = []
    for event in events_list:
        eid = str(event["_id"])
        total = await db.registrations.count_documents({"event_id": eid})
        approved = await db.registrations.count_documents({"event_id": eid, "status": "approved"})
        pending = await db.registrations.count_documents({"event_id": eid, "status": "pending"})
        registrations_of = await db.registrations.find({"event_id": eid}).to_list(1000)
        reg_ids = [str(r["_id"]) for r in registrations_of]
        attended = await db.attendance.count_documents(
            {"registration_id": {"$in": reg_ids}, "present": True}) if reg_ids else 0
        report.append({
            "id": eid, "title": event["title"], "category": event.get("category", ""),
            "date": event.get("date", ""), "capacity": event.get("capacity", 0),
            "status": event.get("status", ""),
            "registrations": total, "approved": approved,
            "pending": pending, "attended": attended,
        })
    return report


# ---------- Startup: indexes + demo seed ----------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.categories.create_index("name", unique=True)
    await db.registrations.create_index([("event_id", 1), ("user_id", 1)], unique=True)
    await db.attendance.create_index("registration_id", unique=True)
    await db.login_attempts.create_index("identifier", unique=True)

    admin_email = os.environ["ADMIN_EMAIL"]
    admin_password = os.environ["ADMIN_PASSWORD"]
    if not await db.users.find_one({"email": admin_email}):
        await db.users.insert_one({
            "name": "System Admin", "email": admin_email,
            "password_hash": hash_password(admin_password),
            "department": "Administration", "role": "admin",
            "phone": "", "created_at": now(),
        })
    if not await db.users.find_one({"email": "student@campus.edu"}):
        await db.users.insert_one({
            "name": "Aarav Kulkarni", "email": "student@campus.edu",
            "password_hash": hash_password("student123"),
            "department": "BSc IT", "role": "student",
            "phone": "", "created_at": now(),
        })
    if await db.categories.count_documents({}) == 0:
        await db.categories.insert_many([
            {"name": "Technology", "description": "Coding, innovation and digital skills", "created_at": now()},
            {"name": "Cultural", "description": "Arts, music and campus culture", "created_at": now()},
            {"name": "Sports", "description": "Fitness and competitive events", "created_at": now()},
            {"name": "Workshop", "description": "Hands-on learning sessions", "created_at": now()},
        ])
    if await db.events.count_documents({}) == 0:
        await db.events.insert_many([
            {"title": "Campus Hackathon 2026", "description": "Build practical solutions with a team in this intensive innovation sprint.",
             "category": "Technology", "date": "2026-04-18", "time": "09:00", "venue": "Innovation Lab",
             "capacity": 80, "image": "https://images.unsplash.com/photo-1515187029135-18ee286d815b?auto=format&fit=crop&w=1200&q=80",
             "status": "upcoming", "created_at": now()},
            {"title": "Annual Cultural Fest", "description": "Celebrate music, movement and creativity across our campus community.",
             "category": "Cultural", "date": "2026-03-28", "time": "16:00", "venue": "Open Air Theatre",
             "capacity": 300, "image": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1200&q=80",
             "status": "upcoming", "created_at": now()},
            {"title": "Cloud & DevOps Workshop", "description": "Introduction to containers, CI/CD and cloud native applications for students.",
             "category": "Workshop", "date": "2026-03-05", "time": "10:30", "venue": "Seminar Hall B",
             "capacity": 60, "image": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
             "status": "upcoming", "created_at": now()},
        ])


app.include_router(api)
cors_origins = [origin.strip() for origin in os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"], allow_headers=["*"],
)
