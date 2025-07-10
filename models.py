from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, carrier, driver
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    carrier = db.relationship('Carrier', backref='user', uselist=False)
    driver = db.relationship('Driver', backref='user', uselist=False)

class Carrier(db.Model):
    __tablename__ = 'carriers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    business_license = db.Column(db.String(50))
    contact_person = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    drivers = db.relationship('Driver', backref='carrier', lazy=True)
    tolerances = db.relationship('Tolerance', backref='carrier', lazy=True)
    delivery_requests = db.relationship('DeliveryRequest', backref='carrier', lazy=True)

class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    license_number = db.Column(db.String(50), nullable=False)
    vehicle_type = db.Column(db.String(50))
    vehicle_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='available')  # available, busy, offline
    current_location_lat = db.Column(db.Float)
    current_location_lng = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Tolerance(db.Model):
    __tablename__ = 'tolerances'
    
    id = db.Column(db.Integer, primary_key=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    container_type = db.Column(db.String(20), nullable=False)  # 20ft, 40ft, etc.
    container_count = db.Column(db.Integer, nullable=False)
    is_empty_run = db.Column(db.Boolean, default=False)
    price = db.Column(db.Integer)  # Price in KRW
    status = db.Column(db.String(20), default='available')  # available, matched, completed, cancelled
    special_requirements = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches = db.relationship('Match', backref='tolerance', lazy=True)

class DeliveryRequest(db.Model):
    __tablename__ = 'delivery_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    pickup_time = db.Column(db.DateTime, nullable=False)
    delivery_time = db.Column(db.DateTime, nullable=False)
    container_type = db.Column(db.String(20), nullable=False)
    container_count = db.Column(db.Integer, nullable=False)
    cargo_details_json = db.Column(db.Text)  # JSON string for cargo details
    budget = db.Column(db.Integer)  # Budget in KRW
    status = db.Column(db.String(20), default='pending')  # pending, matched, completed, cancelled
    special_requirements = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches = db.relationship('Match', backref='delivery_request', lazy=True)

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    tolerance_id = db.Column(db.Integer, db.ForeignKey('tolerances.id'), nullable=False)
    delivery_request_id = db.Column(db.Integer, db.ForeignKey('delivery_requests.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, completed, cancelled
    price = db.Column(db.Integer)  # Final agreed price
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    driver = db.relationship('Driver', backref='matches')
    location_paths = db.relationship('LocationPath', backref='match', lazy=True)

class LocationPath(db.Model):
    __tablename__ = 'location_paths'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # pickup, in_transit, delivered
    notes = db.Column(db.Text) 