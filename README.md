# VoiceBook AI

An autonomous voice agent for appointment scheduling at a multispecialty hospital. A caller speaks to the agent, which checks real doctor availability and books, reschedules, or cancels the appointment without a human receptionist.

Built as a B.Tech CSE (AIML) mini-project at GLA University, Mathura (Team VoiceBook AI, T-168).

> **Status:** Core voice booking loop is working in the browser test. Phone-number telephony (Twilio), SMS confirmations, Google Calendar sync and the React dashboard are planned for v2. See [Project status](#project-status).

---

## Features

- **Book** an appointment by voice: department, doctor, service, and a free time slot
- **Reschedule** or **cancel** an existing appointment, after finding the caller's active bookings
- **Real availability**: doctor working hours, existing bookings, and the current date are all checked
- **Double-booking protection** at two levels: service-layer overlap checks and a database unique index
- **Patient recognition** by phone number, so repeat callers don't re-enter details
- **Safety rules**: chest pain, breathing trouble, or heavy bleeding send the caller to 112 and no booking is made
- **Call logging**: each finished call's transcript, duration, and caller number are saved
- **Staff dashboard** showing counts, active appointments, and call transcripts
- **Patient call page** that starts a browser call with the Vapi Web SDK

## Architecture

```
Caller (browser /call, phone line planned)
   │
Vapi: speech-to-text (Soniox), LLM (OpenAI GPT-4.1), voice (Elliot)
   │  tool calls + end-of-call reports
Webhook: POST /api/vapi/webhook   (FastAPI)
   │
Booking rules: services/availability.py, services/booking.py
   │
Database: SQLite (SQLAlchemy 2.0, Alembic migrations)
```

The language model decides what to ask and which tool to call. All booking rules are enforced in the backend, so the AI cannot book a taken slot, a time outside working hours, or a doctor in the wrong department.

## Tech stack

| Layer | Technology |
|---|---|
| Voice platform | Vapi |
| Speech-to-text | Soniox STT RT v5 |
| Language model | OpenAI GPT-4.1 |
| Text-to-speech | Elliot voice (Vapi) |
| Backend API | FastAPI, Pydantic |
| Database | SQLite (PostgreSQL planned), SQLAlchemy 2.0 |
| Migrations | Alembic |
| Tests | pytest |
| Web pages | HTML, CSS, JavaScript, Vapi Web SDK |
| Dev tunnel | ngrok |

## Project structure

```
voicebook_ai/
├── app/
│   ├── main.py                 # FastAPI app, routers, /call and /dashboard pages
│   ├── database.py             # Engine, session, Base
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── routers/
│   │   ├── catalog.py          # Departments, doctors, services, availability
│   │   ├── appointments.py     # Patients and bookings
│   │   ├── vapi.py             # Vapi webhook and tool functions
│   │   ├── calls.py            # Call log endpoint
│   │   └── dashboard.py        # Dashboard data endpoints
│   ├── services/
│   │   ├── availability.py     # Free-slot calculation
│   │   └── booking.py          # Booking, reschedule, cancel rules
│   └── static/
│       ├── call.html           # Patient page (Vapi Web SDK)
│       └── dashboard.html      # Staff dashboard
├── migrations/                 # Alembic migration files
├── scripts/
│   ├── seed.py                 # Fake hospital data
│   └── score_calls.py          # Intent accuracy scoring
├── tests/
│   ├── conftest.py
│   ├── test_booking.py         # Booking-rule tests
│   ├── test_call_logs.py       # Call-log save test
│   └── voice/scenarios.csv     # 50 voice test scenarios
├── docs/
│   ├── openapi.json            # Exported API spec
│   └── erd.md                  # Entity relationship diagram
├── alembic.ini
├── pytest.ini
└── requirements.txt
```

## Getting started

### Prerequisites

- Python 3.11 or newer
- Git
- A Vapi account (for the voice agent)
- ngrok (so Vapi can reach your local server)

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/<your-username>/voicebook-ai.git
cd voicebook-ai
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\Activate.ps1        # Windows PowerShell
```

```bash
source venv/bin/activate         # Mac/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the database and load fake data

```bash
alembic upgrade head
python -m scripts.seed
```

The seed data contains five departments (Cardiology, Orthopedics, Dermatology, Pediatrics, General Medicine), fake doctors, services, and Monday to Saturday schedules. All names are placeholders.

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs`: interactive API documentation
- `http://127.0.0.1:8000/health`: should return `{"status": "ok"}`
- `http://127.0.0.1:8000/dashboard`: staff dashboard
- `http://127.0.0.1:8000/call`: patient call page

### 5. Run the tests

```bash
pytest -v
```

Tests use a fresh in-memory SQLite database, so your `voicebook.db` is never touched.

## Configuration

Set these as environment variables in the terminal where you start the server. Never commit real keys.

| Variable | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | Database connection string. Defaults to `sqlite:///./voicebook.db` | No |
| `VAPI_PUBLIC_KEY` | Vapi **public** key for the browser call page | For `/call` |
| `VAPI_ASSISTANT_ID` | ID of the Vapi assistant | For `/call` |
| `VAPI_WEBHOOK_SECRET` | Shared secret for the webhook check | Planned (see below) |

PowerShell example:

```powershell
$env:VAPI_PUBLIC_KEY="your-public-key"
$env:VAPI_ASSISTANT_ID="your-assistant-id"
uvicorn app.main:app --reload
```

## Connecting the voice agent (Vapi)

1. **Expose the server.** Run `ngrok http 8000` in a second terminal and copy the `https://…` forwarding address.
2. **Create an assistant** in the Vapi dashboard with the system prompt describing the booking flow (greeting, identity, details, read-back, confirmation, safety rules).
3. **Set the Server URL** in the assistant's Advanced tab to `https://<your-ngrok-address>/api/vapi/webhook`.
4. **Create the 10 tools** as Function tools. Their names must match the functions in `app/routers/vapi.py`:
   `list_departments`, `list_doctors`, `list_services`, `check_availability`, `find_patient`, `register_patient`, `book_appointment`, `my_appointments`, `reschedule_appointment`, `cancel_appointment`.
5. **Enable end-of-call reports** under Server Messages so calls are saved to the call log.
6. **Test** with the **Talk** button in the Vapi dashboard.

If you restart ngrok, its address changes, so update the Server URL in Vapi.

## API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/departments` | List departments |
| GET | `/api/doctors` | List doctors (optional `department_id`) |
| GET | `/api/services` | List services (optional `department_id`) |
| GET | `/api/calendar/availability` | Open slots for a doctor, service, and date range (max 14 days) |
| POST | `/api/patients` | Create or return a patient by phone |
| GET | `/api/patients/by-phone` | Find a patient by phone number |
| GET | `/api/patients/{patient_id}/appointments` | Active appointments for a patient |
| POST | `/api/appointments` | Book an appointment (201) |
| GET | `/api/appointments/{id}` | Get one appointment |
| PATCH | `/api/appointments/{id}` | Reschedule (`start_time`) or cancel (`status: "cancelled"`) |
| POST | `/api/vapi/webhook` | Receives Vapi tool calls and end-of-call reports |
| GET | `/api/calls` | Call log with transcripts |
| GET | `/api/dashboard/stats` | Dashboard counts |
| GET | `/api/dashboard/appointments` | Active appointments for the dashboard |
| GET | `/api/public-config` | Public key and assistant ID for the browser page |

Booking rule violations return **409** with a message the agent can read to the caller.

## Database

| Table | Stores |
|---|---|
| `departments` | Hospital departments |
| `doctors` | Doctors, each in one department |
| `services` | Consultations and procedures, with duration |
| `doctor_schedules` | Weekly working windows per doctor |
| `patients` | Name (optional) and unique phone number |
| `appointments` | Bookings with status `booked`, `rescheduled`, `cancelled`, or `completed` |
| `call_logs` | One row per call, with transcript and duration |

A partial unique index on `appointments (doctor_id, start_time)` applies only to active statuses, so a doctor cannot have two active bookings at the same start time.

See [`docs/erd.md`](docs/erd.md) for the diagram.

## Testing

- **Unit tests (pytest):** booking rules, including double booking, overlapping visits, working hours, department matching, cancel, reschedule, and alternative slots, plus the call-log save test.
- **Voice tests:** 50 scripted scenarios in `tests/voice/scenarios.csv` (20 booking, 8 reschedule, 7 cancel, 7 enquiry, 4 emergency, 4 unclear). After each call, record the intent the agent acted on, then run:

  ```bash
  python scripts/score_calls.py
  ```

## Project status

| Area | Status |
|---|---|
| Database schema, migrations, ERD, API spec | Done |
| Booking, reschedule, and cancel rules with tests | Done |
| Vapi voice agent with 10 tools through the webhook | Done (browser test) |
| Call logging with transcripts | Done |
| Staff dashboard (basic) | Done |
| Patient browser call page | In progress |
| Intent accuracy scoring (50 scenarios) | In progress |
| Webhook shared-secret check | Helper written, not yet enforced |
| Twilio phone number | Planned (v2) |
| SMS confirmations and reminders | Planned (v2) |
| Google Calendar sync | Planned (v2) |
| React dashboard with login | Planned (v2) |
| Human handoff to staff | Planned (v2) |
| PostgreSQL and cloud deployment | Planned (v2) |
| Hindi support | Planned (v2) |

## Security and limitations

- The project uses **fake data only**. Do not enter real patient information.
- The webhook is **not yet authenticated**. Anyone who learns the ngrok address can call it. Enable the shared-secret check before any public or shared use.
- The dashboard has **no login**. Keep it on `127.0.0.1` and don't share the `/dashboard` address.
- SQLite is for development. Use PostgreSQL before deployment.
- Speech recognition accuracy depends on the caller's voice and background noise.
- This is an academic prototype. It does not give medical advice, and it is not a replacement for emergency services.

## Team

- **Diksha Sharma**: Team Leader, backend and dialogue engine
- **Charvi Mittal**: Product lead, frontend and dashboard
- **Akshata Chaudhary**: QA and documentation

**Mentor:** Sir Rohit Kumar Gupta, GLA University

## License

Academic project. Add a license here before publishing if you plan to reuse the code.
