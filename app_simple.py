import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timedelta
from functools import wraps
import json
import bcrypt
import jwt
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

Base = declarative_base()

# Initialize Flask app
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "laem-chabang-logistics-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'shared_logistics.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {'pool_pre_ping': True, "pool_recycle": 300}
db = SQLAlchemy(app, model_class=Base)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize SocketIO for real-time tracking
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active connections
active_connections = {}

# Models
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
    vehicles = db.relationship('Vehicle', backref='carrier', lazy=True)

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

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'), nullable=False)
    vehicle_number = db.Column(db.String(30), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, in_use, maintenance, inactive
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

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

@app.route('/tracking')
def tracking():
    return render_template('tracking.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': '요청 데이터가 없습니다.'}), 400
            username = data.get('username')
            password = data.get('password')
            if not username or not password:
                return jsonify({'error': '사용자명과 비밀번호를 입력하세요.'}), 400
            user = User.query.filter_by(username=username).first()
            if not user:
                return jsonify({'error': '존재하지 않는 사용자명입니다.'}), 401
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    token = generate_token(user.id, user.role)
                    session['token'] = token
                    return jsonify({'success': True, 'user': {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role,
                        'full_name': user.full_name
                    }})
                else:
                    return jsonify({'error': '잘못된 비밀번호입니다.'}), 401
            except Exception as e:
                return jsonify({'error': '비밀번호 검증 중 오류가 발생했습니다.'}), 500
        except Exception as e:
            return jsonify({'error': f'로그인 처리 중 서버 오류: {str(e)}'}), 500
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
        my_matches = Match.query.filter_by(driver_id=driver.id).count()
        active_matches = Match.query.filter_by(driver_id=driver.id, status='accepted').count()
        
        return jsonify({
            'my_matches': my_matches,
            'active_matches': active_matches
        })

@app.route('/api/tolerances', methods=['GET', 'POST'])
@login_required
def tolerances():
    if request.method == 'POST':
        data = request.get_json()
        carrier = Carrier.query.filter_by(user_id=request.user.id).first()
        
        if not carrier:
            return jsonify({'error': '운송사 정보를 찾을 수 없습니다'}), 404
        
        tolerance = Tolerance(
            carrier_id=carrier.id,
            origin=data['origin'],
            destination=data['destination'],
            departure_time=datetime.fromisoformat(data['departure_time']),
            arrival_time=datetime.fromisoformat(data['arrival_time']),
            container_type=data['container_type'],
            container_count=data['container_count'],
            is_empty_run=data.get('is_empty_run', False),
            price=data.get('price'),
            special_requirements=data.get('special_requirements')
        )
        
        db.session.add(tolerance)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '여유운송이 등록되었습니다'})
    
    # GET request
    if request.user.role == 'admin':
        tolerances = Tolerance.query.all()
    elif request.user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=request.user.id).first()
        tolerances = Tolerance.query.filter_by(carrier_id=carrier.id).all()
    else:
        tolerances = Tolerance.query.filter_by(status='available').all()
    
    return jsonify([{
        'id': t.id,
        'origin': t.origin,
        'destination': t.destination,
        'departure_time': t.departure_time.isoformat(),
        'arrival_time': t.arrival_time.isoformat(),
        'container_type': t.container_type,
        'container_count': t.container_count,
        'is_empty_run': t.is_empty_run,
        'price': t.price,
        'status': t.status,
        'carrier_name': t.carrier.company_name,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None
    } for t in tolerances])

