import os
import logging
from datetime import datetime, timedelta
from functools import wraps
import json
import bcrypt
import jwt
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, Numeric
from werkzeug.middleware.proxy_fix import ProxyFix

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

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

db = SQLAlchemy(app, model_class=Base)

# Models
class User(db.Model):
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

# Create tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if not exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = User(
            username='admin',
            email='admin@laemchabang-logistics.com',
            password_hash=password_hash,
            role='admin',
            full_name='시스템 관리자'
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Default admin user created")

# Auth helpers
def generate_token(user_id, role):
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        if not token:
            return redirect(url_for('login'))
        
        payload = verify_token(token)
        if not payload:
            session.clear()
            return redirect(url_for('login'))
        
        request.user = User.query.get(payload['user_id'])
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = session.get('token')
            if not token:
                return jsonify({'error': '인증이 필요합니다'}), 401
            
            payload = verify_token(token)
            if not payload:
                return jsonify({'error': '유효하지 않은 토큰입니다'}), 401
            
            user = User.query.get(payload['user_id'])
            if not user or user.role != required_role:
                return jsonify({'error': '권한이 없습니다'}), 403
            
            request.user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes
@app.route('/')
def index():
    token = session.get('token')
    if token:
        payload = verify_token(token)
        if payload:
            user = User.query.get(payload['user_id'])
            return render_template('index.html', user=user)
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            token = generate_token(user.id, user.role)
            session['token'] = token
            return jsonify({'success': True, 'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name
            }})
        else:
            return jsonify({'error': '잘못된 사용자명 또는 비밀번호입니다'}), 401
    
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '이미 존재하는 사용자명입니다'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': '이미 존재하는 이메일입니다'}), 400
    
    # Create new user
    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash,
        role=data['role'],
        full_name=data['full_name'],
        phone=data.get('phone', '')
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Create carrier or driver profile
    if data['role'] == 'carrier':
        carrier = Carrier(
            user_id=user.id,
            company_name=data['company_name'],
            business_license=data.get('business_license', ''),
            contact_person=data['full_name'],
            address=data.get('address', '')
        )
        db.session.add(carrier)
    elif data['role'] == 'driver':
        driver = Driver(
            user_id=user.id,
            carrier_id=data['carrier_id'],
            license_number=data['license_number'],
            vehicle_type=data.get('vehicle_type', ''),
            vehicle_number=data.get('vehicle_number', '')
        )
        db.session.add(driver)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '계정이 성공적으로 생성되었습니다'})

# API Routes
@app.route('/api/dashboard')
@login_required
def dashboard():
    user = request.user
    
    if user.role == 'admin':
        # Admin dashboard stats
        total_users = User.query.count()
        active_tolerances = Tolerance.query.filter_by(status='available').count()
        pending_requests = DeliveryRequest.query.filter_by(status='pending').count()
        completed_matches = Match.query.filter_by(status='completed').count()
        
        return jsonify({
            'total_users': total_users,
            'active_tolerances': active_tolerances,
            'pending_requests': pending_requests,
            'completed_matches': completed_matches
        })
    
    elif user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        if not carrier:
            return jsonify({'error': '운송사 정보를 찾을 수 없습니다'}), 404
        
        # Carrier dashboard stats
        my_tolerances = Tolerance.query.filter_by(carrier_id=carrier.id).count()
        my_requests = DeliveryRequest.query.filter_by(carrier_id=carrier.id).count()
        my_matches = Match.query.join(Tolerance).filter(Tolerance.carrier_id == carrier.id).count()
        
        return jsonify({
            'my_tolerances': my_tolerances,
            'my_requests': my_requests,
            'my_matches': my_matches
        })
    
    elif user.role == 'driver':
        driver = Driver.query.filter_by(user_id=user.id).first()
        if not driver:
            return jsonify({'error': '기사 정보를 찾을 수 없습니다'}), 404
        
        # Driver dashboard stats
        assigned_matches = Match.query.filter_by(driver_id=driver.id, status='in_progress').count()
        completed_matches = Match.query.filter_by(driver_id=driver.id, status='completed').count()
        
        return jsonify({
            'assigned_matches': assigned_matches,
            'completed_matches': completed_matches,
            'current_status': driver.status
        })

