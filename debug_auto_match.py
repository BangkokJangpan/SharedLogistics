from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest, Match
from datetime import datetime

def debug_auto_match():
    with app.app_context():
        print("=== Auto-Match 디버깅 ===")
        
        # 1. 사용자 확인
        print("\n1. 사용자 확인:")
        users = User.query.all()
        for user in users:
            print(f"  - {user.username} ({user.role})")
        
        # 2. 여유 운송 확인
        print("\n2. 여유 운송 확인:")
        tolerances = Tolerance.query.filter_by(status='available').all()
        print(f"  - 사용 가능한 여유 운송: {len(tolerances)}개")
        for tolerance in tolerances:
            print(f"    * {tolerance.origin} → {tolerance.destination} ({tolerance.container_type})")
        
        # 3. 운송 요청 확인
        print("\n3. 운송 요청 확인:")
        requests = DeliveryRequest.query.filter_by(status='pending').all()
        print(f"  - 대기 중인 운송 요청: {len(requests)}개")
        for request in requests:
            print(f"    * {request.origin} → {request.destination} ({request.container_type})")
        
        # 4. 기존 매칭 확인
        print("\n4. 기존 매칭 확인:")
        existing_matches = Match.query.all()
        print(f"  - 기존 매칭: {len(existing_matches)}개")
        
        # 5. 매칭 조건 테스트
        print("\n5. 매칭 조건 테스트:")
        for tolerance in tolerances:
            for request in requests:
                print(f"  - 여유운송 {tolerance.id}: {tolerance.origin} → {tolerance.destination}")
                print(f"  - 운송요청 {request.id}: {request.origin} → {request.destination}")
                print(f"    * 출발지 일치: {tolerance.origin == request.origin}")
                print(f"    * 도착지 일치: {tolerance.destination == request.destination}")
                print(f"    * 컨테이너 타입 일치: {tolerance.container_type == request.container_type}")
                print(f"    * 날짜 일치: {tolerance.departure_time.date() == request.pickup_time.date()}")
                
                # 매칭 조건 확인
                if (tolerance.origin == request.origin and 
                    tolerance.destination == request.destination and
                    tolerance.container_type == request.container_type and
                    tolerance.departure_time.date() == request.pickup_time.date()):
                    print(f"    ✅ 매칭 가능!")
                else:
                    print(f"    ❌ 매칭 불가")
                print()

if __name__ == '__main__':
    debug_auto_match() 