@app.route('/api/delivery-requests', methods=['GET', 'POST'])
@login_required
def delivery_requests():
    if request.method == 'POST':
        data = request.get_json()
        carrier = Carrier.query.filter_by(user_id=request.user.id).first()
        
        if not carrier:
            return jsonify({'error': '운송사 정보를 찾을 수 없습니다'}), 404
        
        request_obj = DeliveryRequest(
            carrier_id=carrier.id,
            origin=data['origin'],
            destination=data['destination'],
            pickup_time=datetime.fromisoformat(data['pickup_time']),
            delivery_time=datetime.fromisoformat(data['delivery_time']),
            container_type=data['container_type'],
            container_count=data['container_count'],
            cargo_details_json=json.dumps(data.get('cargo_details', {})),
            budget=data.get('budget'),
            special_requirements=data.get('special_requirements')
        )
        
        db.session.add(request_obj)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '배송요청이 등록되었습니다'})
    
    # GET request
    if request.user.role == 'admin':
        requests = DeliveryRequest.query.all()
    elif request.user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=request.user.id).first()
        requests = DeliveryRequest.query.filter_by(carrier_id=carrier.id).all()
    else:
        requests = DeliveryRequest.query.filter_by(status='pending').all()
    
    return jsonify([{
        'id': r.id,
        'origin': r.origin,
        'destination': r.destination,
        'pickup_time': r.pickup_time.isoformat(),
        'delivery_time': r.delivery_time.isoformat(),
        'container_type': r.container_type,
        'container_count': r.container_count,
        'cargo_details': json.loads(r.cargo_details_json) if r.cargo_details_json else {},
        'budget': r.budget,
        'status': r.status,
        'carrier_name': r.carrier.company_name
    } for r in requests])

@app.route('/api/matches', methods=['GET'])
@login_required
def matches():
    if request.user.role == 'admin':
        matches = Match.query.all()
    elif request.user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=request.user.id).first()
        matches = Match.query.join(Tolerance).filter(Tolerance.carrier_id == carrier.id).all()
    else:
        driver = Driver.query.filter_by(user_id=request.user.id).first()
        matches = Match.query.filter_by(driver_id=driver.id).all()
    
    return jsonify([{
        'id': m.id,
        'tolerance': {
            'origin': m.tolerance.origin,
            'destination': m.tolerance.destination,
            'departure_time': m.tolerance.departure_time.isoformat(),
            'arrival_time': m.tolerance.arrival_time.isoformat(),
            'container_type': m.tolerance.container_type,
            'container_count': m.tolerance.container_count,
            'price': m.tolerance.price
        },
        'delivery_request': {
            'origin': m.delivery_request.origin,
            'destination': m.delivery_request.destination,
            'pickup_time': m.delivery_request.pickup_time.isoformat(),
            'delivery_time': m.delivery_request.delivery_time.isoformat(),
            'container_type': m.delivery_request.container_type,
            'container_count': m.delivery_request.container_count,
            'budget': m.delivery_request.budget
        },
        'status': m.status,
        'price': m.price,
        'created_at': m.created_at.isoformat()
    } for m in matches])

@app.route('/api/matches/<int:match_id>/accept', methods=['POST'])
@login_required
def accept_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    if request.user.role == 'driver':
        driver = Driver.query.filter_by(user_id=request.user.id).first()
        if match.driver_id != driver.id:
            return jsonify({'error': '권한이 없습니다'}), 403
    
    match.status = 'accepted'
    match.tolerance.status = 'matched'
    match.delivery_request.status = 'matched'
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '매칭이 수락되었습니다'})

@app.route('/api/matches/<int:match_id>/reject', methods=['POST'])
@login_required
def reject_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    if request.user.role == 'driver':
        driver = Driver.query.filter_by(user_id=request.user.id).first()
        if match.driver_id != driver.id:
            return jsonify({'error': '권한이 없습니다'}), 403
    
    match.status = 'rejected'
    match.tolerance.status = 'available'
    match.delivery_request.status = 'pending'
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '매칭이 거절되었습니다'})

@app.route('/api/location/update', methods=['POST'])
@login_required
def update_location():
    if request.user.role != 'driver':
        return jsonify({'error': '기사만 위치를 업데이트할 수 있습니다'}), 403
    
    data = request.get_json()
    driver = Driver.query.filter_by(user_id=request.user.id).first()
    
    if not driver:
        return jsonify({'error': '기사 정보를 찾을 수 없습니다'}), 404
    
    driver.current_location_lat = data['latitude']
    driver.current_location_lng = data['longitude']
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '위치가 업데이트되었습니다'})

