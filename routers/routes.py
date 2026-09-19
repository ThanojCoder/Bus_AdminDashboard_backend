from typing import List, Optional
from datetime import datetime, date, time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Route, RouteBusAssignment, Bus, Trip, TripStatus, Kiosk, AdminUser
from schemas import (
    RouteResponse, RouteCreate, RouteUpdate,
    AssignmentCreate, AssignmentResponse,
    AssignedBusItem, AssignedKioskItem
)
from auth import get_current_user

router = APIRouter(prefix="/api/admin/routes", tags=["routes"])

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

@router.get("", response_model=List[RouteResponse])
def get_routes(source: Optional[str] = None, destination: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Route)
    if source:
        query = query.filter(Route.source == source)
    if destination:
        query = query.filter(Route.destination == destination)
    routes = query.all()

    today = date.today()
    all_kiosks = db.query(Kiosk).all()

    result = []
    for r in routes:
        # Get active bus assignments
        assignments = (
            db.query(RouteBusAssignment, Bus)
            .join(Bus, RouteBusAssignment.bus_id == Bus.id)
            .filter(RouteBusAssignment.route_id == r.id, RouteBusAssignment.is_active == True)
            .all()
        )

        assigned_buses = []
        for assign, bus in assignments:
            # Check today's trip
            trip = db.query(Trip).filter(
                Trip.route_id == r.id,
                Trip.bus_id == bus.id,
                Trip.travel_date == today
            ).first()

            dep_str = assign.departure_time.strftime("%I:%M %p") if assign.departure_time else "N/A"
            assigned_buses.append(
                AssignedBusItem(
                    assignment_id=assign.id,
                    bus_id=bus.id,
                    bus_number=bus.bus_number,
                    bus_type=bus.bus_type.value if hasattr(bus.bus_type, "value") else str(bus.bus_type),
                    total_seats=bus.total_seats,
                    departure_time=dep_str,
                    is_active=assign.is_active,
                    trip_id=trip.id if trip else None
                )
            )

        # Get kiosks serving this route (where kiosk.source matches route.source)
        assigned_kiosks = [
            AssignedKioskItem(
                kiosk_id=k.id,
                kiosk_code=k.kiosk_code,
                terminal_name=k.location_name or k.kiosk_code,
                source=k.source,
                location_name=k.location_name,
                status=k.status.value if hasattr(k.status, "value") else str(k.status)
            )
            for k in all_kiosks
            if k.source and k.source.strip().lower() == r.source.strip().lower()
        ]

        route_dict = {
            "id": r.id,
            "route_code": r.route_code,
            "source": r.source,
            "destination": r.destination,
            "base_fare": float(r.base_fare),
            "is_active": r.is_active,
            "created_at": r.created_at,
            "assigned_buses": assigned_buses,
            "assigned_kiosks": assigned_kiosks
        }
        result.append(RouteResponse(**route_dict))

    return result

