from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from geopy.distance import geodesic

DATABASE_URL = "sqlite:///./addresses.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    street = Column(String, index=True)
    city = Column(String, index=True)
    state = Column(String, index=True)
    country = Column(String, index=True)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)

Base.metadata.create_all(bind=engine)

class AddressCreate(BaseModel):
    street: str
    city: str
    state: str
    country: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    @field_validator('latitude', 'longitude')
    def check_coordinates(cls, value, info):
        if info.field_name == 'latitude' and (value < -90 or value > 90):
            raise ValueError('Latitude must be between -90 and 90.')
        if info.field_name == 'longitude' and (value < -180 or value > 180):
            raise ValueError('Longitude must be between -180 and 180.')
        return value

class AddressUpdate(BaseModel):
    street: str = None
    city: str = None
    state: str = None
    country: str = None
    latitude: float = None
    longitude: float = None

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/addresses/", response_model=AddressCreate)
def create_address(address: AddressCreate, db: Session = Depends(get_db)):
    db_address = Address(**address.dict())
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@app.put("/addresses/{address_id}", response_model=AddressCreate)
def update_address(address_id: int, address: AddressUpdate, db: Session = Depends(get_db)):
    db_address = db.query(Address).filter(Address.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    for var, value in vars(address).items():
        if value is not None:
            setattr(db_address, var, value)
    db.commit()
    db.refresh(db_address)
    return db_address

@app.delete("/addresses/{address_id}")
def delete_address(address_id: int, db: Session = Depends(get_db)):
    db_address = db.query(Address).filter(Address.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    db.delete(db_address)
    db.commit()
    return {"detail": "Address deleted"}

@app.get("/addresses/")
def read_addresses_within_distance(lat: float, lon: float, distance_km: float, db: Session = Depends(get_db)):
    addresses = db.query(Address).all()
    result = []
    for address in addresses:
        addr_coords = (address.latitude, address.longitude)
        center_coords = (lat, lon)
        distance = geodesic(center_coords, addr_coords).km
        if distance <= distance_km:
            result.append(address)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
