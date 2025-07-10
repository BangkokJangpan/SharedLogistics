from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User, Carrier, Driver
import bcrypt
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """사용자 로그인"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': '사용자명과 비밀번호를 입력해주세요'}), 400
        
        # 사용자 조회
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': '잘못된 사용자명 또는 비밀번호입니다'}), 401
        
        if not user.is_active:
            return jsonify({'error': '비활성화된 계정입니다'}), 401
        
        # JWT 토큰 생성
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'role': user.role, 'username': user.username}
        )
        
        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '로그인 성공',
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'로그인 중 오류가 발생했습니다: {str(e)}'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """사용자 회원가입"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['username', 'email', 'password', 'role', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field}는 필수 입력 항목입니다'}), 400
        
        # 중복 검사
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': '이미 존재하는 사용자명입니다'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': '이미 존재하는 이메일입니다'}), 400
        
        # 사용자 생성
        user = User(
            username=data['username'],
            email=data['email'],
            role=data['role'],
            full_name=data['full_name'],
            phone=data.get('phone', '')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # 역할별 프로필 생성
        if data['role'] == 'carrier':
            carrier = Carrier(
                user_id=user.id,
                company_name=data.get('company_name', ''),
                business_license=data.get('business_license', ''),
                contact_person=data['full_name'],
                address=data.get('address', '')
            )
            db.session.add(carrier)
            
        elif data['role'] == 'driver':
            if not data.get('carrier_id'):
                return jsonify({'error': '기사 등록 시 소속 운송사 ID가 필요합니다'}), 400
            
            driver = Driver(
                user_id=user.id,
                carrier_id=data['carrier_id'],
                license_number=data.get('license_number', ''),
                vehicle_type=data.get('vehicle_type', ''),
                vehicle_number=data.get('vehicle_number', '')
            )
            db.session.add(driver)
        
        db.session.commit()
        
        return jsonify({
            'message': '회원가입이 성공적으로 완료되었습니다',
            'user_id': user.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'회원가입 중 오류가 발생했습니다: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """현재 로그인한 사용자 프로필 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다'}), 404
        
        profile_data = user.to_dict()
        
        # 역할별 추가 정보
        if user.role == 'carrier':
            carrier = Carrier.query.filter_by(user_id=user.id).first()
            if carrier:
                profile_data['carrier_info'] = carrier.to_dict()
        elif user.role == 'driver':
            driver = Driver.query.filter_by(user_id=user.id).first()
            if driver:
                profile_data['driver_info'] = driver.to_dict()
        
        return jsonify(profile_data), 200
        
    except Exception as e:
        return jsonify({'error': f'프로필 조회 중 오류가 발생했습니다: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """사용자 프로필 수정"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다'}), 404
        
        data = request.get_json()
        
        # 수정 가능한 필드들
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'email' in data:
            # 이메일 중복 검사
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': '이미 사용 중인 이메일입니다'}), 400
            user.email = data['email']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '프로필이 성공적으로 수정되었습니다',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'프로필 수정 중 오류가 발생했습니다: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """비밀번호 변경"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다'}), 404
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': '현재 비밀번호와 새 비밀번호를 입력해주세요'}), 400
        
        # 현재 비밀번호 확인
        if not user.check_password(current_password):
            return jsonify({'error': '현재 비밀번호가 올바르지 않습니다'}), 400
        
        # 새 비밀번호 설정
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': '비밀번호가 성공적으로 변경되었습니다'}), 200
        
    except Exception as e:
        return jsonify({'error': f'비밀번호 변경 중 오류가 발생했습니다: {str(e)}'}), 500