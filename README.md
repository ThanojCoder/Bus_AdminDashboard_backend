# 🚌 Bus Booking Admin Dashboard APIs

A robust, production-ready backend service built with **FastAPI** and **SQLAlchemy** for managing bus fleet operations, routes, kiosk terminals, scheduled trips, ticket orders, and financial/occupancy reporting.

---

## 🚀 Features

- **🔐 Admin Authentication & RBAC**: Secure JWT-based authentication supporting super admin and manager roles with bcrypt password hashing.
- **🛣️ Route Management**: Full CRUD operations for bus routes, departure schedules, base fare configurations, and terminal assignments.
- **🚍 Fleet & Bus Management**: Manage bus specifications (seater, sleeper, AC, non-AC), total seating capacity, active status, and real-time daily trip assignments.
- **🖥️ Kiosk & Terminal Monitoring**: Track and configure ticket booking kiosks, assign routes, monitor live status and heartbeats.
- **🎟️ Orders & Ticket Auditing**: Query, filter, paginate, and inspect ticket bookings, payment statuses, and handle order cancellations/refunds.
- **📊 Operational Analytics & Reports**: Live dashboards for revenue calculation, ticket counts, route-level occupancy, and payment breakdown across customizable date ranges.

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI)
- **Database ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Database**: PostgreSQL
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Authentication**: Python-JOSE (JWT) & Passlib (Bcrypt)

---

## 📁 Project Structure

```
adminAPIs/
├── .env.example          # Template for environment configuration
├── .gitignore            # Git ignore file for Python, secrets, and caches
├── requirements.txt      # Python dependencies
├── README.md             # Documentation and setup guide
├── main.py               # Application entrypoint and FastAPI router registration
├── database.py           # Database engine, session maker, and DB dependency
├── models.py             # SQLAlchemy ORM models (Routes, Buses, Trips, Orders, etc.)
├── schemas.py            # Pydantic request/response validation schemas
├── auth.py               # JWT tokens, password hashing, and auth dependencies
└── routers/              # API endpoints organized by domain
    ├── __init__.py
    ├── auth.py           # Admin login and token issuing
    ├── buses.py          # Bus inventory CRUD and live seat availability
    ├── kiosks.py         # Kiosk terminal CRUD and status management
    ├── reports.py        # Financial summaries and occupancy metrics
    ├── routes.py         # Routes and route-bus assignments
    └── tickets.py        # Order listing, search, pagination, and cancellations
```

---

## ⚙️ Getting Started

### Prerequisites

- **Python**: 3.10+
- **PostgreSQL**: Running instance with a database created (e.g., `busBooking_db`)

### 1. Clone & Navigate to Project

```bash
cd adminAPIs
```

### 2. Set Up Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the sample environment file and configure your credentials:

```bash
# Windows PowerShell
cp .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env`:

```ini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=busBooking_db
DB_USER=postgres
DB_PASSWORD=your_password_here

JWT_SECRET=your_jwt_secret_key_change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 5. Run the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The service will be accessible at `http://127.0.0.1:8000`.

---

## 📖 Interactive API Documentation

Once the server is running, explore and test the endpoints interactively:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/admin/auth/login` | Authenticate admin user & retrieve JWT token | ❌ |
| `GET` | `/api/admin/routes` | List all routes with assigned buses & terminals | ❌ |
| `POST` | `/api/admin/routes` | Create a new route | ✅ |
| `PUT` | `/api/admin/routes/{id}` | Update route details | ✅ |
| `DELETE` | `/api/admin/routes/{id}` | Deactivate/remove route | ✅ |
| `POST` | `/api/admin/routes/{id}/assign-bus` | Assign bus with departure time to route | ✅ |
| `GET` | `/api/admin/buses` | List all buses with seat availability for today | ❌ |
| `POST` | `/api/admin/buses` | Register a new bus | ✅ |
| `PUT` | `/api/admin/buses/{id}` | Update bus details | ✅ |
| `DELETE` | `/api/admin/buses/{id}` | Deactivate bus | ✅ |
| `GET` | `/api/admin/kiosks` | List all kiosks with terminal status and route | ❌ |
| `POST` | `/api/admin/kiosks` | Create new kiosk terminal | ✅ |
| `PUT` | `/api/admin/kiosks/{id}` | Update kiosk information | ✅ |
| `DELETE` | `/api/admin/kiosks/{id}` | Deactivate kiosk | ✅ |
| `GET` | `/api/admin/orders` | Paginated ticket orders with date & status filters | ✅ |
| `GET` | `/api/admin/orders/{id}` | View detailed order info | ✅ |
| `PUT` | `/api/admin/orders/{id}/cancel` | Cancel order, refund, and release seats | ✅ |
| `GET` | `/api/admin/reports/summary` | Today / range revenue and tickets summary | ✅ |
| `GET` | `/api/admin/reports/routes` | Route-by-route performance breakdown | ✅ |
| `GET` | `/api/admin/reports/buses` | Bus-level utilization and revenue | ✅ |
| `GET` | `/api/admin/reports/payments` | UPI vs Card payment volume breakdown | ✅ |
| `GET` | `/health` | Healthcheck endpoint | ❌ |

---

## 📤 Pushing to GitHub

To push this service to its own GitHub repository:

```bash
cd adminAPIs
git init
git add .
git commit -m "feat: Initial commit for Bus Booking Admin APIs"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```
