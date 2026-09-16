import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DECIMAL,
    ForeignKey,
    Date,
    Time,
    DateTime,
    Enum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    manager = "manager"


class BusTypeEnum(str, enum.Enum):
    seater = "seater"
    sleeper = "sleeper"
    ac = "ac"
    non_ac = "non_ac"


class TripStatus(str, enum.Enum):
    scheduled = "scheduled"
    filling = "filling"
    full = "full"
    departed = "departed"
    cancelled = "cancelled"


class KioskStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"


class HoldStatus(str, enum.Enum):
    active = "active"
    converted = "converted"
    expired = "expired"
    released = "released"


class PaymentModeEnum(str, enum.Enum):
    card = "card"
    upi = "upi"


class PaymentStatusEnum(str, enum.Enum):
    paid = "paid"
    refunded = "refunded"


class BookingStatusEnum(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"


class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(AdminRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Route(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_code = Column(String(100), unique=True, nullable=False)
    source = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    base_fare = Column(DECIMAL(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("admin_users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    creator = relationship("AdminUser")


class Bus(Base):
    __tablename__ = "buses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_number = Column(String(100), unique=True, nullable=False)
    bus_type = Column(Enum(BusTypeEnum), nullable=False)
    total_seats = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class RouteBusAssignment(Base):
    __tablename__ = "route_bus_assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    departure_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    route = relationship("Route")
    bus = relationship("Bus")

    __table_args__ = (
        Index(
            "unique_active_route_bus",
            "route_id",
            "bus_id",
            postgresql_where=(is_active == True),
            unique=True,
        ),
    )


class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    travel_date = Column(Date, nullable=False)
    departure_time = Column(Time, nullable=False)
    trip_duration = Column(String(50), nullable=True)
    total_seats = Column(Integer, nullable=False)
    booked_seats = Column(Integer, default=0)
    held_seats = Column(Integer, default=0)
    status = Column(Enum(TripStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    route = relationship("Route")
    bus = relationship("Bus")

    __table_args__ = (
        UniqueConstraint(
            "route_id", "bus_id", "travel_date", name="uix_trip_route_bus_date"
        ),
        Index("idx_trips_route_date_status", "route_id", "travel_date", "status"),
    )


class Kiosk(Base):
    __tablename__ = "kiosks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    kiosk_code = Column(String(100), unique=True, nullable=False)
    source = Column(String(255), nullable=False)
    location_name = Column(String(255), nullable=False)
    status = Column(Enum(KioskStatus), nullable=False)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SeatHold(Base):
    __tablename__ = "seat_holds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    kiosk_id = Column(Integer, ForeignKey("kiosks.id"), nullable=False)
    seats_held = Column(Integer, nullable=False)
    seat_numbers = Column(String(255), nullable=False)
    status = Column(Enum(HoldStatus), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    trip = relationship("Trip")
    kiosk = relationship("Kiosk")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(100), unique=True, nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    hold_id = Column(Integer, ForeignKey("seat_holds.id"), nullable=False)
    kiosk_id = Column(Integer, ForeignKey("kiosks.id"), nullable=False)
    total_seats = Column(Integer, nullable=False)
    seat_numbers = Column(String(255), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    payment_status = Column(Enum(PaymentStatusEnum), nullable=False)
    payment_mode = Column(Enum(PaymentModeEnum), nullable=False)
    booking_status = Column(Enum(BookingStatusEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    trip = relationship("Trip")
    hold = relationship("SeatHold")
    kiosk = relationship("Kiosk")
