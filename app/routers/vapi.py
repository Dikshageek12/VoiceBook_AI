import json
from datetime import date, datetime
import os
import secrets
from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models
from app.database import SessionLocal
from app.models import ACTIVE_STATUSES
from app.services.availability import get_available_slots
from app.services.booking import (
    BookingError, cancel_appointment, create_appointment, reschedule_appointment,
)

router = APIRouter(tags=["vapi"])


def _appt_dict(a: models.Appointment) -> dict:
    return {
        "appointment_id": a.id,
        "patient_id": a.patient_id,
        "doctor_id": a.doctor_id,
        "service_id": a.service_id,
        "start_time": a.start_time.isoformat(timespec="minutes"),
        "end_time": a.end_time.isoformat(timespec="minutes"),
        "status": a.status,
    }


# ---- Tool functions: each takes the database session and the arguments from Vapi ----

def list_departments(db: Session, args: dict) -> str:
    rows = db.scalars(select(models.Department).order_by(models.Department.name)).all()
    return json.dumps([{"id": d.id, "name": d.name} for d in rows])


def list_doctors(db: Session, args: dict) -> str:
    query = select(models.Doctor)
    if args.get("department_id"):
        query = query.where(models.Doctor.department_id == int(args["department_id"]))
    rows = db.scalars(query).all()
    return json.dumps([{"id": d.id, "name": d.name, "department_id": d.department_id} for d in rows])


def list_services(db: Session, args: dict) -> str:
    query = select(models.Service)
    if args.get("department_id"):
        query = query.where(models.Service.department_id == int(args["department_id"]))
    rows = db.scalars(query).all()
    return json.dumps([{"id": s.id, "name": s.name, "duration_minutes": s.duration_minutes,
                        "department_id": s.department_id} for s in rows])


def check_availability(db: Session, args: dict) -> str:
    day = date.fromisoformat(args["date"])
    slots = get_available_slots(db, int(args["doctor_id"]), int(args["service_id"]), day, day)
    if not slots:
        return json.dumps({"available": False, "message": "No open slots on that day."})
    return json.dumps({"available": True,
                       "slots": [s.isoformat(timespec="minutes") for s in slots[:6]]})


def find_patient(db: Session, args: dict) -> str:
    patient = db.scalar(select(models.Patient).where(models.Patient.phone == args["phone"]))
    if patient is None:
        return json.dumps({"found": False})
    return json.dumps({"found": True, "patient_id": patient.id, "full_name": patient.full_name})


def register_patient(db: Session, args: dict) -> str:
    patient = db.scalar(select(models.Patient).where(models.Patient.phone == args["phone"]))
    if patient is None:
        patient = models.Patient(full_name=args.get("full_name"), phone=args["phone"])
        db.add(patient)
    elif args.get("full_name") and not patient.full_name:
        patient.full_name = args["full_name"]
    db.commit()
    db.refresh(patient)
    return json.dumps({"patient_id": patient.id, "full_name": patient.full_name})


def book_appointment(db: Session, args: dict) -> str:
    appt = create_appointment(
        db,
        int(args["patient_id"]),
        int(args["doctor_id"]),
        int(args["service_id"]),
        datetime.fromisoformat(args["start_time"]),
    )
    return json.dumps(_appt_dict(appt))


def my_appointments(db: Session, args: dict) -> str:
    rows = db.scalars(
        select(models.Appointment)
        .where(models.Appointment.patient_id == int(args["patient_id"]),
               models.Appointment.status.in_(ACTIVE_STATUSES))
        .order_by(models.Appointment.start_time)
    ).all()
    return json.dumps([_appt_dict(a) for a in rows])


def reschedule(db: Session, args: dict) -> str:
    appt = reschedule_appointment(
        db, int(args["appointment_id"]), datetime.fromisoformat(args["new_start_time"])
    )
    return json.dumps(_appt_dict(appt))


def cancel(db: Session, args: dict) -> str:
    appt = cancel_appointment(db, int(args["appointment_id"]))
    return json.dumps(_appt_dict(appt))


# Tool name (must match Vapi exactly) -> function
TOOLS = {
    "list_departments": list_departments,
    "list_doctors": list_doctors,
    "list_services": list_services,
    "check_availability": check_availability,
    "find_patient": find_patient,
    "register_patient": register_patient,
    "book_appointment": book_appointment,
    "my_appointments": my_appointments,
    "reschedule_appointment": reschedule,
    "cancel_appointment": cancel,
}

###-----------
def verify_vapi_secret(x_vapi_secret: str | None = Header(default=None)):
    """Reject any webhook call that doesn't carry the shared secret."""
    expected = os.getenv("VAPI_WEBHOOK_SECRET")
    if not expected:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "VAPI_WEBHOOK_SECRET is not set on the server")
    if x_vapi_secret is None or not secrets.compare_digest(x_vapi_secret, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret")
#----------------
def save_call_log(db: Session, message: dict) -> None:
    """Store one row per finished call. Ignores calls that were already saved."""
    call = message.get("call") or {}
    provider_id = call.get("id")
    if not provider_id:
        return

    existing = db.scalar(select(models.CallLog).where(models.CallLog.provider_call_id == provider_id))
    if existing is not None:
        return

    caller = (call.get("customer") or {}).get("number") or "unknown"
    transcript = message.get("transcript") or (message.get("artifact") or {}).get("transcript")
    started = call.get("startedAt")
    started_at = (datetime.fromisoformat(started.replace("Z", "+00:00")).replace(tzinfo=None)
                  if started else datetime.now())

    patient = db.scalar(select(models.Patient).where(models.Patient.phone == caller))
    db.add(models.CallLog(
        provider_call_id=provider_id,
        caller_phone=caller,
        patient_id=patient.id if patient else None,
        started_at=started_at,
        duration_sec=int(message.get("durationSeconds") or 0),
        transcript=transcript,
        outcome=None,  # filled in later, once we classify each call
    ))
    db.commit()
#-----------
# ---- Webhook: Vapi sends every tool call here ----
@router.post("/vapi/webhook")
def vapi_webhook(payload: dict = Body(...)):
    message = payload.get("message", {})
    msg_type = message.get("type")

    if msg_type == "end-of-call-report":
        db = SessionLocal()
        try:
            save_call_log(db, message)
        finally:
            db.close()
        return {}

    if msg_type != "tool-calls":
        return {}
    results = []
    db = SessionLocal()
    try:
        for call in message.get("toolCallList", []):
            # Vapi nests the name and arguments under "function"
            fn = call.get("function") or {}
            name = fn.get("name") or call.get("name")
            args = fn.get("arguments") or call.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)

            handler = TOOLS.get(name)
            try:
                output = handler(db, args) if handler else "Unknown tool."
            except BookingError as e:
                output = str(e)  # friendly booking-rule messages, safe to read aloud
            except Exception:
                db.rollback()
                output = "The system could not complete that. Please try a different option."

            results.append({"toolCallId": call["id"], "result": output})
    finally:
        db.close()

    return {"results": results}