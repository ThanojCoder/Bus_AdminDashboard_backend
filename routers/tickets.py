import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Order, Trip, AdminUser
from schemas import OrderResponse, OrderPaginationResponse
from auth import get_current_user
from datetime import date

from sqlalchemy import func
from routers.reports import resolve_date_range

router = APIRouter(prefix="/api/admin/orders", tags=["tickets"])

@router.get("", response_model=OrderPaginationResponse)
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=5000),
    route_id: Optional[int] = None,
    travel_date: Optional[date] = None,
    kiosk_id: Optional[int] = None,
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    range: Optional[str] = Query(None, description="Date range: today, yesterday, this_week, last_week, this_month, last_month"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    query = db.query(Order).join(Trip)
    
    if route_id:
        query = query.filter(Trip.route_id == route_id)
    if travel_date:
        query = query.filter(Trip.travel_date == travel_date)
    if kiosk_id:
        query = query.filter(Order.kiosk_id == kiosk_id)
    if status and status != "all":
        query = query.filter(Order.booking_status == status)
    if payment_status and payment_status != "all":
        query = query.filter(Order.payment_status == payment_status)
    if range:
        start_date, end_date = resolve_date_range(range)
        query = query.filter(
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date
        )
        
    query = query.order_by(Order.created_at.desc())

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    offset = max(0, (page - 1) * page_size)

    items = query.offset(offset).limit(page_size).all()

    for item in items:
        if item.trip and item.trip.route:
            setattr(item, "route_code", item.trip.route.route_code)
            setattr(item, "route_name", f"{item.trip.route.source} → {item.trip.route.destination}")
        if item.trip and item.trip.bus:
            setattr(item, "bus_number", item.trip.bus.bus_number)
        if item.trip:
            setattr(item, "travel_date", item.trip.travel_date)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/{id}", response_model=OrderResponse)
def get_order_detail(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/{id}/cancel")
def cancel_order(id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.booking_status == "cancelled":
        raise HTTPException(status_code=400, detail="Order already cancelled")
        
    order.booking_status = "cancelled"
    order.payment_status = "refunded"
    
    # Decrement booked_seats on trip
    trip = db.query(Trip).filter(Trip.id == order.trip_id).first()
    if trip:
        trip.booked_seats = max(0, trip.booked_seats - order.total_seats)
        
    db.commit()
    return {"message": "Order cancelled and refunded"}
