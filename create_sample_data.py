from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest
import bcrypt
from datetime import datetime, timedelta
import random

def create_sample_data():
    with app.app_context():
        # 기존 데이터 확인
        existing_carrier = Carrier.query.first()
        if not existing_carrier:
            print("먼저 create_test_data.py를 실행하여 기본 데이터를 생성해주세요.")
            return
        
        # 여유 운송 샘플 데이터 생성 (10개)
        tolerance_data = [
            {
                'origin': '부산항',
                'destination': '서울시 강남구',
                'departure_time': datetime.now() + timedelta(days=1, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=1, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 3),
                'is_empty_run': False,
                'price': random.randint(50000, 150000)
            },
            {
                'origin': '인천항',
                'destination': '대구시 수성구',
                'departure_time': datetime.now() + timedelta(days=2, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=2, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'is_empty_run': True,
                'price': random.randint(30000, 80000)
            },
            {
                'origin': '울산항',
                'destination': '광주시 서구',
                'departure_time': datetime.now() + timedelta(days=3, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=3, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 4),
                'is_empty_run': False,
                'price': random.randint(60000, 180000)
            },
            {
                'origin': '서울시 강남구',
                'destination': '부산항',
                'departure_time': datetime.now() + timedelta(days=1, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=1, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'is_empty_run': False,
                'price': random.randint(40000, 100000)
            },
            {
                'origin': '대구시 수성구',
                'destination': '인천항',
                'departure_time': datetime.now() + timedelta(days=2, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=2, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 3),
                'is_empty_run': True,
                'price': random.randint(45000, 120000)
            },
            {
                'origin': '광주시 서구',
                'destination': '울산항',
                'departure_time': datetime.now() + timedelta(days=3, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=3, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'is_empty_run': False,
                'price': random.randint(35000, 90000)
            },
            {
                'origin': '대전시 유성구',
                'destination': '부산항',
                'departure_time': datetime.now() + timedelta(days=4, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=4, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 3),
                'is_empty_run': False,
                'price': random.randint(55000, 140000)
            },
            {
                'origin': '부산항',
                'destination': '대전시 유성구',
                'departure_time': datetime.now() + timedelta(days=5, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=5, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'is_empty_run': True,
                'price': random.randint(40000, 110000)
            },
            {
                'origin': '인천항',
                'destination': '서울시 강남구',
                'departure_time': datetime.now() + timedelta(days=6, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=6, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 4),
                'is_empty_run': False,
                'price': random.randint(65000, 160000)
            },
            {
                'origin': '울산항',
                'destination': '인천항',
                'departure_time': datetime.now() + timedelta(days=7, hours=random.randint(0, 12)),
                'arrival_time': datetime.now() + timedelta(days=7, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'is_empty_run': False,
                'price': random.randint(38000, 95000)
            }
        ]
        
        # 여유 운송 데이터 생성
        for data in tolerance_data:
            tolerance = Tolerance(
                carrier_id=existing_carrier.id,
                origin=data['origin'],
                destination=data['destination'],
                departure_time=data['departure_time'],
                arrival_time=data['arrival_time'],
                container_type=data['container_type'],
                container_count=data['container_count'],
                is_empty_run=data['is_empty_run'],
                price=data['price'],
                status='available'
            )
            db.session.add(tolerance)
        
        # 운송 요청 샘플 데이터 생성 (10개)
        delivery_request_data = [
            {
                'origin': '서울시 강남구',
                'destination': '부산항',
                'pickup_time': datetime.now() + timedelta(days=1, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=1, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 3),
                'cargo_details_json': '{"type": "전자제품", "weight": "5톤", "volume": "30CBM"}',
                'budget': random.randint(60000, 180000)
            },
            {
                'origin': '대구시 수성구',
                'destination': '인천항',
                'pickup_time': datetime.now() + timedelta(days=2, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=2, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'cargo_details_json': '{"type": "의류", "weight": "2톤", "volume": "15CBM"}',
                'budget': random.randint(40000, 100000)
            },
            {
                'origin': '광주시 서구',
                'destination': '울산항',
                'pickup_time': datetime.now() + timedelta(days=3, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=3, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 4),
                'cargo_details_json': '{"type": "자동차부품", "weight": "8톤", "volume": "45CBM"}',
                'budget': random.randint(70000, 200000)
            },
            {
                'origin': '부산항',
                'destination': '서울시 강남구',
                'pickup_time': datetime.now() + timedelta(days=1, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=1, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'cargo_details_json': '{"type": "식품", "weight": "3톤", "volume": "20CBM"}',
                'budget': random.randint(45000, 120000)
            },
            {
                'origin': '인천항',
                'destination': '대구시 수성구',
                'pickup_time': datetime.now() + timedelta(days=2, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=2, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 3),
                'cargo_details_json': '{"type": "화학제품", "weight": "6톤", "volume": "35CBM"}',
                'budget': random.randint(55000, 150000)
            },
            {
                'origin': '울산항',
                'destination': '광주시 서구',
                'pickup_time': datetime.now() + timedelta(days=3, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=3, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'cargo_details_json': '{"type": "섬유제품", "weight": "2.5톤", "volume": "18CBM"}',
                'budget': random.randint(38000, 95000)
            },
            {
                'origin': '대전시 유성구',
                'destination': '부산항',
                'pickup_time': datetime.now() + timedelta(days=4, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=4, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 3),
                'cargo_details_json': '{"type": "기계류", "weight": "10톤", "volume": "50CBM"}',
                'budget': random.randint(80000, 220000)
            },
            {
                'origin': '부산항',
                'destination': '대전시 유성구',
                'pickup_time': datetime.now() + timedelta(days=5, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=5, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'cargo_details_json': '{"type": "가구", "weight": "4톤", "volume": "25CBM"}',
                'budget': random.randint(50000, 130000)
            },
            {
                'origin': '서울시 강남구',
                'destination': '인천항',
                'pickup_time': datetime.now() + timedelta(days=6, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=6, hours=random.randint(13, 24)),
                'container_type': '40ft',
                'container_count': random.randint(1, 4),
                'cargo_details_json': '{"type": "의료기기", "weight": "3톤", "volume": "22CBM"}',
                'budget': random.randint(65000, 170000)
            },
            {
                'origin': '인천항',
                'destination': '울산항',
                'pickup_time': datetime.now() + timedelta(days=7, hours=random.randint(0, 12)),
                'delivery_time': datetime.now() + timedelta(days=7, hours=random.randint(13, 24)),
                'container_type': '20ft',
                'container_count': random.randint(1, 2),
                'cargo_details_json': '{"type": "도서", "weight": "1.5톤", "volume": "12CBM"}',
                'budget': random.randint(35000, 85000)
            }
        ]
        
        # 운송 요청 데이터 생성
        for data in delivery_request_data:
            delivery_request = DeliveryRequest(
                carrier_id=existing_carrier.id,
                origin=data['origin'],
                destination=data['destination'],
                pickup_time=data['pickup_time'],
                delivery_time=data['delivery_time'],
                container_type=data['container_type'],
                container_count=data['container_count'],
                cargo_details_json=data['cargo_details_json'],
                budget=data['budget'],
                status='pending'
            )
            db.session.add(delivery_request)
        
        db.session.commit()
        
        print('샘플 데이터가 성공적으로 생성되었습니다.')
        print(f'- 여유 운송: {len(tolerance_data)}개')
        print(f'- 운송 요청: {len(delivery_request_data)}개')

if __name__ == '__main__':
    create_sample_data() 