@app.route('/api/location/path/<int:match_id>')
@login_required
def get_location_path(match_id):
    match = Match.query.get_or_404(match_id)
    paths = LocationPath.query.filter_by(match_id=match_id).order_by(LocationPath.timestamp).all()
    
    return jsonify([{
        'latitude': p.latitude,
        'longitude': p.longitude,
        'timestamp': p.timestamp.isoformat(),
        'status': p.status,
        'notes': p.notes
    } for p in paths])

@app.route('/api/carriers')
@login_required
def get_carriers():
    carriers = Carrier.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': c.id,
        'company_name': c.company_name,
        'contact_person': c.contact_person,
        'phone': c.phone,
        'email': c.email
    } for c in carriers])

@app.route('/api/auto-match', methods=['POST'])
@login_required
def auto_match():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '요청 데이터가 없습니다'}), 400
        
        tolerance_id = data.get('tolerance_id')
        delivery_request_id = data.get('delivery_request_id')
        
        if not tolerance_id or not delivery_request_id:
            return jsonify({'error': 'tolerance_id와 delivery_request_id가 필요합니다'}), 400
        
        tolerance = Tolerance.query.get_or_404(tolerance_id)
        delivery_request = DeliveryRequest.query.get_or_404(delivery_request_id)
        
        # Check if tolerance and delivery request are available
        if tolerance.status != 'available':
            return jsonify({'error': '해당 여유운송은 이미 매칭되었습니다'}), 400
        
        if delivery_request.status != 'pending':
            return jsonify({'error': '해당 배송요청은 이미 처리되었습니다'}), 400
        
        # Find available driver
        driver = Driver.query.filter_by(status='available').first()
        
        if not driver:
            return jsonify({'error': '사용 가능한 기사가 없습니다'}), 404
        
        # Check if match already exists
        existing_match = Match.query.filter_by(
            tolerance_id=tolerance_id,
            delivery_request_id=delivery_request_id
        ).first()
        
        if existing_match:
            return jsonify({'error': '이미 매칭이 존재합니다'}), 400
        
        # Create match
        match = Match(
            tolerance_id=tolerance_id,
            delivery_request_id=delivery_request_id,
            driver_id=driver.id,
            status='pending'
        )
        
        db.session.add(match)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '자동 매칭이 완료되었습니다'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'매칭 중 오류가 발생했습니다: {str(e)}'}), 500

# Admin routes
@app.route('/api/admin/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_users():
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'full_name': u.full_name,
            'phone': u.phone,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat()
        } for u in users])
    
    elif request.method == 'POST':
        data = request.get_json()
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
        
        return jsonify({'success': True, 'message': '사용자가 생성되었습니다'})
    
    elif request.method == 'PUT':
        data = request.get_json()
        user = User.query.get_or_404(data['id'])
        
        user.username = data['username']
        user.email = data['email']
        user.role = data['role']
        user.full_name = data['full_name']
        user.phone = data.get('phone', '')
        user.is_active = data.get('is_active', True)
        
        if data.get('password'):
            password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.password_hash = password_hash
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '사용자 정보가 업데이트되었습니다'})
    
    elif request.method == 'DELETE':
        user_id = request.args.get('id')
        user = User.query.get_or_404(user_id)
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '사용자가 삭제되었습니다'})

