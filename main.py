import sys
import time as time_module
from pathlib import Path

# Add project root to sys.path so imports work both standalone and when run from root
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import auth, routes, buses, tickets, kiosks, reports

app = FastAPI(title="Bus Booking Admin Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(routes.router)
app.include_router(buses.router)
app.include_router(tickets.router)
app.include_router(kiosks.router)
app.include_router(reports.router)


def init_db_and_seed():
    """Create database tables and seed starter data if database is empty, with retry logic."""
    max_retries = 5
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[DB] Attempting database initialization (attempt {attempt}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            try:
                from models import (
                    AdminUser,
                    AdminRole,
                    Route,
                    Bus,
                    BusTypeEnum,
                    RouteBusAssignment,
                    Trip,
                    TripStatus,
                    Kiosk,
                    KioskStatus,
                )
                from auth import get_password_hash
                from datetime import date, time

                # 1. Super Admin
                admin = db.query(AdminUser).first()
                if not admin:
                    print("[Info] No admin user found. Seeding default super-admin...")
                    admin = AdminUser(
                        name="Admin User",
                        email="admin@example.com",
                        password_hash=get_password_hash("password123"),
                        role=AdminRole.super_admin,
                    )
                    db.add(admin)
                    db.commit()
                    db.refresh(admin)
                    print("[Info] Default admin created: admin@example.com / password123")

                # 2. Sample Kiosk
                if db.query(Kiosk).count() == 0:
                    print("[Info] Seeding initial kiosk...")
                    kiosk = Kiosk(
                        kiosk_code="K-HYD-001",
                        source="HYD",
                        location_name="Hyderabad Main Bus Stand",
                        status=KioskStatus.active,
                    )
                    db.add(kiosk)
                    db.commit()

                # 3. Sample Routes & Buses
                if db.query(Route).count() == 0:
                    print("[Info] Seeding initial routes & buses...")
                    r1 = Route(
                        route_code="HYD-BLR",
                        source="HYD",
                        destination="BLR",
                        base_fare=1500.00,
                        created_by=admin.id if admin else None,
                    )
                    r2 = Route(
                        route_code="HYD-MUM",
                        source="HYD",
                        destination="MUM",
                        base_fare=2000.00,
                        created_by=admin.id if admin else None,
                    )
                    db.add_all([r1, r2])
                    db.commit()
                    db.refresh(r1)
                    db.refresh(r2)

                    if db.query(Bus).count() == 0:
                        b1 = Bus(
                            bus_number="AP09-AB-1234",
                            bus_type=BusTypeEnum.sleeper,
                            total_seats=30,
                        )
                        b2 = Bus(
                            bus_number="TS07-XY-9876",
                            bus_type=BusTypeEnum.ac,
                            total_seats=40,
                        )
                        db.add_all([b1, b2])
                        db.commit()
                        db.refresh(b1)
                        db.refresh(b2)

                        assign1 = RouteBusAssignment(
                            route_id=r1.id, bus_id=b1.id, departure_time=time(20, 0)
                        )
                        assign2 = RouteBusAssignment(
                            route_id=r2.id, bus_id=b2.id, departure_time=time(22, 30)
                        )
                        db.add_all([assign1, assign2])

                        today = date.today()
                        trip1 = Trip(
                            route_id=r1.id,
                            bus_id=b1.id,
                            travel_date=today,
                            departure_time=time(20, 0),
                            trip_duration="12h",
                            total_seats=30,
                            booked_seats=5,
                            held_seats=0,
                            status=TripStatus.scheduled,
                        )
                        trip2 = Trip(
                            route_id=r2.id,
                            bus_id=b2.id,
                            travel_date=today,
                            departure_time=time(22, 30),
                            trip_duration="14h 30m",
                            total_seats=40,
                            booked_seats=10,
                            held_seats=0,
                            status=TripStatus.scheduled,
                        )
                        db.add_all([trip1, trip2])
                        db.commit()
                        print("[Info] Seeded sample routes, buses, and trips for today!")

                print("[DB] Database connected and initialized successfully!")
                return
            finally:
                db.close()
        except Exception as e:
            print(f"[Warning] Database init attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time_module.sleep(retry_delay)
            else:
                print("[Error] All database connection attempts failed. Check DATABASE_URL in Railway Variables.")


@app.on_event("startup")
def startup_event():
    init_db_and_seed()


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Bus Booking Admin Dashboard API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "admin-api"}
