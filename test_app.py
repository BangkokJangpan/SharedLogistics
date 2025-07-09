import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from app import app, db
from models import User, Carrier, Driver, Tolerance, DeliveryRequest, Match, LocationPath
import bcrypt

class LogisticsTestCase(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary database for testing
        self.db_fd, db_path = tempfile.mkstemp()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app = app.test_client()
        
        with app.app_context():
            db.drop_all()
            db.create_all()
            self.create_test_users()
    
    def tearDown(self):
        with app.app_context():
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    
    def create_test_users(self):
        # Create test admin user
        admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = User(
            username='admin',
            email='admin@test.com',
            password_hash=admin_password,
            role='admin',
            full_name='관리자'
        )
        db.session.add(admin_user)
        
        # Create test carrier user
        carrier_password = bcrypt.hashpw('carrier123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        carrier_user = User(
            username='testcarrier',
            email='carrier@test.com',
            password_hash=carrier_password,
            role='carrier',
            full_name='테스트운송사'
        )
        db.session.add(carrier_user)
        db.session.commit()
        
        # Create carrier profile
        carrier = Carrier(
            user_id=carrier_user.id,
            company_name='테스트운송회사',
            business_license='123-45-67890',
            contact_person='테스트운송사',
            address='테스트주소'
        )
        db.session.add(carrier)
        db.session.commit()
        
        # Create test driver user
        driver_password = bcrypt.hashpw('driver123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        driver_user = User(
            username='testdriver',
            email='driver@test.com',
            password_hash=driver_password,
            role='driver',
            full_name='테스트기사'
        )
        db.session.add(driver_user)
        db.session.commit()
        
        # Create driver profile
        driver = Driver(
            user_id=driver_user.id,
            carrier_id=carrier.id,
            license_number='12-34-567890',
            vehicle_type='트레일러',
            vehicle_number='테스트123',
            status='available'
        )
        db.session.add(driver)
        db.session.commit()
    
    def login_as_admin(self):
        response = self.app.post('/login', 
                                data=json.dumps({'username': 'admin', 'password': 'admin123'}),
                                content_type='application/json')
        return response
    
    def login_as_carrier(self):
        response = self.app.post('/login', 
                                data=json.dumps({'username': 'testcarrier', 'password': 'carrier123'}),
                                content_type='application/json')
        return response
    
    def login_as_driver(self):
        response = self.app.post('/login', 
                                data=json.dumps({'username': 'testdriver', 'password': 'driver123'}),
                                content_type='application/json')
        return response
    
    def test_admin_login(self):
        """Test admin login functionality"""
        response = self.login_as_admin()
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'admin')
    
    def test_carrier_login(self):
        """Test carrier login functionality"""
        response = self.login_as_carrier()
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'carrier')
    
    def test_tolerance_creation(self):
        """Test tolerance creation API"""
        # Login as carrier first
        with self.app.session_transaction() as sess:
            sess['user_id'] = 2  # carrier user id
        
        tolerance_data = {
            'origin': '람차방 항구',
            'destination': '부산 신항',
            'departure_time': (datetime.now() + timedelta(hours=2)).isoformat(),
            'arrival_time': (datetime.now() + timedelta(hours=8)).isoformat(),
            'container_type': '40ft',
            'container_count': 2,
            'price': 500000,
            'is_empty_run': False
        }
        
        response = self.app.post('/api/tolerances',
                                data=json.dumps(tolerance_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        
        # Verify tolerance was created in database
        with app.app_context():
            tolerance = Tolerance.query.filter_by(origin='람차방 항구').first()
            self.assertIsNotNone(tolerance)
            self.assertEqual(tolerance.destination, '부산 신항')
    
    def test_delivery_request_creation(self):
        """Test delivery request creation API"""
        # Login as carrier first
        with self.app.session_transaction() as sess:
            sess['user_id'] = 2  # carrier user id
        
        request_data = {
            'origin': '람차방 항구',
            'destination': '부산 신항',
            'pickup_time': (datetime.now() + timedelta(hours=3)).isoformat(),
            'delivery_time': (datetime.now() + timedelta(hours=9)).isoformat(),
            'container_type': '40ft',
            'container_count': 1,
            'budget': 450000,
            'cargo_details': '전자제품'
        }
        
        response = self.app.post('/api/delivery-requests',
                                data=json.dumps(request_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        
        # Verify request was created in database
        with app.app_context():
            request = DeliveryRequest.query.filter_by(origin='람차방 항구').first()
            self.assertIsNotNone(request)
            self.assertEqual(request.destination, '부산 신항')
    
    def test_auto_matching(self):
        """Test auto matching functionality"""
        # Login as admin
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1  # admin user id
        
        # Create tolerance and request first
        with app.app_context():
            carrier = Carrier.query.first()
            
            tolerance = Tolerance(
                carrier_id=carrier.id,
                origin='람차방 항구',
                destination='부산 신항',
                departure_time=datetime.now() + timedelta(hours=2),
                container_type='40ft',
                container_count=2,
                price=500000,
                status='available'
            )
            db.session.add(tolerance)
            
            request = DeliveryRequest(
                carrier_id=carrier.id,
                origin='람차방 항구',
                destination='부산 신항',
                pickup_time=datetime.now() + timedelta(hours=3),
                container_type='40ft',
                container_count=1,
                budget=450000,
                status='pending'
            )
            db.session.add(request)
            db.session.commit()
        
        response = self.app.post('/api/auto-match',
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        
        # Verify match was created
        with app.app_context():
            match = Match.query.first()
            self.assertIsNotNone(match)
            self.assertEqual(match.status, 'proposed')
    
    def test_dashboard_stats(self):
        """Test dashboard statistics API"""
        # Login as admin
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1  # admin user id
        
        response = self.app.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        
        # Check required fields exist
        self.assertIn('total_users', data)
        self.assertIn('active_tolerances', data)
        self.assertIn('pending_requests', data)
        self.assertIn('completed_matches', data)
    
    def test_location_update(self):
        """Test location update functionality"""
        # Login as driver
        with self.app.session_transaction() as sess:
            sess['user_id'] = 3  # driver user id
        
        location_data = {
            'latitude': 37.5665,
            'longitude': 126.9780
        }
        
        response = self.app.post('/api/location/update',
                                data=json.dumps(location_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        
        # Verify location was updated
        with app.app_context():
            driver = Driver.query.filter_by(user_id=3).first()
            self.assertIsNotNone(driver.current_location)
    
    def test_user_registration(self):
        """Test user registration functionality"""
        registration_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'password123',
            'full_name': '새로운 사용자',
            'phone': '010-1234-5678',
            'role': 'carrier',
            'company_name': '새로운 회사',
            'business_license': '987-65-43210',
            'address': '새로운 주소'
        }
        
        response = self.app.post('/register',
                                data=json.dumps(registration_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        
        # Verify user was created
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'carrier')
            
            carrier = Carrier.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(carrier)
            self.assertEqual(carrier.company_name, '새로운 회사')

if __name__ == '__main__':
    unittest.main()