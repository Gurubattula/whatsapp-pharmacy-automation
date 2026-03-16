from database import SessionLocal, engine, Base
import models  # This is crucial! It tells SQLAlchemy which tables to create
from models import Medicine

def seed_data():
    # 1. Physically create the tables in MySQL if they don't exist
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 2. Your medicine list
    medicines = [
        Medicine(name="Paracetamol 500mg", price=30.0, stock_quantity=100, is_prescription_required=False),
        Medicine(name="Dolo 650", price=45.0, stock_quantity=50, is_prescription_required=False),
        Medicine(name="Amoxicillin 500mg", price=120.0, stock_quantity=20, is_prescription_required=True),
        Medicine(name="Cetirizine 10mg", price=15.0, stock_quantity=0, is_prescription_required=False),
        Medicine(name="Azithromycin 500mg", price=95.0, stock_quantity=15, is_prescription_required=True)
    ]

    try:
        print("Seeding medicines...")
        for med in medicines:
            exists = db.query(Medicine).filter(Medicine.name == med.name).first()
            if not exists:
                db.add(med)
        db.commit()
        print("✅ Success: Medicine inventory created and seeded!")
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()