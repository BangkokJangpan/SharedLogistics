from app import app, db
from models import User, Carrier, Driver
import bcrypt

def create_test_data():
    with app.app_context():
        # Create admin user
        admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=admin_password,
            role='admin',
            full_name='관리자',
            phone='010-1234-5678'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        # Create carrier user
        carrier_password = bcrypt.hashpw('carrier123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        carrier_user = User(
            username='carrier1',
            email='carrier1@example.com',
            password_hash=carrier_password,
            role='carrier',
            full_name='김운송',
            phone='010-2345-6789'
        )
        db.session.add(carrier_user)
        db.session.commit()
        
        # Create carrier profile
        carrier = Carrier(
            user_id=carrier_user.id,
            company_name='한국운송(주)',
            business_license='123-45-67890',
            contact_person='김운송',
            address='서울시 강남구 테헤란로 123',
            phone='02-1234-5678',
            email='info@koreatransport.com',
            status='active'
        )
        db.session.add(carrier)
        db.session.commit()
        
        # Create driver user
        driver_password = bcrypt.hashpw('driver123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        driver_user = User(
            username='driver1',
            email='driver1@example.com',
            password_hash=driver_password,
            role='driver',
            full_name='박기사',
            phone='010-3456-7890'
        )
        db.session.add(driver_user)
        db.session.commit()
        
        # Create driver profile
        driver = Driver(
            user_id=driver_user.id,
            carrier_id=carrier.id,
            license_number='12-345678-90',
            vehicle_type='트럭',
            vehicle_number='12가3456',
            status='available',
            current_location='서울시 강남구'
        )
        db.session.add(driver)
        db.session.commit()
        
        print('테스트 데이터가 성공적으로 생성되었습니다.')
        print('Admin 계정: admin / admin123')
        print('Carrier 계정: carrier1 / carrier123')
        print('Driver 계정: driver1 / driver123')

if __name__ == '__main__':
    create_test_data() 