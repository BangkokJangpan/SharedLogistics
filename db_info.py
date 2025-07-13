import sqlite3
import os
from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest, Match, LocationPath

def show_database_info():
    print("=" * 80)
    print("📊 SharedLogistics 데이터베이스 정보")
    print("=" * 80)
    
    # 데이터베이스 기본 정보
    db_path = "shared_logistics.db"
    db_size = os.path.getsize(db_path) / 1024  # KB
    
    print(f"🗄️  데이터베이스 종류: SQLite")
    print(f"📁 경로: {os.path.abspath(db_path)}")
    print(f"📄 파일명: {db_path}")
    print(f"💾 데이터베이스 크기: {db_size:.2f} KB")
    print(f"🔗 연결 문자열: sqlite:///shared_logistics.db")
    print()
    
    # SQLite 연결로 테이블 정보 확인
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 테이블 목록 조회
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("📋 테이블 목록:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count}개 레코드")
    print()
    
    # Flask-SQLAlchemy로 상세 데이터 확인
    with app.app_context():
        print("👥 사용자 테이블 (users)")
        print("-" * 50)
        users = User.query.all()
        for user in users:
            print(f"ID: {user.id}, 사용자명: {user.username}, 역할: {user.role}, 이름: {user.full_name}, 이메일: {user.email}")
        print()
        
        print("🚛 운송사 테이블 (carriers)")
        print("-" * 50)
        carriers = Carrier.query.all()
        for carrier in carriers:
            print(f"ID: {carrier.id}, 회사명: {carrier.company_name}, 사업자번호: {carrier.business_license}, 연락처: {carrier.contact_person}, 상태: {getattr(carrier, 'status', 'N/A')}")
        print()
        
        print("🚗 기사 테이블 (drivers)")
        print("-" * 50)
        drivers = Driver.query.all()
        for driver in drivers:
            user_name = driver.user.full_name if driver.user else 'N/A'
            carrier_name = driver.carrier.company_name if driver.carrier else 'N/A'
            print(f"ID: {driver.id}, 기사명: {user_name}, 운송사: {carrier_name}, 면허번호: {driver.license_number}, 차량번호: {driver.vehicle_number}, 상태: {driver.status}")
        print()
        
        print("📦 여유 운송 테이블 (tolerances)")
        print("-" * 50)
        tolerances = Tolerance.query.all()
        for tolerance in tolerances:
            carrier_name = tolerance.carrier.company_name if tolerance.carrier else 'N/A'
            print(f"ID: {tolerance.id}, 운송사: {carrier_name}, 경로: {tolerance.origin} → {tolerance.destination}, 컨테이너: {tolerance.container_type} {tolerance.container_count}개, 가격: {tolerance.price:,}원, 상태: {tolerance.status}")
        print()
        
        print("📋 운송 요청 테이블 (delivery_requests)")
        print("-" * 50)
        delivery_requests = DeliveryRequest.query.all()
        for request in delivery_requests:
            carrier_name = request.carrier.company_name if request.carrier else 'N/A'
            print(f"ID: {request.id}, 운송사: {carrier_name}, 경로: {request.origin} → {request.destination}, 컨테이너: {request.container_type} {request.container_count}개, 예산: {request.budget:,}원, 상태: {request.status}")
        print()
        
        print("🤝 매칭 테이블 (matches)")
        print("-" * 50)
        matches = Match.query.all()
        for match in matches:
            tolerance_info = f"{match.tolerance.origin} → {match.tolerance.destination}" if match.tolerance else 'N/A'
            request_info = f"{match.delivery_request.origin} → {match.delivery_request.destination}" if match.delivery_request else 'N/A'
            driver_name = match.driver.user.full_name if match.driver and match.driver.user else 'N/A'
            print(f"ID: {match.id}, 여유운송: {tolerance_info}, 운송요청: {request_info}, 기사: {driver_name}, 상태: {match.status}, 가격: {match.price:,}원" if match.price else f"ID: {match.id}, 여유운송: {tolerance_info}, 운송요청: {request_info}, 기사: {driver_name}, 상태: {match.status}")
        print()
        
        print("📍 위치 경로 테이블 (location_paths)")
        print("-" * 50)
        location_paths = LocationPath.query.all()
        for path in location_paths:
            print(f"ID: {path.id}, 매칭ID: {path.match_id}, 좌표: ({path.latitude}, {path.longitude}), 상태: {path.status}, 시간: {path.timestamp}")
        print()
    
    conn.close()
    
    print("=" * 80)
    print("✅ 데이터베이스 정보 조회 완료")
    print("=" * 80)

if __name__ == '__main__':
    show_database_info() 