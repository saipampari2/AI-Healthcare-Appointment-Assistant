import hashlib
import hmac
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

APP_SECRET = os.getenv("APP_SECRET_KEY", "demo-hospital-secret-change-me")
USERS = {
    "demo@hospital.test": {"password": "Demo@123", "role": "patient"},
}
DEFAULT_SLOTS = ["09:00", "10:00", "11:30", "14:00", "15:30"]
DOCTORS = {
    "cardiology": ["Dr. Rao", "Dr. Shah"],
    "dermatology": ["Dr. Lee"],
    "general": ["Dr. Nair", "Dr. Patel"],
    "neurology": ["Dr. Khan"],
}
BOOKED = {}


def sign_token(username: str) -> str:
    payload = f"{username}:{int(time.time() // 300)}"
    digest = hmac.new(APP_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{username}.{digest}"


def validate_token(token: str):
    if not token:
        return None
    try:
        username, digest = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(APP_SECRET.encode("utf-8"), f"{username}:{int(time.time() // 300)}".encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(digest, expected):
        return username
    return None


def get_available_slots(department: str, preferred_date: str):
    department = (department or "general").lower()
    today_slots = list(DEFAULT_SLOTS)
    booked_slots = BOOKED.get(preferred_date, {}).get(department, [])
    return [slot for slot in today_slots if slot not in booked_slots]


class HospitalRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_request_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _require_auth(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self._send_json(401, {"error": "Authentication required."})
            return None
        token = auth_header.split(" ", 1)[1].strip()
        username = validate_token(token)
        if username is None:
            self._send_json(401, {"error": "Invalid or expired token."})
            return None
        return username

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path == "/api/availability":
            params = parse_qs(parsed.query)
            department = (params.get("department", ["general"])[0] or "general").lower()
            preferred_date = params.get("date", [""])[0]
            slots = get_available_slots(department, preferred_date)
            self._send_json(200, {"department": department, "date": preferred_date, "available_slots": slots})
            return

        self._send_json(404, {"error": "Not found."})

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._get_request_body()

        if parsed.path == "/api/login":
            username = (body.get("username") or "").strip()
            password = (body.get("password") or "").strip()
            user = USERS.get(username)
            if not user or user.get("password") != password:
                self._send_json(401, {"error": "Invalid username or password."})
                return
            token = sign_token(username)
            self._send_json(200, {"token": token, "user": username, "role": user.get("role")})
            return

        if parsed.path == "/api/appointments":
            username = self._require_auth()
            if username is None:
                return

            name = (body.get("name") or "").strip()
            department = (body.get("department") or "general").strip()
            preferred_date = (body.get("preferred_date") or "").strip()
            preferred_time = (body.get("preferred_time") or "").strip()
            contact = (body.get("contact") or "").strip()

            if not all([name, department, preferred_date, preferred_time, contact]):
                self._send_json(400, {"error": "Missing required booking information."})
                return

            if preferred_date < time.strftime("%Y-%m-%d"):
                self._send_json(400, {"error": "The requested date is in the past. Please choose a future date."})
                return

            available_slots = get_available_slots(department, preferred_date)
            if preferred_time not in available_slots:
                self._send_json(409, {"error": "Selected doctor slot is unavailable or already booked."})
                return

            doctor = DOCTORS.get(department.lower(), ["Dr. Smith"])[0]
            booking_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
            BOOKED.setdefault(preferred_date, {})
            BOOKED[preferred_date].setdefault(department.lower(), [])
            BOOKED[preferred_date][department.lower()].append(preferred_time)

            self._send_json(
                201,
                {
                    "status": "confirmed",
                    "booking_id": booking_id,
                    "patient": name,
                    "department": department,
                    "preferred_date": preferred_date,
                    "preferred_time": preferred_time,
                    "doctor": doctor,
                    "contact": contact,
                    "message": "Appointment request confirmed by the hospital booking API.",
                },
            )
            return

        self._send_json(404, {"error": "Not found."})


def main():
    port = int(os.getenv("HOSPITAL_API_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HospitalRequestHandler)
    print(f"Hospital booking API listening on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