@router.post("", response_model=RouteResponse)
def create_route(route: RouteCreate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_route = Route(**route.model_dump(), created_by=current_user.id)
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return RouteResponse(
        id=db_route.id,
        route_code=db_route.route_code,
        source=db_route.source,
        destination=db_route.destination,
        base_fare=float(db_route.base_fare),
        is_active=db_route.is_active,
        created_at=db_route.created_at,
        assigned_buses=[],
        assigned_kiosks=[]
    )

@router.put("/{id}", response_model=RouteResponse)
def update_route(id: int, route: RouteUpdate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_route = db.query(Route).filter(Route.id == id).first()
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    update_data = route.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_route, key, value)
    
    db.commit()
    db.refresh(db_route)
    return RouteResponse(
        id=db_route.id,
        route_code=db_route.route_code,
        source=db_route.source,
        destination=db_route.destination,
        base_fare=float(db_route.base_fare),
        is_active=db_route.is_active,
        created_at=db_route.created_at,
        assigned_buses=[],
        assigned_kiosks=[]
    )

@router.delete("/{id}")
def delete_route(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_route = db.query(Route).filter(Route.id == id).first()
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")
    db_route.is_active = False
    db.commit()
    return {"message": "Route deactivated"}

@router.post("/{id}/activate")
def activate_route(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_route = db.query(Route).filter(Route.id == id).first()
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")
    db_route.is_active = True
    db.commit()
    return {"message": "Route activated"}

# Route-Bus Assignments
@router.post("/{id}/buses", response_model=AssignmentResponse)
def assign_bus_to_route(id: int, assignment: AssignmentCreate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    route = db.query(Route).filter(Route.id == id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    bus = db.query(Bus).filter(Bus.id == assignment.bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    dep_time = parse_time_str(assignment.departure_time)

    # Check existing assignment
    db_assignment = db.query(RouteBusAssignment).filter(
        RouteBusAssignment.route_id == id,
        RouteBusAssignment.bus_id == assignment.bus_id
    ).first()

    if db_assignment:
        db_assignment.is_active = True
        db_assignment.departure_time = dep_time
    else:
        db_assignment = RouteBusAssignment(
            route_id=id,
            bus_id=assignment.bus_id,
            departure_time=dep_time,
            is_active=True
        )
        db.add(db_assignment)

    # Automatically create or activate today's Trip so kiosks have live booking inventory
    today = date.today()
    trip = db.query(Trip).filter(
        Trip.route_id == id,
        Trip.bus_id == bus.id,
        Trip.travel_date == today
    ).first()

    if not trip:
        new_trip = Trip(
            route_id=id,
            bus_id=bus.id,
            travel_date=today,
            departure_time=dep_time,
            trip_duration=assignment.trip_duration or "8h",
            total_seats=bus.total_seats,
            booked_seats=0,
            held_seats=0,
            status=TripStatus.scheduled
        )
        db.add(new_trip)
    else:
        if trip.status == TripStatus.cancelled:
            trip.status = TripStatus.scheduled
        trip.departure_time = dep_time

    db.commit()
    db.refresh(db_assignment)

    return AssignmentResponse(
        id=db_assignment.id,
        route_id=db_assignment.route_id,
        bus_id=db_assignment.bus_id,
        departure_time=db_assignment.departure_time,
        is_active=db_assignment.is_active,
        bus_number=bus.bus_number,
        bus_type=bus.bus_type.value if hasattr(bus.bus_type, "value") else str(bus.bus_type),
        total_seats=bus.total_seats
    )

@router.put("/{id}/buses/{bus_id}", response_model=AssignmentResponse)
def update_assignment(id: int, bus_id: int, departure_time: str, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_assignment = db.query(RouteBusAssignment).filter(
        RouteBusAssignment.route_id == id,
        RouteBusAssignment.bus_id == bus_id
    ).first()
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    dep_time = parse_time_str(departure_time)
    db_assignment.departure_time = dep_time

    # Also update today's trip departure time if present
    today = date.today()
    trip = db.query(Trip).filter(
        Trip.route_id == id,
        Trip.bus_id == bus_id,
        Trip.travel_date == today
    ).first()
    if trip:
        trip.departure_time = dep_time

    db.commit()
    db.refresh(db_assignment)

    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    return AssignmentResponse(
        id=db_assignment.id,
        route_id=db_assignment.route_id,
        bus_id=db_assignment.bus_id,
        departure_time=db_assignment.departure_time,
        is_active=db_assignment.is_active,
        bus_number=bus.bus_number if bus else None,
        bus_type=bus.bus_type.value if bus and hasattr(bus.bus_type, "value") else (str(bus.bus_type) if bus else None),
        total_seats=bus.total_seats if bus else None
    )

@router.delete("/{id}/buses/{bus_id}")
def unassign_bus(id: int, bus_id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    db_assignment = db.query(RouteBusAssignment).filter(
        RouteBusAssignment.route_id == id,
        RouteBusAssignment.bus_id == bus_id,
        RouteBusAssignment.is_active == True
    ).first()
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found")
    
    db_assignment.is_active = False

    # Cancel today's trip if 0 seats booked
    today = date.today()
    trip = db.query(Trip).filter(
        Trip.route_id == id,
        Trip.bus_id == bus_id,
        Trip.travel_date == today
    ).first()
    if trip and trip.booked_seats == 0:
        trip.status = TripStatus.cancelled

    db.commit()
    return {"message": "Bus unassigned from route"}
