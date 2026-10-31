from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.schemas import AvailabilityOut, DepartmentOut, DoctorOut, ServiceOut
from app.services.availability import get_available_slots

router = APIRouter(tags=["catalog"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.scalars(select(models.Department).order_by(models.Department.name)).all()


@router.get("/doctors", response_model=list[DoctorOut])
def list_doctors(department_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.Doctor)
    if department_id is not None:
        query = query.where(models.Doctor.department_id == department_id)
    return db.scalars(query).all()


@router.get("/services", response_model=list[ServiceOut])
def list_services(department_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.Service)
    if department_id is not None:
        query = query.where(models.Service.department_id == department_id)
    return db.scalars(query).all()


@router.get("/calendar/availability", response_model=AvailabilityOut)
def availability(doctor_id: int, service_id: int, date_from: date, date_to: date,
                 db: Session = Depends(get_db)):
    if date_to < date_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_to must be on or after date_from")
    if (date_to - date_from).days > 14:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Date range is limited to 14 days")
    try:
        slots = get_available_slots(db, doctor_id, service_id, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return AvailabilityOut(
        doctor_id=doctor_id,
        service_id=service_id,
        slots=[s.isoformat(timespec="minutes") for s in slots[:50]],
    )