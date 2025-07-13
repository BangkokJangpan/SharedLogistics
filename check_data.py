from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest

def check_data():
    with app.app_context():
        print("=== 데이터베이스 현황 ===")
        
        # 사용자 데이터
        users = User.query.all()
        print(f"사용자: {len(users)}명")
        for user in users:
            print(f"  - {user.username} ({user.role}) - {user.full_name}")
        
        # 운송사 데이터
        carriers = Carrier.query.all()
        print(f"\n운송사: {len(carriers)}개")
        for carrier in carriers:
            print(f"  - {carrier.company_name} (상태: {getattr(carrier, 'status', 'N/A')})")
        
        # 기사 데이터
        drivers = Driver.query.all()
        print(f"\n기사: {len(drivers)}명")
        for driver in drivers:
            print(f"  - {driver.user.full_name if driver.user else 'N/A'} (차량: {driver.vehicle_number})")
        
        # 여유 운송 데이터
        tolerances = Tolerance.query.all()
        print(f"\n여유 운송: {len(tolerances)}개")
        for tolerance in tolerances:
            print(f"  - {tolerance.origin} → {tolerance.destination} ({tolerance.container_type}, {tolerance.container_count}개)")
        
        # 운송 요청 데이터
        delivery_requests = DeliveryRequest.query.all()
        print(f"\n운송 요청: {len(delivery_requests)}개")
        for request in delivery_requests:
            print(f"  - {request.origin} → {request.destination} ({request.container_type}, {request.container_count}개)")

if __name__ == '__main__':
    check_data() 