@app.route('/api/admin/carriers', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_carriers():
    if request.method == 'GET':
        carriers = Carrier.query.all()
        return jsonify([{
            'id': c.id,
            'user_id': c.user_id,
            'company_name': c.company_name,
            'business_license': c.business_license,
            'contact_person': c.contact_person,
            'address': c.address,
            'phone': c.phone,
            'email': c.email,
            'is_active': c.is_active,
            'created_at': c.created_at.isoformat()
        } for c in carriers])
    
    elif request.method == 'POST':
        data = request.get_json()
        carrier = Carrier(
            user_id=data['user_id'],
            company_name=data['company_name'],
            business_license=data.get('business_license', ''),
            contact_person=data['contact_person'],
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', '')
        )
        
        db.session.add(carrier)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송사가 생성되었습니다'})
    
    elif request.method == 'PUT':
        data = request.get_json()
        carrier = Carrier.query.get_or_404(data['id'])
        
        carrier.company_name = data['company_name']
        carrier.business_license = data.get('business_license', '')
        carrier.contact_person = data['contact_person']
        carrier.address = data.get('address', '')
        carrier.phone = data.get('phone', '')
        carrier.email = data.get('email', '')
        carrier.is_active = data.get('is_active', True)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송사 정보가 업데이트되었습니다'})
    
    elif request.method == 'DELETE':
        carrier_id = request.args.get('id')
        carrier = Carrier.query.get_or_404(carrier_id)
        
        db.session.delete(carrier)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송사가 삭제되었습니다'})

@app.route('/api/admin/drivers', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_drivers():
    if request.method == 'GET':
        drivers = Driver.query.all()
        return jsonify([{
            'id': d.id,
            'user_id': d.user_id,
            'carrier_id': d.carrier_id,
            'license_number': d.license_number,
            'vehicle_type': d.vehicle_type,
            'vehicle_number': d.vehicle_number,
            'status': d.status,
            'current_location_lat': d.current_location_lat,
            'current_location_lng': d.current_location_lng,
            'is_active': d.is_active,
            'created_at': d.created_at.isoformat()
        } for d in drivers])
    
    elif request.method == 'POST':
        data = request.get_json()
        driver = Driver(
            user_id=data['user_id'],
            carrier_id=data['carrier_id'],
            license_number=data['license_number'],
            vehicle_type=data.get('vehicle_type', ''),
            vehicle_number=data.get('vehicle_number', ''),
            status=data.get('status', 'available')
        )
        
        db.session.add(driver)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '기사가 생성되었습니다'})
    
    elif request.method == 'PUT':
        data = request.get_json()
        driver = Driver.query.get_or_404(data['id'])
        
        driver.license_number = data['license_number']
        driver.vehicle_type = data.get('vehicle_type', '')
        driver.vehicle_number = data.get('vehicle_number', '')
        driver.status = data.get('status', 'available')
        driver.is_active = data.get('is_active', True)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '기사 정보가 업데이트되었습니다'})
    
    elif request.method == 'DELETE':
        driver_id = request.args.get('id')
        driver = Driver.query.get_or_404(driver_id)
        
        db.session.delete(driver)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '기사가 삭제되었습니다'})