@app.route('/api/tolerances', methods=['GET', 'POST'])
@login_required
def tolerances():
    user = request.user
    
    if request.method == 'POST':
        if user.role != 'carrier':
            return jsonify({'error': '운송사만 여유 운송을 등록할 수 있습니다'}), 403
        
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        if not carrier:
            return jsonify({'error': '운송사 정보를 찾을 수 없습니다'}), 404
        
        data = request.get_json()
        tolerance = Tolerance(
            carrier_id=carrier.id,
            origin=data['origin'],
            destination=data['destination'],
            departure_time=datetime.fromisoformat(data['departure_time']),
            arrival_time=datetime.fromisoformat(data['arrival_time']) if data.get('arrival_time') else None,
            container_type=data['container_type'],
            container_count=data.get('container_count', 1),
            is_empty_run=data.get('is_empty_run', False),
            price=data.get('price', 0)
        )
        
        db.session.add(tolerance)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '여유 운송이 등록되었습니다'})
    
    # GET request
    if user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        tolerances = Tolerance.query.filter_by(carrier_id=carrier.id).all()
    else:
        tolerances = Tolerance.query.filter_by(status='available').all()
    
    result = []
    for tolerance in tolerances:
        result.append({
            'id': tolerance.id,
            'carrier_name': tolerance.carrier.company_name,
            'origin': tolerance.origin,
            'destination': tolerance.destination,
            'departure_time': tolerance.departure_time.isoformat(),
            'arrival_time': tolerance.arrival_time.isoformat() if tolerance.arrival_time else None,
            'container_type': tolerance.container_type,
            'container_count': tolerance.container_count,
            'is_empty_run': tolerance.is_empty_run,
            'price': float(tolerance.price) if tolerance.price else 0,
            'status': tolerance.status,
            'created_at': tolerance.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/delivery-requests', methods=['GET', 'POST'])
@login_required
def delivery_requests():
    user = request.user
    
    if request.method == 'POST':
        if user.role != 'carrier':
            return jsonify({'error': '운송사만 운송 요청을 등록할 수 있습니다'}), 403
        
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        if not carrier:
            return jsonify({'error': '운송사 정보를 찾을 수 없습니다'}), 404
        
        data = request.get_json()
        request_obj = DeliveryRequest(
            carrier_id=carrier.id,
            origin=data['origin'],
            destination=data['destination'],
            pickup_time=datetime.fromisoformat(data['pickup_time']),
            delivery_time=datetime.fromisoformat(data['delivery_time']) if data.get('delivery_time') else None,
            container_type=data['container_type'],
            container_count=data.get('container_count', 1),
            cargo_details_json=json.dumps(data.get('cargo_details', {})),
            budget=data.get('budget', 0)
        )
        
        db.session.add(request_obj)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송 요청이 등록되었습니다'})
    
    # GET request
    if user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        requests = DeliveryRequest.query.filter_by(carrier_id=carrier.id).all()
    else:
        requests = DeliveryRequest.query.filter_by(status='pending').all()
    
    result = []
    for req in requests:
        cargo_details = json.loads(req.cargo_details_json) if req.cargo_details_json else {}
        result.append({
            'id': req.id,
            'carrier_name': req.carrier.company_name,
            'origin': req.origin,
            'destination': req.destination,
            'pickup_time': req.pickup_time.isoformat(),
            'delivery_time': req.delivery_time.isoformat() if req.delivery_time else None,
            'container_type': req.container_type,
            'container_count': req.container_count,
            'cargo_details': cargo_details,
            'budget': float(req.budget) if req.budget else 0,
            'status': req.status,
            'created_at': req.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/matches', methods=['GET', 'POST'])
@login_required
def matches():
    user = request.user
    
    if request.method == 'POST':
        # Create a match (for admin or system)
        data = request.get_json()
        match = Match(
            tolerance_id=data['tolerance_id'],
            request_id=data['request_id'],
            driver_id=data.get('driver_id')
        )
        
        db.session.add(match)
        
        # Update status
        tolerance = Tolerance.query.get(data['tolerance_id'])
        request_obj = DeliveryRequest.query.get(data['request_id'])
        
        if tolerance:
            tolerance.status = 'matched'
        if request_obj:
            request_obj.status = 'matched'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '매칭이 생성되었습니다'})
    
    # GET request
    if user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        matches = Match.query.join(Tolerance).filter(Tolerance.carrier_id == carrier.id).all()
    elif user.role == 'driver':
        driver = Driver.query.filter_by(user_id=user.id).first()
        matches = Match.query.filter_by(driver_id=driver.id).all()
    else:
        matches = Match.query.all()
    
    result = []
    for match in matches:
        result.append({
            'id': match.id,
            'tolerance': {
                'origin': match.tolerance.origin,
                'destination': match.tolerance.destination,
                'departure_time': match.tolerance.departure_time.isoformat(),
                'container_type': match.tolerance.container_type
            },
            'request': {
                'origin': match.request.origin,
                'destination': match.request.destination,
                'pickup_time': match.request.pickup_time.isoformat(),
                'container_type': match.request.container_type
            },
            'driver': {
                'name': match.driver.user.full_name if match.driver else None,
                'vehicle_number': match.driver.vehicle_number if match.driver else None
            },
            'status': match.status,
            'matched_at': match.matched_at.isoformat(),
            'accepted_at': match.accepted_at.isoformat() if match.accepted_at else None,
            'completed_at': match.completed_at.isoformat() if match.completed_at else None
        })
    
    return jsonify(result)

@app.route('/api/matches/<int:match_id>/accept', methods=['POST'])
@login_required
def accept_match(match_id):
    user = request.user
    match = Match.query.get_or_404(match_id)
    
    if user.role == 'carrier':
        # Carrier accepting the match
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        if match.tolerance.carrier_id != carrier.id and match.request.carrier_id != carrier.id:
            return jsonify({'error': '권한이 없습니다'}), 403
        
        match.status = 'accepted'
        match.accepted_at = datetime.utcnow()
        
    elif user.role == 'driver':
        # Driver accepting the assignment
        driver = Driver.query.filter_by(user_id=user.id).first()
        if match.driver_id != driver.id:
            return jsonify({'error': '권한이 없습니다'}), 403
        
        match.status = 'in_progress'
        match.request.status = 'in_transit'
        
    db.session.commit()
    
    return jsonify({'success': True, 'message': '매칭이 수락되었습니다'})

@app.route('/api/matches/<int:match_id>/reject', methods=['POST'])
@login_required
def reject_match(match_id):
    user = request.user
    match = Match.query.get_or_404(match_id)
    data = request.get_json()
    
    if user.role != 'carrier':
        return jsonify({'error': '운송사만 매칭을 거절할 수 있습니다'}), 403
    
    carrier = Carrier.query.filter_by(user_id=user.id).first()
    if match.tolerance.carrier_id != carrier.id and match.request.carrier_id != carrier.id:
        return jsonify({'error': '권한이 없습니다'}), 403
    
    match.status = 'rejected'
    match.rejection_reason = data.get('reason', '')
    
    # Reset tolerance and request status
    match.tolerance.status = 'available'
    match.request.status = 'pending'
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '매칭이 거절되었습니다'})

