from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest, Match, LocationPath
from datetime import datetime, timedelta
from functools import wraps
import json
import bcrypt
import jwt
from flask import render_template, request, jsonify, session, redirect, url_for
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

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
        delivery_request = DeliveryRequest(
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
        
        db.session.add(delivery_request)
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
        result.append({
            'id': req.id,
            'carrier_name': req.carrier.company_name,
            'origin': req.origin,
            'destination': req.destination,
            'pickup_time': req.pickup_time.isoformat(),
            'delivery_time': req.delivery_time.isoformat() if req.delivery_time else None,
            'container_type': req.container_type,
            'container_count': req.container_count,
            'cargo_details': json.loads(req.cargo_details_json) if req.cargo_details_json else {},
            'budget': float(req.budget) if req.budget else 0,
            'status': req.status,
            'created_at': req.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/matches', methods=['GET'])
@login_required
def matches():
    user = request.user
    
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
                'id': match.tolerance.id,
                'origin': match.tolerance.origin,
                'destination': match.tolerance.destination,
                'departure_time': match.tolerance.departure_time.isoformat(),
                'container_type': match.tolerance.container_type,
                'carrier_name': match.tolerance.carrier.company_name
            },
            'request': {
                'id': match.request.id,
                'origin': match.request.origin,
                'destination': match.request.destination,
                'pickup_time': match.request.pickup_time.isoformat(),
                'container_type': match.request.container_type,
                'carrier_name': match.request.carrier.company_name
            },
            'driver': {
                'name': match.driver.user.full_name if match.driver else None,
                'vehicle_number': match.driver.vehicle_number if match.driver else None
            },
            'status': match.status,
            'matched_at': match.matched_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/matches/<int:match_id>/accept', methods=['POST'])
@login_required
def accept_match(match_id):
    user = request.user
    
    match = Match.query.get_or_404(match_id)
    
    # Check if user has permission to accept this match
    if user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        if match.tolerance.carrier_id != carrier.id and match.request.carrier_id != carrier.id:
            return jsonify({'error': '이 매칭을 수락할 권한이 없습니다'}), 403
    
    match.status = 'accepted'
    match.accepted_at = datetime.utcnow()
    
    # Update tolerance and request status
    match.tolerance.status = 'matched'
    match.request.status = 'matched'
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '매칭이 수락되었습니다'})

@app.route('/api/matches/<int:match_id>/reject', methods=['POST'])
@login_required
def reject_match(match_id):
    user = request.user
    
    match = Match.query.get_or_404(match_id)
    data = request.get_json()
    
    # Check if user has permission to reject this match
    if user.role == 'carrier':
        carrier = Carrier.query.filter_by(user_id=user.id).first()
        if match.tolerance.carrier_id != carrier.id and match.request.carrier_id != carrier.id:
            return jsonify({'error': '이 매칭을 거절할 권한이 없습니다'}), 403
    
    match.status = 'rejected'
    match.rejection_reason = data.get('reason', '')
    
    # Reset tolerance and request status
    match.tolerance.status = 'available'
    match.request.status = 'pending'
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '매칭이 거절되었습니다'})

@app.route('/api/location/update', methods=['POST'])
@login_required
def update_location():
    user = request.user
    
    if user.role != 'driver':
        return jsonify({'error': '기사만 위치를 업데이트할 수 있습니다'}), 403
    
    driver = Driver.query.filter_by(user_id=user.id).first()
    if not driver:
        return jsonify({'error': '기사 정보를 찾을 수 없습니다'}), 404
    
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    match_id = data.get('match_id')
    
    if not latitude or not longitude:
        return jsonify({'error': '위치 정보가 필요합니다'}), 400
    
    # Update driver's current location
    driver.current_location = json.dumps({'latitude': latitude, 'longitude': longitude})
    
    # If match_id is provided, save location path
    if match_id:
        location_path = LocationPath(
            match_id=match_id,
            driver_id=driver.id,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(location_path)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '위치가 업데이트되었습니다'})

