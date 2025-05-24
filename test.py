from sqlalchemy.orm import sessionmaker
from main import engine, Contact, SessionLocal

db = SessionLocal()
test_contact = Contact(contact_id="test-001", phone_number="0928156792")
db.add(test_contact)
db.commit()
db.close()