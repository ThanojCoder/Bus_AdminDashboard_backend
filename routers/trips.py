from typing import List, Optional
from datetime import date, datetime, time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Trip, Route, Bus, TripStatus, AdminUser
from schemas import TripResponse, TripCreate, TripUpdate
from auth import get_current_user
from routers.reports import resolve_date_range

router = APIRouter(prefix="/api/admin/trips", tags=["trips"])

def parse_time_str(val: str) -> time:
    if isinstance(val, time):
        return val
    val = str(val).strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I:%M %P", "%I:%M%P"):
        try:
            return datetime.strptime(val, fmt).time()
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Invalid time format: '{val}'. Expected format like '14:30' or '02:30 PM'")

@router.get("", response_model=List[TripResponse])
def get_trips(
    route_id: Optional[int] = None,
    travel_date: Optional[date] = None,
    range: Optional[str] = Query(None, description="Date range: today, yesterday, this_week, last_week, this_month, last_month"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    query = db.query(Trip).join(Bus, Trip.bus_id == Bus.id)
    if route_id:
        query = query.filter(Trip.route_id == route_id)
    if travel_date:
        query = query.filter(Trip.travel_date == travel_date)
    elif range and range.lower() != 'all':
        start_date, end_date = resolve_date_range(range)
        query = query.filter(Trip.travel_date >= start_date, Trip.travel_date <= end_date)
    
    trips = query.order_by(Trip.travel_date.desc(), Trip.departure_time.asc()).all()
    
    # We map the bus_type from the joined Bus to the response
    result = []
    for trip in trips:
        trip_dict = {
            "id": trip.id,
            "route_id": trip.route_id,
            "bus_id": trip.bus_id,
            "travel_date": trip.travel_date,
            "departure_time": trip.departure_time,
            "trip_duration": trip.trip_duration,
            "bus_type": trip.bus.bus_type,
            "total_seats": trip.total_seats,
            "booked_seats": trip.booked_seats,
            "held_seats": trip.held_seats,
            "status": trip.status,
        }
        result.append(TripResponse(**trip_dict))

    return result

@router.post("", response_model=TripResponse)
def create_trip(
    trip_in: TripCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    route = db.query(Route).filter(Route.id == trip_in.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
        
    bus = db.query(Bus).filter(Bus.id == trip_in.bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    # Check for conflict
    existing_trip = db.query(Trip).filter(
        Trip.route_id == trip_in.route_id,
        Trip.bus_id == trip_in.bus_id,
        Trip.travel_date == trip_in.travel_date
    ).first()

    if existing_trip:
        raise HTTPException(status_code=400, detail="Trip already exists for this route, bus, and date")

    dep_time = parse_time_str(trip_in.departure_time)

    new_trip = Trip(
        route_id=trip_in.route_id,
        bus_id=trip_in.bus_id,
        travel_date=trip_in.travel_date,
        departure_time=dep_time,
        trip_duration=trip_in.trip_duration,
        total_seats=bus.total_seats,
        booked_seats=0,
        held_seats=0,
        status=TripStatus.scheduled
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    
    trip_dict = {
        "id": new_trip.id,
        "route_id": new_trip.route_id,
        "bus_id": new_trip.bus_id,
        "travel_date": new_trip.travel_date,
        "departure_time": new_trip.departure_time,
        "trip_duration": new_trip.trip_duration,
        "bus_type": bus.bus_type,
        "total_seats": new_trip.total_seats,
        "booked_seats": new_trip.booked_seats,
        "held_seats": new_trip.held_seats,
        "status": new_trip.status,
    }
    
    return TripResponse(**trip_dict)

@router.put("/{id}", response_model=TripResponse)
def update_trip(
    id: int,
    trip_in: TripUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    db_trip = db.query(Trip).filter(Trip.id == id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip_in.travel_date:
        if trip_in.travel_date != db_trip.travel_date:
            existing_trip = db.query(Trip).filter(
                Trip.route_id == db_trip.route_id,
                Trip.bus_id == db_trip.bus_id,
                Trip.travel_date == trip_in.travel_date,
                Trip.id != id
            ).first()
            if existing_trip:
                raise HTTPException(status_code=400, detail="Another trip already exists for this route, bus, and date")
        db_trip.travel_date = trip_in.travel_date

    if trip_in.departure_time:
        db_trip.departure_time = parse_time_str(trip_in.departure_time)
    if trip_in.trip_duration is not None:
        db_trip.trip_duration = trip_in.trip_duration
    if trip_in.status:
        db_trip.status = trip_in.status

    db.commit()
    db.refresh(db_trip)
    
    bus = db.query(Bus).filter(Bus.id == db_trip.bus_id).first()

    trip_dict = {
        "id": db_trip.id,
        "route_id": db_trip.route_id,
        "bus_id": db_trip.bus_id,
        "travel_date": db_trip.travel_date,
        "departure_time": db_trip.departure_time,
        "trip_duration": db_trip.trip_duration,
        "bus_type": bus.bus_type if bus else None,
        "total_seats": db_trip.total_seats,
        "booked_seats": db_trip.booked_seats,
        "held_seats": db_trip.held_seats,
        "status": db_trip.status,
    }
    
    return TripResponse(**trip_dict)

@router.delete("/{id}")
def delete_trip(
    id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    db_trip = db.query(Trip).filter(Trip.id == id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
        
    if db_trip.booked_seats > 0:
        raise HTTPException(status_code=400, detail="Cannot delete trip with booked seats. Please cancel instead.")
        
    # Or just mark as cancelled instead of hard delete
    db_trip.status = TripStatus.cancelled
    db.commit()
    return {"message": "Trip cancelled successfully"}
