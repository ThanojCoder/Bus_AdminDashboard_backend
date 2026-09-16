from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timezone
from database import get_db
from models import Bus, AdminUser, Trip, Order, SeatHold, TripStatus
from schemas import BusResponse, BusCreate, BusUpdate
from auth import get_current_user

router = APIRouter(prefix="/api/admin/buses", tags=["buses"])

@router.get("", response_model=List[BusResponse])
def get_buses(db: Session = Depends(get_db)):
    today = date.today()
    buses = db.query(Bus).all()
    trips = db.query(Trip).filter(Trip.travel_date == today, Trip.status != 'cancelled').all()
    trip_map = {t.bus_id: t for t in trips}
    
    response_list = []
    for bus in buses:
        trip = trip_map.get(bus.id)
        if trip:
            avail = max(0, trip.total_seats - trip.booked_seats - trip.held_seats)
            route_desc = f"{trip.route.source} → {trip.route.destination}" if trip.route else None
            response_list.append(BusResponse(
                id=bus.id,
                bus_number=bus.bus_number,
                bus_type=bus.bus_type,
                total_seats=bus.total_seats,
                is_active=bus.is_active,
                available_seats=avail,
                booked_seats=trip.booked_seats,
                held_seats=trip.held_seats,
                has_trip_today=True,
                trip_id=trip.id,
                route_name=route_desc
            ))
        else:
            response_list.append(BusResponse(
                id=bus.id,
                bus_number=bus.bus_number,
                bus_type=bus.bus_type,
                total_seats=bus.total_seats,
                is_active=bus.is_active,
                available_seats=bus.total_seats,
                booked_seats=0,
                held_seats=0,
                has_trip_today=False,
                trip_id=None,
                route_name=None
            ))
    return response_list

@router.post("", response_model=BusResponse)
def create_bus(bus: BusCreate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_bus = Bus(**bus.model_dump())
    db.add(db_bus)
    db.commit()
    db.refresh(db_bus)
    return db_bus

@router.put("/{id}", response_model=BusResponse)
def update_bus(id: int, bus: BusUpdate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_bus = db.query(Bus).filter(Bus.id == id).first()
    if not db_bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    
    update_data = bus.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_bus, key, value)
    
    db.commit()
    db.refresh(db_bus)
    return db_bus

@router.delete("/{id}")
def delete_bus(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_bus = db.query(Bus).filter(Bus.id == id).first()
    if not db_bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    db_bus.is_active = False
    db.commit()
    return {"message": "Bus deactivated"}

@router.post("/{id}/release-seats")
def release_bus_seats(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_bus = db.query(Bus).filter(Bus.id == id).first()
    if not db_bus:
        raise HTTPException(status_code=404, detail="Bus not found")
        
    today = date.today()
    trip = db.query(Trip).filter(Trip.bus_id == id, Trip.travel_date == today).first()
    
    if not trip:
        raise HTTPException(
            status_code=400, 
            detail="No active trip found for this bus today to release seats"
        )
        
    # Release any active temporary holds
    db.query(SeatHold).filter(SeatHold.trip_id == trip.id, SeatHold.status == "active").update(
        {"status": "released"}
    )
    
    # Reset trip seat counters so new passengers can book tickets
    trip.total_seats = db_bus.total_seats
    trip.booked_seats = 0
    trip.held_seats = 0
    trip.status = TripStatus.scheduled
    trip.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(trip)
    
    return {
        "message": f"Successfully released all seats for bus {db_bus.bus_number}. Bus is now ready for new bookings.",
        "bus_number": db_bus.bus_number,
        "total_seats": trip.total_seats,
        "available_seats": trip.total_seats
    }

@router.get("/{id}/layout")
def get_bus_layout(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_bus = db.query(Bus).filter(Bus.id == id).first()
    if not db_bus:
        raise HTTPException(status_code=404, detail="Bus not found")
        
    today = date.today()
    trip = db.query(Trip).filter(Trip.bus_id == id, Trip.travel_date == today).first()
    
    occupied_seats = []
    held_seats = []
    
    if trip:
        # Collect actual occupied seat numbers from most recent confirmed orders matching trip.booked_seats
        if trip.booked_seats > 0:
            recent_orders = db.query(Order).filter(
                Order.trip_id == trip.id,
                Order.booking_status == "confirmed"
            ).order_by(Order.id.desc()).all()
            
            for o in recent_orders:
                if len(occupied_seats) >= trip.booked_seats:
                    break
                seats = [int(s.strip()) for s in o.seat_numbers.split(",") if s.strip()]
                for s in seats:
                    if s not in occupied_seats and len(occupied_seats) < trip.booked_seats:
                        occupied_seats.append(s)
            occupied_seats.sort()

        # Collect actual held seat numbers from active, unexpired holds matching trip.held_seats
        if trip.held_seats > 0:
            now = datetime.now(timezone.utc)
            active_holds = db.query(SeatHold).filter(
                SeatHold.trip_id == trip.id,
                SeatHold.status == "active"
            ).order_by(SeatHold.id.desc()).all()
            
            for h in active_holds:
                if len(held_seats) >= trip.held_seats:
                    break
                if h.expires_at:
                    exp = h.expires_at if h.expires_at.tzinfo else h.expires_at.replace(tzinfo=timezone.utc)
                    if exp < now:
                        continue
                seats = [int(s.strip()) for s in h.seat_numbers.split(",") if s.strip()]
                for s in seats:
                    if s not in held_seats and s not in occupied_seats and len(held_seats) < trip.held_seats:
                        held_seats.append(s)
            held_seats.sort()

        # Keep trip.held_seats in sync with active holds
        if trip.held_seats != len(held_seats):
            trip.held_seats = len(held_seats)
            db.commit()

    all_seats = list(range(1, db_bus.total_seats + 1))
    taken_seats_set = set(occupied_seats) | set(held_seats)
    free_seats = [s for s in all_seats if s not in taken_seats_set]

    available_count = len(free_seats)

    return {
        "bus_number": db_bus.bus_number,
        "total_seats": db_bus.total_seats,
        "has_trip_today": trip is not None,
        # Actual lists of seat numbers
        "occupied_seats": occupied_seats,
        "occupied_seat_numbers": occupied_seats,
        "held_seats": held_seats,
        "held_seat_numbers": held_seats,
        "free_seats": free_seats,
        "available_seat_numbers": free_seats,
        # Numeric counts
        "available_seats": available_count,
        "available_seats_count": available_count,
        "booked_seats": len(occupied_seats),
        "occupied_seats_count": len(occupied_seats),
        "held_seats_count": len(held_seats),
    }