@app.route('/api/location/path/<int:match_id>')
@login_required
def get_location_path(match_id):
    paths = LocationPath.query.filter_by(match_id=match_id).order_by(LocationPath.timestamp).all()
    
    result = []
    for path in paths:
        result.append({
            'latitude': path.latitude,
            'longitude': path.longitude,
            'timestamp': path.timestamp.isoformat()
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
            'contact_person': carrier.contact_person
        })
    
    return jsonify(result)

@app.route('/api/auto-match', methods=['POST'])
@login_required
def auto_match():
    """Basic auto-matching algorithm"""
    user = request.user
    
    if user.role != 'admin':
        return jsonify({'error': '관리자만 자동 매칭을 실행할 수 있습니다'}), 403
    
    # Get available tolerances and pending requests
    tolerances = Tolerance.query.filter_by(status='available').all()
    requests = DeliveryRequest.query.filter_by(status='pending').all()
    
    matches_created = 0
    
    for tolerance in tolerances:
        for request in requests:
            # Basic matching criteria
            if (tolerance.origin == request.origin and 
                tolerance.destination == request.destination and
                tolerance.container_type == request.container_type and
                tolerance.departure_time.date() == request.pickup_time.date()):
                
                # Check if match already exists
                existing_match = Match.query.filter_by(
                    tolerance_id=tolerance.id,
                    request_id=request.id
                ).first()
                
                if not existing_match:
                    # Create new match
                    match = Match(
                        tolerance_id=tolerance.id,
                        request_id=request.id,
                        status='proposed'
                    )
                    db.session.add(match)
                    matches_created += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{matches_created}개의 매칭이 생성되었습니다'
    })

@app.route('/api/admin/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_users():
    """Admin user management API"""
    if request.method == 'GET':
        users = User.query.all()
        result = []
        for user in users:
            result.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name,
                'phone': user.phone,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat()
            })
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': '이미 존재하는 사용자명입니다'}), 400
        
        # Check if email already exists
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
            phone=data.get('phone', ''),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '사용자가 생성되었습니다'})
    
    elif request.method == 'PUT':
        data = request.get_json()
        user_id = data.get('id')
        
        user = User.query.get_or_404(user_id)
        
        # Update user fields
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': '사용자가 수정되었습니다'})
    
    elif request.method == 'DELETE':
        user_id = request.get_json().get('id')
        user = User.query.get_or_404(user_id)
        
        # Don't allow deletion of admin users
        if user.role == 'admin':
            return jsonify({'error': '관리자 계정은 삭제할 수 없습니다'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '사용자가 삭제되었습니다'})

@app.route('/api/admin/carriers', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_carriers():
    """Admin carrier management API"""
    if request.method == 'GET':
        carriers = Carrier.query.all()
        result = []
        for carrier in carriers:
            result.append({
                'id': carrier.id,
                'user_id': carrier.user_id,
                'username': carrier.user.username,
                'company_name': carrier.company_name,
                'business_license': carrier.business_license,
                'contact_person': carrier.contact_person,
                'address': carrier.address,
                'status': carrier.status,
                'created_at': carrier.created_at.isoformat()
            })
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.get_json()
        
        carrier = Carrier(
            user_id=data['user_id'],
            company_name=data['company_name'],
            business_license=data.get('business_license', ''),
            contact_person=data.get('contact_person', ''),
            address=data.get('address', ''),
            status=data.get('status', 'active')
        )
        
        db.session.add(carrier)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송사가 생성되었습니다'})
    
    elif request.method == 'PUT':
        data = request.get_json()
        carrier_id = data.get('id')
        
        carrier = Carrier.query.get_or_404(carrier_id)
        
        # Update carrier fields
        if 'company_name' in data:
            carrier.company_name = data['company_name']
        if 'business_license' in data:
            carrier.business_license = data['business_license']
        if 'contact_person' in data:
            carrier.contact_person = data['contact_person']
        if 'address' in data:
            carrier.address = data['address']
        if 'status' in data:
            carrier.status = data['status']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송사가 수정되었습니다'})
    
    elif request.method == 'DELETE':
        carrier_id = request.get_json().get('id')
        carrier = Carrier.query.get_or_404(carrier_id)
        
        db.session.delete(carrier)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '운송사가 삭제되었습니다'})