@app.route('/api/location', methods=['POST'])
@login_required
def update_location():
    user = request.user
    
    if user.role != 'driver':
        return jsonify({'error': '기사만 위치를 업데이트할 수 있습니다'}), 403
    
    driver = Driver.query.filter_by(user_id=user.id).first()
    if not driver:
        return jsonify({'error': '기사 정보를 찾을 수 없습니다'}), 404
    
    data = request.get_json()
    
    # Update driver's current location
    driver.current_location = json.dumps({
        'latitude': data['latitude'],
        'longitude': data['longitude']
    })
    
    # If there's an active match, save to location path
    active_match = Match.query.filter_by(driver_id=driver.id, status='in_progress').first()
    if active_match:
        location_path = LocationPath(
            match_id=active_match.id,
            driver_id=driver.id,
            latitude=data['latitude'],
            longitude=data['longitude']
        )
        db.session.add(location_path)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '위치가 업데이트되었습니다'})

@app.route('/api/location/<int:match_id>')
@login_required
def get_location_path(match_id):
    match = Match.query.get_or_404(match_id)
    
    locations = LocationPath.query.filter_by(match_id=match_id).order_by(LocationPath.timestamp.desc()).limit(100).all()
    
    result = []
    for location in locations:
        result.append({
            'latitude': location.latitude,
            'longitude': location.longitude,
            'timestamp': location.timestamp.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/carriers')
@login_required
def get_carriers():
    carriers = Carrier.query.filter_by(status='active').all()
    
    result = []
    for carrier in carriers:
        result.append({
            'id': carrier.id,
            'company_name': carrier.company_name,
            'contact_person': carrier.contact_person,
            'created_at': carrier.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/auto-match', methods=['POST'])
@role_required('admin')
def auto_match():
    """Basic auto-matching algorithm"""
    
    # Get available tolerances and pending requests
    tolerances = Tolerance.query.filter_by(status='available').all()
    requests = DeliveryRequest.query.filter_by(status='pending').all()
    
    matches_created = 0
    
    for tolerance in tolerances:
        for request in requests:
            # Simple matching criteria
            if (tolerance.origin == request.origin and 
                tolerance.destination == request.destination and
                tolerance.container_type == request.container_type and
                tolerance.departure_time <= request.pickup_time and
                tolerance.container_count >= request.container_count):
                
                # Create match
                match = Match(
                    tolerance_id=tolerance.id,
                    request_id=request.id
                )
                
                db.session.add(match)
                
                # Update statuses
                tolerance.status = 'matched'
                request.status = 'matched'
                
                matches_created += 1
                break
    
    db.session.commit()
    
    return jsonify({'success': True, 'matches_created': matches_created})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
