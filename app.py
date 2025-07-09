import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "laem-chabang-logistics-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/logistics_db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# No need to call db.init_app(app) here, it's already done in the constructor.
db = SQLAlchemy(app, model_class=Base)

# Create tables
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
    
    # Initialize sample data
    from models import User, Carrier, Driver, Tolerance, DeliveryRequest, Match, LocationPath
    import bcrypt
    from datetime import datetime, timedelta
    
    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=admin_password,
            role='admin',
            full_name='시스템 관리자',
            phone='010-0000-0000'
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Default admin user created")
    
    # Create sample data if not exists
    if not Carrier.query.first():
        # Sample carriers
        carrier1_password = bcrypt.hashpw('carrier1'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        carrier1_user = User(
            username='carrier1',
            email='carrier1@example.com',
            password_hash=carrier1_password,
            role='carrier',
            full_name='운송사1 담당자',
            phone='010-1111-1111'
        )
        db.session.add(carrier1_user)
        db.session.commit()
        
        carrier1 = Carrier(
            user_id=carrier1_user.id,
            company_name='한국해운물류',
            business_license='123-45-67890',
            contact_person='운송사1 담당자',
            address='부산시 해운대구 센텀중앙로 100'
        )
        db.session.add(carrier1)
        
        carrier2_password = bcrypt.hashpw('carrier2'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        carrier2_user = User(
            username='carrier2',
            email='carrier2@example.com',
            password_hash=carrier2_password,
            role='carrier',
            full_name='운송사2 담당자',
            phone='010-2222-2222'
        )
        db.session.add(carrier2_user)
        db.session.commit()
        
        carrier2 = Carrier(
            user_id=carrier2_user.id,
            company_name='태평양운송',
            business_license='234-56-78901',
            contact_person='운송사2 담당자',
            address='인천시 연수구 컨벤시아대로 300'
        )
        db.session.add(carrier2)
        db.session.commit()
        
        # Sample drivers
        driver1_password = bcrypt.hashpw('driver1'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        driver1_user = User(
            username='driver1',
            email='driver1@example.com',
            password_hash=driver1_password,
            role='driver',
            full_name='박민수',
            phone='010-3333-3333'
        )
        db.session.add(driver1_user)
        db.session.commit()
        
        driver1 = Driver(
            user_id=driver1_user.id,
            carrier_id=carrier1.id,
            license_number='12-34-567890',
            vehicle_type='트레일러',
            vehicle_number='부산12가3456',
            status='available'
        )
        db.session.add(driver1)
        
        driver2_password = bcrypt.hashpw('driver2'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        driver2_user = User(
            username='driver2',
            email='driver2@example.com',
            password_hash=driver2_password,
            role='driver',
            full_name='정수현',
            phone='010-4444-4444'
        )
        db.session.add(driver2_user)
        db.session.commit()
        
        driver2 = Driver(
            user_id=driver2_user.id,
            carrier_id=carrier2.id,
            license_number='23-45-678901',
            vehicle_type='5톤 트럭',
            vehicle_number='인천34나5678',
            status='available'
        )
        db.session.add(driver2)
        db.session.commit()
        
        # Sample tolerances
        tolerance1 = Tolerance(
            carrier_id=carrier1.id,
            origin='람차방 항구',
            destination='부산 신항',
            departure_time=datetime.now() + timedelta(hours=2),
            arrival_time=datetime.now() + timedelta(hours=8),
            container_type='40ft',
            container_count=2,
            is_empty_run=False,
            price=500000,
            status='available'
        )
        db.session.add(tolerance1)
        
        tolerance2 = Tolerance(
            carrier_id=carrier2.id,
            origin='람차방 항구',
            destination='인천 항구',
            departure_time=datetime.now() + timedelta(hours=6),
            arrival_time=datetime.now() + timedelta(hours=14),
            container_type='20ft',
            container_count=3,
            is_empty_run=True,
            price=300000,
            status='available'
        )
        db.session.add(tolerance2)
        
        # Sample delivery requests
        request1 = DeliveryRequest(
            carrier_id=carrier1.id,
            origin='람차방 항구',
            destination='부산 신항',
            pickup_time=datetime.now() + timedelta(hours=3),
            delivery_time=datetime.now() + timedelta(hours=9),
            container_type='40ft',
            container_count=1,
            cargo_details_json='{"type": "전자제품", "weight": "12톤", "special_requirements": "온도관리"}',
            budget=450000,
            status='pending'
        )
        db.session.add(request1)
        
        request2 = DeliveryRequest(
            carrier_id=carrier2.id,
            origin='람차방 항구',
            destination='인천 항구',
            pickup_time=datetime.now() + timedelta(hours=8),
            delivery_time=datetime.now() + timedelta(hours=16),
            container_type='20ft',
            container_count=2,
            cargo_details_json='{"type": "의류", "weight": "5톤", "special_requirements": "습도관리"}',
            budget=250000,
            status='pending'
        )
        db.session.add(request2)
        
        db.session.commit()
        logging.info("Sample data created")
    
    logging.info("Database initialization completed")