@app.route('/api/admin/drivers', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required('admin')
def admin_drivers():
    """Admin driver management API"""
    if request.method == 'GET':
        drivers = Driver.query.all()
        result = []
        for driver in drivers:
            result.append({
                'id': driver.id,
                'user_id': driver.user_id,
                'username': driver.user.username,
                'carrier_id': driver.carrier_id,
                'carrier_name': driver.carrier.company_name,
                'license_number': driver.license_number,
                'vehicle_type': driver.vehicle_type,
                'vehicle_number': driver.vehicle_number,
                'status': driver.status,
                'current_location': driver.current_location,
                'created_at': driver.created_at.isoformat()
            })
        return jsonify(result)
    
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
        driver_id = data.get('id')
        
        driver = Driver.query.get_or_404(driver_id)
        
        # Update driver fields
        if 'carrier_id' in data:
            driver.carrier_id = data['carrier_id']
        if 'license_number' in data:
            driver.license_number = data['license_number']
        if 'vehicle_type' in data:
            driver.vehicle_type = data['vehicle_type']
        if 'vehicle_number' in data:
            driver.vehicle_number = data['vehicle_number']
        if 'status' in data:
            driver.status = data['status']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '기사가 수정되었습니다'})
    
    elif request.method == 'DELETE':
        driver_id = request.get_json().get('id')
        driver = Driver.query.get_or_404(driver_id)
        
        db.session.delete(driver)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '기사가 삭제되었습니다'})

@app.route('/api/admin/statistics', methods=['GET'])
@login_required
@role_required('admin')
def admin_statistics():
    """Admin statistics API"""
    
    # Basic counts
    total_users = User.query.count()
    total_carriers = Carrier.query.count()
    total_drivers = Driver.query.count()
    active_tolerances = Tolerance.query.filter_by(status='available').count()
    pending_requests = DeliveryRequest.query.filter_by(status='pending').count()
    total_matches = Match.query.count()
    completed_matches = Match.query.filter_by(status='completed').count()
    
    # Monthly statistics
    current_month = datetime.now().replace(day=1)
    monthly_tolerances = Tolerance.query.filter(Tolerance.created_at >= current_month).count()
    monthly_requests = DeliveryRequest.query.filter(DeliveryRequest.created_at >= current_month).count()
    monthly_matches = Match.query.filter(Match.matched_at >= current_month).count()
    
    # Status breakdown
    tolerance_status = {}
    for status in ['available', 'matched', 'completed']:
        tolerance_status[status] = Tolerance.query.filter_by(status=status).count()
    
    request_status = {}
    for status in ['pending', 'matched', 'in_transit', 'completed']:
        request_status[status] = DeliveryRequest.query.filter_by(status=status).count()
    
    match_status = {}
    for status in ['proposed', 'accepted', 'rejected', 'in_progress', 'completed']:
        match_status[status] = Match.query.filter_by(status=status).count()
    
    # Top performing carriers
    top_carriers = db.session.query(
        Carrier.company_name,
        db.func.count(Match.id).label('match_count')
    ).join(
        Tolerance, Carrier.id == Tolerance.carrier_id
    ).join(
        Match, Tolerance.id == Match.tolerance_id
    ).group_by(Carrier.id).order_by(db.func.count(Match.id).desc()).limit(5).all()
    
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
            'tolerances': tolerance_status,
            'requests': request_status,
            'matches': match_status
        },
        'top_carriers': [{'name': name, 'matches': count} for name, count in top_carriers]
    })

