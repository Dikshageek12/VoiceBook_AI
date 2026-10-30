from app import models
from app.routers.vapi import save_call_log


def test_call_is_saved_once(db):
    message = {
        "type": "end-of-call-report",
        "durationSeconds": 95,
        "call": {"id": "call-001", "startedAt": "2026-10-27T10:00:00Z",
                 "customer": {"number": "+919999900002"}},
        "artifact": {"transcript": "AI: Hello. User: I want a cardiology consultation."},
    }
    save_call_log(db, message)
    save_call_log(db, message)  # duplicate report must not create a second row

    logs = db.query(models.CallLog).all()
    assert len(logs) == 1
    assert logs[0].duration_sec == 95
    assert logs[0].caller_phone == "+919999900002"