from database import SessionLocal
from sqlalchemy import text
import sys

session = SessionLocal()
try:
    session.execute(text("ALTER TYPE bookingstatusenum ADD VALUE 'pending'"))
    session.commit()
    print('Enum updated')
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
