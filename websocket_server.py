import json
import logging
from datetime import datetime
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room
from app_simple import app, db
from app_simple import User, Driver, Match, LocationPath

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active connections
active_connections = {}

@socketio.on('connect')
def handle_connect():
    """클라이언트 연결 처리"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to location tracking server'})

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제 처리"""
    logger.info(f"Client disconnected: {request.sid}")
    if request.sid in active_connections:
        user_id = active_connections[request.sid]
        del active_connections[request.sid]
        logger.info(f"User {user_id} disconnected")

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
        
        logger.info(f"User {user_id} joined tracking room: {room}")
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
        logger.error(f"Error in join_tracking: {str(e)}")
        emit('error', {'message': f'오류가 발생했습니다: {str(e)}'})

@socketio.on('leave_tracking')
def handle_leave_tracking(data):
    """위치 추적 룸 나가기"""
    try:
        match_id = data.get('match_id')
        if match_id:
            room = f"match_{match_id}"
            leave_room(room)
            logger.info(f"Client left tracking room: {room}")
            emit('left_tracking', {
                'message': f'매칭 {match_id} 추적을 종료했습니다',
                'match_id': match_id
            })
    except Exception as e:
        logger.error(f"Error in leave_tracking: {str(e)}")
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
        
        logger.info(f"Location updated for match {match_id}: {latitude}, {longitude}")
        emit('location_update_success', {
            'message': '위치가 업데이트되었습니다',
            'location': location_data
        })
        
    except Exception as e:
        logger.error(f"Error in update_location: {str(e)}")
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
        logger.error(f"Error in request_location: {str(e)}")
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
        
        logger.info(f"Delivery status updated for match {match_id}: {status}")
        emit('status_update_success', {
            'message': f'배송 상태가 {status}로 업데이트되었습니다',
            'status': status_data
        })
        
    except Exception as e:
        logger.error(f"Error in delivery_status_update: {str(e)}")
        db.session.rollback()
        emit('error', {'message': f'상태 업데이트 중 오류가 발생했습니다: {str(e)}'})

if __name__ == '__main__':
    logger.info("Starting WebSocket server...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True) 