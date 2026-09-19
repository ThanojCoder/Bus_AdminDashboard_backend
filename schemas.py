from datetime import date, datetime, time
from typing import List, Optional
from pydantic import BaseModel, EmailStr, model_validator
from models import (
    AdminRole,
    BookingStatusEnum,
    BusTypeEnum,
    HoldStatus,
    KioskStatus,
    PaymentModeEnum,
    PaymentStatusEnum,
    TripStatus,
)


# --- Token & Auth ---
class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: AdminRole
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[AdminUserResponse] = None


class TokenData(BaseModel):
    email: Optional[str] = None


class AdminUserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: AdminRole


# --- Routes ---
class RouteBase(BaseModel):
    route_code: str
    source: str
    destination: str
    base_fare: float


class RouteCreate(RouteBase):
    pass


class RouteUpdate(RouteBase):
    pass


class AssignedBusItem(BaseModel):
    assignment_id: int
    bus_id: int
    bus_number: str
    bus_type: str
    total_seats: int
    departure_time: str
    is_active: bool = True
    trip_id: Optional[int] = None


class AssignedKioskItem(BaseModel):
    kiosk_id: int
    kiosk_code: str
    terminal_name: str
    source: str
    location_name: str
    status: str


class RouteResponse(RouteBase):
    id: int
    is_active: bool
    created_at: datetime
    assigned_buses: Optional[List[AssignedBusItem]] = []
    assigned_kiosks: Optional[List[AssignedKioskItem]] = []

    class Config:
        from_attributes = True


# --- Buses ---
class BusBase(BaseModel):
    bus_number: str
    bus_type: BusTypeEnum
    total_seats: int


class BusCreate(BusBase):
    pass


class BusUpdate(BusBase):
    pass


class BusResponse(BusBase):
    id: int
    is_active: bool
    available_seats: Optional[int] = None
    booked_seats: Optional[int] = None
    held_seats: Optional[int] = None
    has_trip_today: Optional[bool] = False
    trip_id: Optional[int] = None
    route_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Route Bus Assignments ---
class AssignmentCreate(BaseModel):
    bus_id: int
    departure_time: str
    trip_duration: Optional[str] = "8h"


class AssignmentResponse(BaseModel):
    id: int
    route_id: int
    bus_id: int
    departure_time: time
    is_active: bool
    bus_number: Optional[str] = None
    bus_type: Optional[str] = None
    total_seats: Optional[int] = None

    class Config:
        from_attributes = True


# --- Trips ---
class TripCreate(BaseModel):
    route_id: int
    bus_id: int
    travel_date: date
    departure_time: str
    trip_duration: Optional[str] = "8h"


class TripUpdate(BaseModel):
    travel_date: Optional[date] = None
    departure_time: Optional[str] = None
    trip_duration: Optional[str] = None
    status: Optional[TripStatus] = None


class TripResponse(BaseModel):
    id: int
    route_id: int
    bus_id: int
    travel_date: date
    departure_time: time
    trip_duration: Optional[str] = None
    bus_type: Optional[BusTypeEnum] = None
    total_seats: int
    booked_seats: int
    held_seats: int
    status: TripStatus

    class Config:
        from_attributes = True


class TripAppResponse(TripResponse):
    available_seats: int


# --- Kiosks ---
class KioskBase(BaseModel):
    kiosk_code: Optional[str] = None
    terminal_name: Optional[str] = None
    source: Optional[str] = None
    location_name: Optional[str] = None
    status: KioskStatus = KioskStatus.active
    route_id: Optional[int] = None
    route_name: Optional[str] = None


class KioskCreate(KioskBase):
    pass


class KioskUpdate(BaseModel):
    kiosk_code: Optional[str] = None
    terminal_name: Optional[str] = None
    source: Optional[str] = None
    location_name: Optional[str] = None
    status: Optional[KioskStatus] = None
    route_id: Optional[int] = None
    route_name: Optional[str] = None


class KioskResponse(KioskBase):
    id: int
    last_heartbeat_at: Optional[datetime] = None

    @model_validator(mode="after")
    def ensure_names(self):
        if not self.kiosk_code and self.terminal_name:
            self.kiosk_code = self.terminal_name
        if not self.terminal_name and self.kiosk_code:
            self.terminal_name = self.kiosk_code
        if not self.location_name:
            self.location_name = self.source
        return self

    class Config:
        from_attributes = True


# --- Holds ---
class HoldCreate(BaseModel):
    trip_id: int
    seats: int


class HoldResponse(BaseModel):
    id: int
    trip_id: int
    kiosk_id: int
    seats_held: int
    seat_numbers: str
    status: HoldStatus
    expires_at: datetime

    class Config:
        from_attributes = True


# --- Payments & Orders ---
class PaymentRequest(BaseModel):
    hold_id: int
    payment_mode: PaymentModeEnum


class OrderResponse(BaseModel):
    id: int
    order_number: str
    trip_id: int
    hold_id: int
    kiosk_id: int
    total_seats: int
    seat_numbers: str
    total_amount: float
    payment_status: PaymentStatusEnum
    payment_mode: PaymentModeEnum
    booking_status: BookingStatusEnum
    created_at: datetime
    payment_session_id: Optional[str] = None
    qr_string: Optional[str] = None
    route_code: Optional[str] = None
    route_name: Optional[str] = None
    bus_number: Optional[str] = None
    travel_date: Optional[date] = None

    class Config:
        from_attributes = True


class OrderPaginationResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class TicketPrintResponse(BaseModel):
    order_number: str
    route_code: str
    source: str
    destination: str
    bus_number: str
    travel_date: date
    departure_time: time
    seat_numbers: str
    total_amount: float
    payment_mode: PaymentModeEnum


# --- Heartbeat ---
class HeartbeatRequest(BaseModel):
    status: KioskStatus
