from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Order, Trip, AdminUser
from auth import get_current_user
from datetime import date, datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/api/admin/reports", tags=["reports"])

def resolve_date_range(range_name: str) -> tuple[date, date]:
    today = date.today()
    r = (range_name or "today").lower().strip()
    
    if r == "yesterday":
        yest = today - timedelta(days=1)
        return yest, yest
    elif r == "this_week":
        # Monday of current week to today
        start = today - timedelta(days=today.weekday())
        return start, today
    elif r == "last_week":
        # Monday of previous week to Sunday of previous week
        this_monday = today - timedelta(days=today.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        return last_monday, last_sunday
    elif r == "this_month":
        # 1st of current month to today
        start = today.replace(day=1)
        return start, today
    elif r == "last_month":
        # 1st of previous month to last day of previous month
        first_this_month = today.replace(day=1)
        last_day_prev_month = first_this_month - timedelta(days=1)
        first_prev_month = last_day_prev_month.replace(day=1)
        return first_prev_month, last_day_prev_month
    else:  # "today" by default
        return today, today

@router.get("/summary")
def get_summary(
    range: Optional[str] = Query("today", description="Date range: today, yesterday, this_week, last_week, this_month, last_month"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    start_date, end_date = resolve_date_range(range or "today")
    
    # 1. Trips operating in range
    trips_in_range = db.query(Trip).filter(Trip.travel_date >= start_date, Trip.travel_date <= end_date).all()
    total_trips = len(trips_in_range)
    total_capacity = sum(trip.total_seats for trip in trips_in_range)
    trip_booked_seats = sum(trip.booked_seats for trip in trips_in_range)
    
    # 2. Revenue in range
    # Priority: Orders created in this date range
    rev_created = db.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) >= start_date,
        func.date(Order.created_at) <= end_date,
        Order.booking_status == 'confirmed'
    ).scalar() or 0
    
    rev_trips = db.query(func.sum(Order.total_amount)).join(Trip).filter(
        Trip.travel_date >= start_date,
        Trip.travel_date <= end_date,
        Order.booking_status == 'confirmed'
    ).scalar() or 0
    
    total_revenue = float(rev_created) if rev_created > 0 else float(rev_trips)
    
    # 3. Bookings in range
    bookings_created = db.query(func.sum(Order.total_seats)).filter(
        func.date(Order.created_at) >= start_date,
        func.date(Order.created_at) <= end_date,
        Order.booking_status == 'confirmed'
    ).scalar() or 0
    
    total_bookings = int(bookings_created) if bookings_created > 0 else trip_booked_seats
    
    # 4. Occupancy rate
    if total_capacity > 0:
        occupancy_rate = (trip_booked_seats / total_capacity * 100)
    elif total_bookings > 0:
        occupancy_rate = 100.0
    else:
        occupancy_rate = 0.0
    
    return {
        "range": range,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "total_bookings": total_bookings,
        "total_revenue": round(total_revenue, 2),
        "occupancy_rate_percentage": round(occupancy_rate, 2),
        "total_trips": total_trips
    }

@router.get("/route-performance")
def get_route_performance(from_date: date, to_date: date, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    # Performance over a date range
    trips = db.query(Trip).filter(Trip.travel_date >= from_date, Trip.travel_date <= to_date).all()
    
    route_stats = {}
    for trip in trips:
        if trip.route_id not in route_stats:
            route_stats[trip.route_id] = {
                "total_seats": 0,
                "booked_seats": 0,
                "trips_count": 0
            }
        route_stats[trip.route_id]["total_seats"] += trip.total_seats
        route_stats[trip.route_id]["booked_seats"] += trip.booked_seats
        route_stats[trip.route_id]["trips_count"] += 1
        
    for r_id, stat in route_stats.items():
        stat["occupancy_rate"] = (stat["booked_seats"] / stat["total_seats"] * 100) if stat["total_seats"] > 0 else 0
        
    return route_stats

@router.get("/today-trips")
def get_today_trips(
    range: Optional[str] = Query("today"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    start_date, end_date = resolve_date_range(range or "today")
    trips = db.query(Trip).filter(
        Trip.travel_date >= start_date,
        Trip.travel_date <= end_date
    ).order_by(Trip.travel_date.desc(), Trip.departure_time.asc()).all()
    
    result = []
    for t in trips:
        t_dict = {
            "id": t.id,
            "travel_date": str(t.travel_date),
            "route_code": t.route.route_code if t.route else "",
            "source": t.route.source if t.route else "",
            "destination": t.route.destination if t.route else "",
            "departure_time": str(t.departure_time),
            "status": t.status,
            "total_seats": t.bus.total_seats if t.bus else t.total_seats,
            "booked_seats": t.booked_seats,
            "held_seats": t.held_seats,
            "available_seats": (t.bus.total_seats if t.bus else t.total_seats) - t.booked_seats - t.held_seats,
            "bus_number": t.bus.bus_number if t.bus else ""
        }
        result.append(t_dict)
        
    return result
