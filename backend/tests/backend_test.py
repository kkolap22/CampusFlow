"""Iteration 3 backend regression for College Event Management System.

Covers: auth (login/me/logout), dashboard, event CRUD + filters,
categories CRUD, registrations (duplicate/capacity/past),
approve + attendance rule, certificates HTML + cross-user 403,
announcements admin/student, users role/self-delete, profile,
reports, brute-force lockout.
"""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
ADMIN = ("admin@campus.edu", "Admin@123")
STUDENT = ("student@campus.edu", "student123")


def _client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, email, password):
    r = session.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email} -> {r.status_code}: {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def admin():
    s = _client()
    _login(s, *ADMIN)
    return s


@pytest.fixture(scope="module")
def student():
    s = _client()
    _login(s, *STUDENT)
    return s


class TestAuth:
    def test_admin_login_and_me(self, admin):
        r = admin.get(f"{BASE}/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN[0]
        assert data["role"] == "admin"
        assert "password_hash" not in data
        assert "access_token" in admin.cookies.get_dict()

    def test_student_login_and_me(self, student):
        r = student.get(f"{BASE}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "student"

    def test_wrong_password(self):
        s = _client()
        r = s.post(f"{BASE}/auth/login", json={"email": ADMIN[0], "password": "wrong-xyz"})
        assert r.status_code == 401

    def test_me_without_auth(self):
        r = requests.get(f"{BASE}/auth/me")
        assert r.status_code == 401

    def test_logout_clears_cookie(self):
        s = _client()
        _login(s, *STUDENT)
        r = s.post(f"{BASE}/auth/logout")
        assert r.status_code == 200
        s.cookies.clear()
        assert s.get(f"{BASE}/auth/me").status_code == 401


class TestDashboard:
    def test_admin_dashboard(self, admin):
        r = admin.get(f"{BASE}/dashboard")
        assert r.status_code == 200
        d = r.json()
        for k in ["total_events", "total_participants", "total_registrations",
                  "upcoming_events", "role"]:
            assert k in d
        assert d["role"] == "admin"

    def test_student_dashboard_has_my_registrations(self, student):
        d = student.get(f"{BASE}/dashboard").json()
        assert "my_registrations" in d


class TestCategories:
    unique = f"TEST_cat_{uuid.uuid4().hex[:6]}"
    created_id = None

    def test_list(self, admin):
        r = admin.get(f"{BASE}/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create(self, admin):
        r = admin.post(f"{BASE}/categories",
                       json={"name": self.unique, "description": "test"})
        assert r.status_code == 200, r.text
        TestCategories.created_id = r.json()["id"]

    def test_duplicate_name_rejected(self, admin):
        r = admin.post(f"{BASE}/categories",
                       json={"name": self.unique, "description": "dup"})
        assert r.status_code == 409

    def test_student_cannot_create(self, student):
        r = student.post(f"{BASE}/categories",
                         json={"name": "TEST_x_" + uuid.uuid4().hex[:4]})
        assert r.status_code == 403

    def test_delete(self, admin):
        assert TestCategories.created_id
        r = admin.delete(f"{BASE}/categories/{TestCategories.created_id}")
        assert r.status_code == 200


class TestEvents:
    event_id = None

    def _payload(self, **over):
        p = {
            "title": f"TEST_evt_{uuid.uuid4().hex[:6]}",
            "description": "Testing event created by pytest suite.",
            "category": "Technology",
            "date": "2027-06-15",
            "time": "10:00",
            "venue": "Hall A",
            "capacity": 2,
            "status": "upcoming",
        }
        p.update(over)
        return p

    def test_list_events(self, admin):
        r = admin.get(f"{BASE}/events")
        assert r.status_code == 200

    def test_create_event(self, admin):
        p = self._payload()
        r = admin.post(f"{BASE}/events", json=p)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == p["title"]
        assert "_id" not in data
        TestEvents.event_id = data["id"]
        g = admin.get(f"{BASE}/events/{TestEvents.event_id}")
        assert g.status_code == 200
        assert g.json()["title"] == p["title"]

    def test_student_cannot_create_event(self, student):
        r = student.post(f"{BASE}/events", json=self._payload())
        assert r.status_code == 403

    def test_update_event(self, admin):
        r = admin.put(f"{BASE}/events/{TestEvents.event_id}",
                      json=self._payload(title="TEST_evt_updated", capacity=2))
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_evt_updated"

    def test_search_filter(self, admin):
        r = admin.get(f"{BASE}/events?search=TEST_evt_updated")
        assert r.status_code == 200
        titles = [e["title"] for e in r.json()]
        assert "TEST_evt_updated" in titles

    def test_category_filter(self, admin):
        r = admin.get(f"{BASE}/events?category=Technology")
        assert r.status_code == 200
        for e in r.json():
            assert e["category"] == "Technology"

    def test_status_filter(self, admin):
        r = admin.get(f"{BASE}/events?status=upcoming")
        assert r.status_code == 200
        for e in r.json():
            assert e["status"] == "upcoming"


class TestRegistrationFlow:
    past_event_id = None
    reg_id = None

    def test_register_success(self, student):
        assert TestEvents.event_id
        r = student.post(f"{BASE}/events/{TestEvents.event_id}/register")
        assert r.status_code == 200, r.text

    def test_duplicate_register_409(self, student):
        r = student.post(f"{BASE}/events/{TestEvents.event_id}/register")
        assert r.status_code == 409

    def test_past_event_rejected(self, admin, student):
        past = {
            "title": f"TEST_past_{uuid.uuid4().hex[:6]}",
            "description": "past event testing rejection",
            "category": "Technology",
            "date": "2020-01-01", "time": "10:00", "venue": "X",
            "capacity": 10, "status": "completed",
        }
        r = admin.post(f"{BASE}/events", json=past)
        assert r.status_code == 200
        TestRegistrationFlow.past_event_id = r.json()["id"]
        rr = student.post(f"{BASE}/events/{TestRegistrationFlow.past_event_id}/register")
        assert rr.status_code == 400

    def test_admin_sees_registrations(self, admin):
        r = admin.get(f"{BASE}/registrations")
        assert r.status_code == 200
        rows = r.json()
        for row in rows:
            if row["event_id"] == TestEvents.event_id:
                TestRegistrationFlow.reg_id = row["id"]
                break
        assert TestRegistrationFlow.reg_id

    def test_attendance_before_approval_fails(self, admin):
        r = admin.post(
            f"{BASE}/registrations/{TestRegistrationFlow.reg_id}/attendance?present=true")
        assert r.status_code == 400

    def test_approve(self, admin):
        r = admin.patch(
            f"{BASE}/registrations/{TestRegistrationFlow.reg_id}?status=approved")
        assert r.status_code == 200

    def test_mark_present(self, admin):
        r = admin.post(
            f"{BASE}/registrations/{TestRegistrationFlow.reg_id}/attendance?present=true")
        assert r.status_code == 200

    def test_certificates_list(self, student):
        r = student.get(f"{BASE}/certificates")
        assert r.status_code == 200
        ids = [c["registration_id"] for c in r.json()]
        assert TestRegistrationFlow.reg_id in ids

    def test_certificate_html_download(self, student):
        r = student.get(
            f"{BASE}/certificates/{TestRegistrationFlow.reg_id}/download")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "Certificate of Participation" in r.text

    def test_certificate_cross_user_forbidden(self):
        s2 = _client()
        alt_email = f"TEST_stu_{uuid.uuid4().hex[:6]}@campus.edu"
        reg = s2.post(f"{BASE}/auth/register",
                      json={"name": "Test Alt", "email": alt_email,
                            "password": "pass1234", "department": "IT"})
        assert reg.status_code == 200
        r = s2.get(
            f"{BASE}/certificates/{TestRegistrationFlow.reg_id}/download")
        assert r.status_code == 403

    def test_capacity_enforced(self):
        s2 = _client()
        e2 = f"TEST_cap2_{uuid.uuid4().hex[:5]}@campus.edu"
        s2.post(f"{BASE}/auth/register",
                json={"name": "Cap2", "email": e2, "password": "pass1234"})
        r2 = s2.post(f"{BASE}/events/{TestEvents.event_id}/register")
        assert r2.status_code == 200
        s3 = _client()
        e3 = f"TEST_cap3_{uuid.uuid4().hex[:5]}@campus.edu"
        s3.post(f"{BASE}/auth/register",
                json={"name": "Cap3", "email": e3, "password": "pass1234"})
        r3 = s3.post(f"{BASE}/events/{TestEvents.event_id}/register")
        assert r3.status_code == 400

    def test_unregister(self, student):
        r = student.delete(f"{BASE}/events/{TestEvents.event_id}/register")
        assert r.status_code == 200


class TestAnnouncements:
    ann_id = None

    def test_admin_create(self, admin):
        r = admin.post(f"{BASE}/announcements",
                       json={"title": f"TEST_ann_{uuid.uuid4().hex[:5]}",
                             "message": "iteration 3 pytest"})
        assert r.status_code == 200
        TestAnnouncements.ann_id = r.json()["id"]

    def test_student_cannot_create(self, student):
        r = student.post(f"{BASE}/announcements",
                         json={"title": "TEST_bad", "message": "no way"})
        assert r.status_code == 403

    def test_student_can_view(self, student):
        r = student.get(f"{BASE}/announcements")
        assert r.status_code == 200

    def test_admin_delete(self, admin):
        r = admin.delete(f"{BASE}/announcements/{TestAnnouncements.ann_id}")
        assert r.status_code == 200


class TestUsersProfile:
    def test_admin_list_users(self, admin):
        r = admin.get(f"{BASE}/users")
        assert r.status_code == 200
        for u in r.json():
            assert "password_hash" not in u

    def test_student_cannot_list_users(self, student):
        assert student.get(f"{BASE}/users").status_code == 403

    def test_change_role_and_self_delete_protection(self, admin):
        s = _client()
        email = f"TEST_role_{uuid.uuid4().hex[:5]}@campus.edu"
        s.post(f"{BASE}/auth/register",
               json={"name": "Role Guy", "email": email, "password": "pass1234"})
        uid = s.get(f"{BASE}/auth/me").json()["id"]
        r = admin.patch(f"{BASE}/users/{uid}/role?role=admin")
        assert r.status_code == 200

        me = admin.get(f"{BASE}/auth/me").json()
        r2 = admin.delete(f"{BASE}/users/{me['id']}")
        assert r2.status_code == 400

        admin.delete(f"{BASE}/users/{uid}")

    def test_profile_update(self, student):
        r = student.put(f"{BASE}/profile",
                        json={"name": "Aarav Kulkarni", "department": "BSc IT",
                              "phone": "9999999999"})
        assert r.status_code == 200
        assert r.json()["phone"] == "9999999999"


class TestReports:
    def test_admin_reports(self, admin):
        r = admin.get(f"{BASE}/reports/events")
        assert r.status_code == 200
        for row in r.json():
            for k in ["registrations", "approved", "pending", "attended",
                      "capacity", "title", "date"]:
                assert k in row

    def test_student_cannot_access_reports(self, student):
        assert student.get(f"{BASE}/reports/events").status_code == 403


class TestLockout:
    def test_five_bad_then_429(self):
        email = f"TEST_lock_{uuid.uuid4().hex[:6]}@campus.edu"
        s = _client()
        s.post(f"{BASE}/auth/register",
               json={"name": "Locky", "email": email, "password": "pass1234"})
        s.cookies.clear()
        codes = []
        for _ in range(6):
            r = s.post(f"{BASE}/auth/login",
                       json={"email": email, "password": "WRONG!"})
            codes.append(r.status_code)
            time.sleep(0.1)
        assert codes[:5] == [401] * 5, codes
        assert codes[5] == 429, codes


class TestEdgeCases:
    def test_api_root(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200
        assert "message" in r.json()

    def test_invalid_object_id_returns_400(self, admin):
        r = admin.get(f"{BASE}/events/invalid-id-xyz")
        assert r.status_code == 400
        assert "Invalid ID format" in r.text

    def test_invalid_event_status_rejected(self, admin):
        payload = {
            "title": "Invalid Status Test",
            "description": "Valid description length test",
            "category": "Technology",
            "date": "2027-01-01",
            "time": "10:00",
            "venue": "Lab 1",
            "capacity": 50,
            "status": "not-a-valid-status",
        }
        r = admin.post(f"{BASE}/events", json=payload)
        assert r.status_code == 422

    def test_password_over_72_chars_rejected(self):
        s = _client()
        too_long_pw = "a" * 73
        r = s.post(f"{BASE}/auth/register", json={
            "name": "Long Password",
            "email": f"TEST_pw_{uuid.uuid4().hex[:6]}@campus.edu",
            "password": too_long_pw,
            "department": "BSc IT",
        })
        assert r.status_code == 422

    def test_admin_cannot_register_for_event(self, admin):
        # Create a test event first
        evt = admin.post(f"{BASE}/events", json={
            "title": f"TEST_adm_reg_{uuid.uuid4().hex[:6]}",
            "description": "Admin cannot register test event description",
            "category": "Technology",
            "date": "2027-10-10",
            "time": "12:00",
            "venue": "Hall B",
            "capacity": 50,
            "status": "upcoming",
        }).json()
        r = admin.post(f"{BASE}/events/{evt['id']}/register")
        assert r.status_code == 403
        admin.delete(f"{BASE}/events/{evt['id']}")

    def test_phone_max_length_profile(self, student):
        r = student.put(f"{BASE}/profile", json={
            "name": "Student A",
            "department": "BSc IT",
            "phone": "1" * 25,
        })
        assert r.status_code == 422


def test_zz_cleanup(admin):
    for e in admin.get(f"{BASE}/events").json():
        if e["title"].startswith("TEST_"):
            admin.delete(f"{BASE}/events/{e['id']}")
    for u in admin.get(f"{BASE}/users").json():
        if u["email"].startswith("TEST_"):
            admin.delete(f"{BASE}/users/{u['id']}")
    for c in admin.get(f"{BASE}/categories").json():
        if c["name"].startswith("TEST_"):
            admin.delete(f"{BASE}/categories/{c['id']}")
    for a in admin.get(f"{BASE}/announcements").json():
        if a["title"].startswith("TEST_"):
            admin.delete(f"{BASE}/announcements/{a['id']}")
