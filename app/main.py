from fastapi import FastAPI, Request
from app.routers import appointments, calls, catalog, dashboard, vapi
from app.services.booking import BookingError
from pathlib import Path
import os
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="VoiceBook AI API", version="0.2.0")

app.include_router(catalog.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(vapi.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.exception_handler(BookingError)
async def booking_error_handler(request: Request, exc: BookingError):
    """Any booking rule violation becomes a 409 with a message safe to read aloud."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

DASHBOARD_FILE = Path(__file__).parent / "static" / "dashboard.html"
@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return FileResponse(DASHBOARD_FILE)

CALL_PAGE_FILE = Path(__file__).parent / "static" / "call.html"


@app.get("/call", include_in_schema=False)
def call_page():
    return FileResponse(CALL_PAGE_FILE)


@app.get("/api/public-config", include_in_schema=False)
def public_config():
    """Gives the browser only the public key and assistant ID, never the private key."""
    return JSONResponse({
        "public_key": os.getenv("VAPI_PUBLIC_KEY", ""),
        "assistant_id": os.getenv("VAPI_ASSISTANT_ID", ""),
    })