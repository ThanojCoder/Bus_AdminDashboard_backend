from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Kiosk, Route, AdminUser
from schemas import KioskResponse, KioskCreate, KioskUpdate
from auth import get_current_user

router = APIRouter(prefix="/api/admin/kiosks", tags=["kiosks"])

def enrich_kiosk_response(kiosk: Kiosk, db: Session) -> KioskResponse:
    # Find matching route based on source
    route = None
    if kiosk.source:
        route = db.query(Route).filter(
            Route.source.ilike(kiosk.source.strip()),
            Route.is_active == True
        ).first()

    return KioskResponse(
        id=kiosk.id,
        kiosk_code=kiosk.kiosk_code,
        terminal_name=kiosk.location_name or kiosk.kiosk_code,
        source=kiosk.source,
        location_name=kiosk.location_name,
        status=kiosk.status,
        last_heartbeat_at=kiosk.last_heartbeat_at,
        route_id=route.id if route else None,
        route_name=f"{route.source} → {route.destination} ({route.route_code})" if route else None
    )

@router.get("", response_model=List[KioskResponse])
def get_kiosks(db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    kiosks = db.query(Kiosk).all()
    routes = db.query(Route).filter(Route.is_active == True).all()
    route_by_source = {r.source.strip().lower(): r for r in routes}

    results = []
    for k in kiosks:
        r = route_by_source.get(k.source.strip().lower()) if k.source else None
        results.append(
            KioskResponse(
                id=k.id,
                kiosk_code=k.kiosk_code,
                terminal_name=k.location_name or k.kiosk_code,
                source=k.source,
                location_name=k.location_name,
                status=k.status,
                last_heartbeat_at=k.last_heartbeat_at,
                route_id=r.id if r else None,
                route_name=f"{r.source} → {r.destination} ({r.route_code})" if r else None
            )
        )
    return results

@router.get("/{id}", response_model=KioskResponse)
def get_kiosk_detail(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    kiosk = db.query(Kiosk).filter(Kiosk.id == id).first()
    if not kiosk:
        raise HTTPException(status_code=404, detail="Kiosk not found")
    return enrich_kiosk_response(kiosk, db)

@router.post("", response_model=KioskResponse)
def register_kiosk(kiosk: KioskCreate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    data = kiosk.model_dump()
    source = data.get("source")
    route = None

    if data.get("route_id"):
        route = db.query(Route).filter(Route.id == data["route_id"]).first()
        if route:
            source = route.source

    if not source:
        raise HTTPException(status_code=400, detail="Source city or Route is required")

    source_clean = source.strip()
    code = (
        data.get("kiosk_code")
        or data.get("terminal_name")
        or f"K-{source_clean[:3].upper()}-01"
    )
    loc = (
        data.get("location_name")
        or data.get("terminal_name")
        or (f"{source_clean} Terminal - {route.route_code}" if route else f"{source_clean} Station")
    )

    db_kiosk = Kiosk(
        kiosk_code=code,
        source=source_clean,
        location_name=loc,
        status=kiosk.status
    )
    db.add(db_kiosk)
    db.commit()
    db.refresh(db_kiosk)

    return enrich_kiosk_response(db_kiosk, db)

@router.put("/{id}", response_model=KioskResponse)
def update_kiosk(id: int, kiosk: KioskUpdate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_kiosk = db.query(Kiosk).filter(Kiosk.id == id).first()
    if not db_kiosk:
        raise HTTPException(status_code=404, detail="Kiosk not found")
    
    update_data = kiosk.model_dump(exclude_unset=True)

    if update_data.get("route_id"):
        route = db.query(Route).filter(Route.id == update_data["route_id"]).first()
        if route:
            db_kiosk.source = route.source
            if not update_data.get("location_name") and not db_kiosk.location_name:
                db_kiosk.location_name = f"{route.source} Terminal - {route.route_code}"

    if "terminal_name" in update_data:
        term_name = update_data.pop("terminal_name")
        if "kiosk_code" not in update_data:
            update_data["kiosk_code"] = term_name
        if "location_name" not in update_data and not db_kiosk.location_name:
            update_data["location_name"] = term_name

    # Remove virtual route fields before setting on ORM model
    update_data.pop("route_id", None)
    update_data.pop("route_name", None)

    for key, value in update_data.items():
        if value is not None:
            setattr(db_kiosk, key, value)
        
    db.commit()
    db.refresh(db_kiosk)
    return enrich_kiosk_response(db_kiosk, db)

@router.post("/{id}/activate", response_model=KioskResponse)
def activate_kiosk(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_kiosk = db.query(Kiosk).filter(Kiosk.id == id).first()
    if not db_kiosk:
        raise HTTPException(status_code=404, detail="Kiosk not found")
    db_kiosk.status = "active"
    db.commit()
    db.refresh(db_kiosk)
    return enrich_kiosk_response(db_kiosk, db)

@router.delete("/{id}")
def delete_kiosk(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_kiosk = db.query(Kiosk).filter(Kiosk.id == id).first()
    if not db_kiosk:
        raise HTTPException(status_code=404, detail="Kiosk not found")
    db_kiosk.status = "inactive"
    db.commit()
    return {"message": "Kiosk deactivated"}
