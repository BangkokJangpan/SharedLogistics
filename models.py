from datetime import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy import Numeric

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, carrier, driver
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Carrier(db.Model):
    __tablename__ = 'carriers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    business_license = db.Column(db.String(50))
    contact_person = db.Column(db.String(100))
    address = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='carrier_profile')

class Driver(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    license_number = db.Column(db.String(50), nullable=False)
    vehicle_type = db.Column(db.String(50))
    vehicle_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='available')
    current_location = db.Column(db.Text)  # JSON string for lat/lng
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='driver_profile')
    carrier = db.relationship('Carrier', backref='drivers')

class Tolerance(db.Model):
    __tablename__ = 'tolerances'
    id = db.Column(db.Integer, primary_key=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime)
    container_type = db.Column(db.String(50), nullable=False)
    container_count = db.Column(db.Integer, default=1)
    is_empty_run = db.Column(db.Boolean, default=False)
    price = db.Column(Numeric(10, 2))
    status = db.Column(db.String(20), default='available')  # available, matched, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    carrier = db.relationship('Carrier', backref='tolerances')

class DeliveryRequest(db.Model):
    __tablename__ = 'delivery_requests'
    id = db.Column(db.Integer, primary_key=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    pickup_time = db.Column(db.DateTime, nullable=False)
    delivery_time = db.Column(db.DateTime)
    container_type = db.Column(db.String(50), nullable=False)
    container_count = db.Column(db.Integer, default=1)
    cargo_details_json = db.Column(db.Text)  # JSON string for cargo details
    budget = db.Column(Numeric(10, 2))
    status = db.Column(db.String(20), default='pending')  # pending, matched, in_transit, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    carrier = db.relationship('Carrier', backref='delivery_requests')

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    tolerance_id = db.Column(db.Integer, db.ForeignKey('tolerances.id'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('delivery_requests.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'))
    status = db.Column(db.String(20), default='proposed')  # proposed, accepted, rejected, in_progress, completed
    matched_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    
    tolerance = db.relationship('Tolerance', backref='matches')
    request = db.relationship('DeliveryRequest', backref='matches')
    driver = db.relationship('Driver', backref='assigned_matches')

class LocationPath(db.Model):
    __tablename__ = 'location_paths'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    match = db.relationship('Match', backref='location_paths')
    driver = db.relationship('Driver', backref='location_paths')