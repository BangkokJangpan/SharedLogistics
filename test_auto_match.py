from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest, Match
from datetime import datetime

def test_auto_match():
    with app.app_context():
        print("=== Auto-Match 함수 테스트 ===")
        
        try:
            # 관리자 사용자 찾기
            admin_user = User.query.filter_by(role='admin').first()
            if not admin_user:
                print("❌ 관리자 사용자를 찾을 수 없습니다.")
                return
            
            print(f"✅ 관리자 사용자: {admin_user.username}")
            
            # 여유 운송과 운송 요청 확인
            tolerances = Tolerance.query.filter_by(status='available').all()
            requests = DeliveryRequest.query.filter_by(status='pending').all()
            
            print(f"✅ 사용 가능한 여유 운송: {len(tolerances)}개")
            print(f"✅ 대기 중인 운송 요청: {len(requests)}개")
            
            # 기존 매칭 확인
            existing_matches = Match.query.all()
            print(f"✅ 기존 매칭: {len(existing_matches)}개")
            
            # 매칭 생성 시도
            matches_created = 0
            
            for tolerance in tolerances:
                for request in requests:
                    # 매칭 조건 확인
                    if (tolerance.origin == request.origin and 
                        tolerance.destination == request.destination and
                        tolerance.container_type == request.container_type and
                        tolerance.departure_time.date() == request.pickup_time.date()):
                        
                        # 기존 매칭 확인
                        existing_match = Match.query.filter_by(
                            tolerance_id=tolerance.id,
                            delivery_request_id=request.id
                        ).first()
                        
                        if not existing_match:
                            # 새 매칭 생성
                            match = Match(
                                tolerance_id=tolerance.id,
                                delivery_request_id=request.id,
                                status='pending'
                            )
                            db.session.add(match)
                            matches_created += 1
                            print(f"✅ 매칭 생성: 여유운송 {tolerance.id} ↔ 운송요청 {request.id}")
            
            # 변경사항 커밋
            db.session.commit()
            print(f"✅ 총 {matches_created}개의 매칭이 생성되었습니다.")
            
            # 생성된 매칭 확인
            new_matches = Match.query.all()
            print(f"✅ 전체 매칭 수: {len(new_matches)}개")
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    test_auto_match() 