@app.route('/api/admin/statistics', methods=['GET'])
@login_required
@role_required('admin')
def admin_statistics():
    try:
        # Overview statistics
        total_users = User.query.count()
        total_carriers = Carrier.query.count()
        total_drivers = Driver.query.count()
        active_tolerances = Tolerance.query.filter_by(status='available').count()
        pending_requests = DeliveryRequest.query.filter_by(status='pending').count()
        total_matches = Match.query.count()
        completed_matches = Match.query.filter_by(status='completed').count()
        
        # Monthly statistics
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_tolerances = Tolerance.query.filter(Tolerance.created_at >= month_start).count()
        monthly_requests = DeliveryRequest.query.filter(DeliveryRequest.created_at >= month_start).count()
        monthly_matches = Match.query.filter(Match.created_at >= month_start).count()
        
        # Status breakdown
        tolerance_status = db.session.query(Tolerance.status, db.func.count(Tolerance.id)).group_by(Tolerance.status).all()
        request_status = db.session.query(DeliveryRequest.status, db.func.count(DeliveryRequest.id)).group_by(DeliveryRequest.status).all()
        match_status = db.session.query(Match.status, db.func.count(Match.id)).group_by(Match.status).all()
        
        # Top carriers by matches - with error handling
        try:
            top_carriers = db.session.query(
                Carrier.company_name,
                db.func.count(Match.id)
            ).join(Tolerance).join(Match).group_by(Carrier.id).order_by(db.func.count(Match.id).desc()).limit(5).all()
        except Exception:
            # If join fails, return empty list
            top_carriers = []
        
        return jsonify({
            'overview': {
                'total_users': total_users,
                'total_carriers': total_carriers,
                'total_drivers': total_drivers,
                'active_tolerances': active_tolerances,
                'pending_requests': pending_requests,
                'total_matches': total_matches,
                'completed_matches': completed_matches
            },
            'monthly': {
                'tolerances': monthly_tolerances,
                'requests': monthly_requests,
                'matches': monthly_matches
            },
            'status_breakdown': {
                'tolerances': dict(tolerance_status),
                'requests': dict(request_status),
                'matches': dict(match_status)
            },
            'top_carriers': [{'name': name, 'matches': count} for name, count in top_carriers]
        })
    
    except Exception as e:
        return jsonify({'error': f'통계 조회 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/admin/vehicles', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_vehicles():
    if request.method == 'GET':
        vehicles = Vehicle.query.all()
        return jsonify([{
            'id': v.id,
            'carrier_id': v.carrier_id,
            'carrier_name': v.carrier.company_name if v.carrier else None,
            'vehicle_number': v.vehicle_number,
            'vehicle_type': v.vehicle_type,
            'status': v.status,
            'description': v.description,
            'is_active': v.is_active,
            'created_at': v.created_at.isoformat()
        } for v in vehicles])
    elif request.method == 'POST':
        data = request.get_json()
        vehicle = Vehicle(
            carrier_id=data['carrier_id'],
            vehicle_number=data['vehicle_number'],
            vehicle_type=data['vehicle_type'],
            status=data.get('status', 'available'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True)
        )
        db.session.add(vehicle)
        db.session.commit()
        return jsonify({'success': True, 'message': '차량이 생성되었습니다'})
    elif request.method == 'PUT':
        data = request.get_json()
        vehicle = Vehicle.query.get_or_404(data['id'])
        vehicle.carrier_id = data['carrier_id']
        vehicle.vehicle_number = data['vehicle_number']
        vehicle.vehicle_type = data['vehicle_type']
        vehicle.status = data.get('status', 'available')
        vehicle.description = data.get('description', '')
        vehicle.is_active = data.get('is_active', True)
        db.session.commit()
        return jsonify({'success': True, 'message': '차량 정보가 업데이트되었습니다'})
    elif request.method == 'DELETE':
        vehicle_id = request.args.get('id')
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        db.session.delete(vehicle)
        db.session.commit()
        return jsonify({'success': True, 'message': '차량이 삭제되었습니다'})

# Database initialization
with app.app_context():
    db.create_all()
    logging.info("Database tables created")
    
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
            address='부산시 해운대구 센텀중앙로 100',
            phone='010-1111-1111',
            email='carrier1@example.com'
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
            address='인천시 연수구 컨벤시아대로 300',
            phone='010-2222-2222',
            email='carrier2@example.com'
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
    
    # 차량 샘플 데이터가 없으면 2개 이상 자동 추가
    if Carrier.query.first() and (not Vehicle.query.first() or Vehicle.query.count() < 2):
        carrier = Carrier.query.first()
        v1 = Vehicle(carrier_id=carrier.id, vehicle_number='123가4567', vehicle_type='트럭', status='available', description='샘플 트럭')
        v2 = Vehicle(carrier_id=carrier.id, vehicle_number='456나7890', vehicle_type='냉동탑차', status='maintenance', description='샘플 냉동차')
        db.session.add_all([v1, v2])
        db.session.commit()
        logging.info("샘플 차량 데이터 생성 완료")
    
    logging.info("Database initialization completed")

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    """클라이언트 연결 처리"""
    logging.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to location tracking server'})

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제 처리"""
    logging.info(f"Client disconnected: {request.sid}")
    if request.sid in active_connections:
        user_id = active_connections[request.sid]
        del active_connections[request.sid]
        logging.info(f"User {user_id} disconnected")

@socketio.on('join_tracking')
def handle_join_tracking(data):
    """위치 추적 룸 참가"""
    try:
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        
        if not user_id or not match_id:
            emit('error', {'message': 'user_id와 match_id가 필요합니다'})
            return
        
        # 사용자 인증 확인
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': '유효하지 않은 사용자입니다'})
            return
        
        # 매칭 정보 확인
        match = Match.query.get(match_id)
        if not match:
            emit('error', {'message': '유효하지 않은 매칭입니다'})
            return
        
        # 권한 확인 (기사, 운송사, 관리자만 접근 가능)
        if user.role == 'driver':
            driver = Driver.query.filter_by(user_id=user_id).first()
            if not driver or match.driver_id != driver.id:
                emit('error', {'message': '권한이 없습니다'})
                return
        elif user.role == 'carrier':
            # 운송사는 자신의 매칭만 볼 수 있음
            if match.tolerance.carrier_id != user.carrier.id:
                emit('error', {'message': '권한이 없습니다'})
                return
        elif user.role != 'admin':
            emit('error', {'message': '권한이 없습니다'})
            return
        
        # 룸 참가
        room = f"match_{match_id}"
        join_room(room)
        active_connections[request.sid] = user_id
        
        logging.info(f"User {user_id} joined tracking room: {room}")
        emit('joined_tracking', {
            'message': f'매칭 {match_id} 추적에 참가했습니다',
            'match_id': match_id
        })
        
        # 기존 위치 데이터 전송
        locations = LocationPath.query.filter_by(match_id=match_id).order_by(LocationPath.timestamp).all()
        location_data = [{
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'timestamp': loc.timestamp.isoformat(),
            'status': loc.status,
            'notes': loc.notes
        } for loc in locations]
        
        emit('location_history', {
            'match_id': match_id,
            'locations': location_data
        })
        
    except Exception as e:
        logging.error(f"Error in join_tracking: {str(e)}")
        emit('error', {'message': f'오류가 발생했습니다: {str(e)}'})

@socketio.on('leave_tracking')
def handle_leave_tracking(data):
    """위치 추적 룸 나가기"""
    try:
        match_id = data.get('match_id')
        if match_id:
            room = f"match_{match_id}"
            leave_room(room)
            logging.info(f"Client left tracking room: {room}")
            emit('left_tracking', {
                'message': f'매칭 {match_id} 추적을 종료했습니다',
                'match_id': match_id
            })
    except Exception as e:
        logging.error(f"Error in leave_tracking: {str(e)}")
        emit('error', {'message': f'오류가 발생했습니다: {str(e)}'})

@socketio.on('update_location')
def handle_update_location(data):
    """기사 위치 업데이트"""
    try:
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        status = data.get('status', 'in_transit')
        notes = data.get('notes', '')
        
        # 필수 데이터 검증
        if not all([user_id, match_id, latitude, longitude]):
            emit('error', {'message': '필수 데이터가 누락되었습니다'})
            return
        
        # 사용자 인증 확인
        user = User.query.get(user_id)
        if not user or user.role != 'driver':
            emit('error', {'message': '기사만 위치를 업데이트할 수 있습니다'})
            return
        
        # 매칭 정보 확인
        match = Match.query.get(match_id)
        if not match:
            emit('error', {'message': '유효하지 않은 매칭입니다'})
            return
        
        # 기사 권한 확인
        driver = Driver.query.filter_by(user_id=user_id).first()
        if not driver or match.driver_id != driver.id:
            emit('error', {'message': '권한이 없습니다'})
            return
        
        # 위치 데이터 저장
        location_path = LocationPath(
            match_id=match_id,
            latitude=latitude,
            longitude=longitude,
            status=status,
            notes=notes
        )
        
        db.session.add(location_path)
        
        # 기사 현재 위치 업데이트
        driver.current_location_lat = latitude
        driver.current_location_lng = longitude
        
        db.session.commit()
        
        # 위치 데이터를 룸의 모든 클라이언트에게 브로드캐스트
        location_data = {
            'match_id': match_id,
            'driver_id': driver.id,
            'driver_name': user.full_name,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': location_path.timestamp.isoformat(),
            'status': status,
            'notes': notes
        }
        
        room = f"match_{match_id}"
        socketio.emit('location_updated', location_data, room=room)
        
        logging.info(f"Location updated for match {match_id}: {latitude}, {longitude}")
        emit('location_update_success', {
            'message': '위치가 업데이트되었습니다',
            'location': location_data
        })
        
    except Exception as e:
        logging.error(f"Error in update_location: {str(e)}")
        db.session.rollback()
        emit('error', {'message': f'위치 업데이트 중 오류가 발생했습니다: {str(e)}'})

@socketio.on('request_location')
def handle_request_location(data):
    """특정 매칭의 현재 위치 요청"""
    try:
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        
        if not user_id or not match_id:
            emit('error', {'message': 'user_id와 match_id가 필요합니다'})
            return
        
        # 사용자 인증 확인
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': '유효하지 않은 사용자입니다'})
            return
        
        # 매칭 정보 확인
        match = Match.query.get(match_id)
        if not match:
            emit('error', {'message': '유효하지 않은 매칭입니다'})
            return
        
        # 권한 확인
        if user.role == 'driver':
            driver = Driver.query.filter_by(user_id=user_id).first()
            if not driver or match.driver_id != driver.id:
                emit('error', {'message': '권한이 없습니다'})
                return
        elif user.role == 'carrier':
            if match.tolerance.carrier_id != user.carrier.id:
                emit('error', {'message': '권한이 없습니다'})
                return
        elif user.role != 'admin':
            emit('error', {'message': '권한이 없습니다'})
            return
        
        # 기사 현재 위치 조회
        driver = Driver.query.get(match.driver_id)
        if driver and driver.current_location_lat and driver.current_location_lng:
            location_data = {
                'match_id': match_id,
                'driver_id': driver.id,
                'driver_name': driver.user.full_name,
                'latitude': driver.current_location_lat,
                'longitude': driver.current_location_lng,
                'timestamp': datetime.now().isoformat(),
                'status': 'current',
                'notes': '현재 위치'
            }
            emit('current_location', location_data)
        else:
            emit('error', {'message': '기사 위치 정보가 없습니다'})
            
    except Exception as e:
        logging.error(f"Error in request_location: {str(e)}")
        emit('error', {'message': f'위치 요청 중 오류가 발생했습니다: {str(e)}'})

@socketio.on('delivery_status_update')
def handle_delivery_status_update(data):
    """배송 상태 업데이트"""
    try:
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        status = data.get('status')  # pickup, in_transit, delivered
        
        if not all([user_id, match_id, status]):
            emit('error', {'message': '필수 데이터가 누락되었습니다'})
            return
        
        # 사용자 인증 확인
        user = User.query.get(user_id)
        if not user or user.role != 'driver':
            emit('error', {'message': '기사만 배송 상태를 업데이트할 수 있습니다'})
            return
        
        # 매칭 정보 확인
        match = Match.query.get(match_id)
        if not match:
            emit('error', {'message': '유효하지 않은 매칭입니다'})
            return
        
        # 기사 권한 확인
        driver = Driver.query.filter_by(user_id=user_id).first()
        if not driver or match.driver_id != driver.id:
            emit('error', {'message': '권한이 없습니다'})
            return
        
        # 배송 상태 업데이트
        if status == 'delivered':
            match.status = 'completed'
            match.tolerance.status = 'completed'
            match.delivery_request.status = 'completed'
        
        db.session.commit()
        
        # 상태 변경을 룸의 모든 클라이언트에게 브로드캐스트
        status_data = {
            'match_id': match_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'driver_name': user.full_name
        }
        
        room = f"match_{match_id}"
        socketio.emit('delivery_status_changed', status_data, room=room)
        
        logging.info(f"Delivery status updated for match {match_id}: {status}")
        emit('status_update_success', {
            'message': f'배송 상태가 {status}로 업데이트되었습니다',
            'status': status_data
        })
        
    except Exception as e:
        logging.error(f"Error in delivery_status_update: {str(e)}")
        db.session.rollback()
        emit('error', {'message': f'상태 업데이트 중 오류가 발생했습니다: {str(e)}'})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True) 