# Create tables and sample data
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
    
    # Create sample data if not exists
    if User.query.count() == 1:  # Only admin user exists
        # Create sample carriers
        carrier1_password = bcrypt.hashpw('carrier1'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        carrier1_user = User(
            username='carrier1',
            email='carrier1@example.com',
            password_hash=carrier1_password,
            role='carrier',
            full_name='김철수',
            phone='010-1234-5678'
        )
        db.session.add(carrier1_user)
        db.session.commit()
        
        carrier1 = Carrier(
            user_id=carrier1_user.id,
            company_name='한국해운물류',
            business_license='123-45-67890',
            contact_person='김철수',
            address='부산광역시 중구 중앙대로 123'
        )
        db.session.add(carrier1)
        
        carrier2_password = bcrypt.hashpw('carrier2'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        carrier2_user = User(
            username='carrier2',
            email='carrier2@example.com',
            password_hash=carrier2_password,
            role='carrier',
            full_name='이영희',
            phone='010-2345-6789'
        )
        db.session.add(carrier2_user)
        db.session.commit()
        
        carrier2 = Carrier(
            user_id=carrier2_user.id,
            company_name='태평양운송',
            business_license='234-56-78901',
            contact_person='이영희',
            address='인천광역시 연수구 송도동 456'
        )
        db.session.add(carrier2)
        db.session.commit()
        
        # Create sample drivers
        driver1_password = bcrypt.hashpw('driver1'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        driver1_user = User(
            username='driver1',
            email='driver1@example.com',
            password_hash=driver1_password,
            role='driver',
            full_name='박민수',
            phone='010-3456-7890'
        )
        db.session.add(driver1_user)
        db.session.commit()
        
        driver1 = Driver(
            user_id=driver1_user.id,
            carrier_id=carrier1.id,
            license_number='11-23-456789',
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
            phone='010-4567-8901'
        )
        db.session.add(driver2_user)
        db.session.commit()
        
        driver2 = Driver(
            user_id=driver2_user.id,
            carrier_id=carrier2.id,
            license_number='22-34-567890',
            vehicle_type='트레일러',
            vehicle_number='인천34나5678',
            status='available'
        )
        db.session.add(driver2)
        db.session.commit()
        
        # Create sample tolerances
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
            destination='인천항',
            departure_time=datetime.now() + timedelta(hours=4),
            arrival_time=datetime.now() + timedelta(hours=12),
            container_type='20ft',
            container_count=3,
            is_empty_run=True,
            price=300000,
            status='available'
        )
        db.session.add(tolerance2)
        
        # Create sample delivery requests
        request1 = DeliveryRequest(
            carrier_id=carrier1.id,
            origin='람차방 항구',
            destination='부산 신항',
            pickup_time=datetime.now() + timedelta(hours=3),
            delivery_time=datetime.now() + timedelta(hours=9),
            container_type='40ft',
            container_count=1,
            cargo_details_json='{"type": "전자제품", "weight": "15톤", "special_handling": "냉장보관"}',
            budget=450000,
            status='pending'
        )
        db.session.add(request1)
        
        request2 = DeliveryRequest(
            carrier_id=carrier2.id,
            origin='람차방 항구',
            destination='인천항',
            pickup_time=datetime.now() + timedelta(hours=5),
            delivery_time=datetime.now() + timedelta(hours=13),
            container_type='20ft',
            container_count=2,
            cargo_details_json='{"type": "의류", "weight": "8톤", "special_handling": "건조보관"}',
            budget=280000,
            status='pending'
        )
        db.session.add(request2)
        
        # Create sample matches
        match1 = Match(
            tolerance_id=tolerance1.id,
            request_id=request1.id,
            driver_id=driver1.id,
            status='proposed'
        )
        db.session.add(match1)
        
        db.session.commit()
        logging.info("Sample data created")
    
    logging.info("Database initialization completed")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)