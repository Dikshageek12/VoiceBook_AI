from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models
from app.database import get_db

router = APIRouter(tags=["calls"])


@router.get("/calls")
def list_calls(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.CallLog).order_by(models.CallLog.started_at.desc())).all()
    return [
        {
            "id": c.id,
            "provider_call_id": c.provider_call_id,
            "caller_phone": c.caller_phone,
            "patient_id": c.patient_id,
            "started_at": c.started_at.isoformat(timespec="seconds"),
            "duration_sec": c.duration_sec,
            "transcript": c.transcript,
            "outcome": c.outcome,
        }
        for c in rows
    ]