// Global variables
let currentUser = null;
let currentUserRole = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    setupEventListeners();
});

// Check authentication status
function checkAuthStatus() {
    // Check if user is logged in (this would be done via session in a real app)
    const token = sessionStorage.getItem('auth_token');
    if (token) {
        // For now, we'll just show the main section
        // In a real app, we'd validate the token with the server
        showMainSection();
    } else {
        showLoginSection();
    }
}

// Set up event listeners
function setupEventListeners() {
    // Helper function to safely add event listener
    function safeAddEventListener(id, event, handler) {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener(event, handler);
        }
    }
    
    // Login form
    safeAddEventListener('login-form', 'submit', login);
    
    // Register form
    safeAddEventListener('register-form', 'submit', register);
    
    // Show register section
    safeAddEventListener('show-register-btn', 'click', showRegisterSection);
    
    // Back to login
    safeAddEventListener('back-to-login', 'click', showLoginForm);
    
    // Logout
    safeAddEventListener('logout-btn', 'click', function() {
        sessionStorage.removeItem('auth_token');
        currentUser = null;
        currentUserRole = null;
        onLogoutOrLoginFail();
    });
    
    // Role selection change
    safeAddEventListener('reg-role', 'change', toggleRoleFields);
    
    // Tab change listeners
    safeAddEventListener('tolerances-tab', 'click', function() {
        setTimeout(loadTolerances, 100);
    });
    
    safeAddEventListener('requests-tab', 'click', function() {
        setTimeout(loadRequests, 100);
    });
    
    safeAddEventListener('matches-tab', 'click', function() {
        setTimeout(loadMatches, 100);
    });
    
    // Admin tab listener
    safeAddEventListener('admin-tab', 'click', function() {
        console.log('Admin tab clicked');
        setTimeout(loadAdminStatistics, 100);
    });
    
    // Modal buttons
    safeAddEventListener('add-tolerance-btn', 'click', showToleranceForm);
    safeAddEventListener('add-request-btn', 'click', showRequestForm);
    safeAddEventListener('save-tolerance', 'click', submitTolerance);
    safeAddEventListener('save-request', 'click', submitRequest);
    
    // Auto match buttons
    safeAddEventListener('auto-match-btn', 'click', autoMatch);
    safeAddEventListener('auto-match-admin-btn', 'click', autoMatch);
    
    // Admin buttons
    safeAddEventListener('refresh-stats-btn', 'click', loadAdminStatistics);
    safeAddEventListener('statistics-tab', 'click', function() {
        setTimeout(loadAdminStatistics, 100);
    });
    safeAddEventListener('users-tab', 'click', function() {
        setTimeout(loadAdminUsers, 100);
    });
    safeAddEventListener('carriers-tab', 'click', function() {
        console.log('Carriers tab clicked');
        setTimeout(loadAdminCarriers, 100);
    });
    safeAddEventListener('drivers-tab', 'click', function() {
        console.log('Drivers tab clicked');
        setTimeout(loadAdminDrivers, 100);
    });
    safeAddEventListener('vehicles-tab', 'click', function() {
        setTimeout(loadAdminVehicles, 100);
    });
}

// Login function
async function login(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            window.currentUser = data.user;
            currentUserRole = data.user.role;
            sessionStorage.setItem('auth_token', 'dummy_token'); // In real app, store actual token
            onLoginSuccess();
            showAlert('로그인에 성공했습니다!', 'success');
        } else {
            onLogoutOrLoginFail();
            showAlert(data.error || '로그인에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Register function
async function register(e) {
    e.preventDefault();
    
    const formData = {
        username: document.getElementById('reg-username').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        full_name: document.getElementById('reg-fullname').value,
        phone: document.getElementById('reg-phone').value,
        role: document.getElementById('reg-role').value
    };
    
    // Add role-specific fields
    if (formData.role === 'carrier') {
        formData.company_name = document.getElementById('company-name').value;
        formData.business_license = document.getElementById('business-license').value;
        formData.address = document.getElementById('address').value;
    } else if (formData.role === 'driver') {
        formData.carrier_id = document.getElementById('carrier-id').value;
        formData.license_number = document.getElementById('license-number').value;
        formData.vehicle_type = document.getElementById('vehicle-type').value;
        formData.vehicle_number = document.getElementById('vehicle-number').value;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('계정이 성공적으로 생성되었습니다!', 'success');
            showLoginForm();
        } else {
            showAlert(data.error || '계정 생성에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Show sections
function showLoginSection() {
    document.getElementById('login-section').style.display = 'block';
    document.getElementById('register-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'none';
}

function showRegisterSection() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('register-section').style.display = 'block';
    document.getElementById('main-section').style.display = 'none';
    loadCarriers(); // Load carriers for driver registration
}

function showMainSection() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('register-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';
    
    // Update user info
    if (currentUser) {
        document.getElementById('user-info').textContent = `${currentUser.full_name} (${getRoleText(currentUser.role)})`;
        document.getElementById('logout-btn').style.display = 'inline-block';
        console.log('Current user role:', currentUser.role);
    }
    
    setupRoleBasedUI();
    loadDashboard();
    loadTolerances();
    
    // Force admin tab visibility if admin
    if (currentUser && currentUser.role === 'admin') {
        const adminTab = document.getElementById('admin-tab-item');
        if (adminTab) {
            adminTab.style.display = 'block';
            console.log('Admin tab forced to visible');
        }
    }
}

function showLoginForm() {
    showLoginSection();
}

function showRegisterForm() {
    showRegisterSection();
}

// Setup role-based UI
function setupRoleBasedUI() {
    if (!currentUser) return;
    
    const role = currentUser.role;
    
    // Show/hide buttons based on role
    const addToleranceBtn = document.getElementById('add-tolerance-btn');
    const addRequestBtn = document.getElementById('add-request-btn');
    const autoMatchBtn = document.getElementById('auto-match-btn');
    
    if (addToleranceBtn) addToleranceBtn.style.display = role === 'carrier' ? 'inline-block' : 'none';
    if (addRequestBtn) addRequestBtn.style.display = role === 'carrier' ? 'inline-block' : 'none';
    if (autoMatchBtn) autoMatchBtn.style.display = role === 'admin' ? 'inline-block' : 'none';
    
    // Show/hide admin tab
    const adminTab = document.getElementById('admin-tab-item');
    if (adminTab) {
        adminTab.style.display = role === 'admin' ? 'block' : 'none';
        console.log('Admin tab visibility set to:', role === 'admin' ? 'visible' : 'hidden');
    }
    
    // If admin, load admin data
    if (role === 'admin') {
        setTimeout(() => {
            loadAdminStatistics();
        }, 100);
    }
}

// Toggle role-specific fields
function toggleRoleFields() {
    const role = document.getElementById('reg-role').value;
    const carrierFields = document.getElementById('carrier-fields');
    const driverFields = document.getElementById('driver-fields');
    
    if (role === 'carrier') {
        carrierFields.style.display = 'block';
        driverFields.style.display = 'none';
    } else if (role === 'driver') {
        carrierFields.style.display = 'none';
        driverFields.style.display = 'block';
    } else {
        carrierFields.style.display = 'none';
        driverFields.style.display = 'none';
    }
}

// Load dashboard
async function loadDashboard() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        if (response.ok) {
            renderDashboard(data);
        } else {
            showAlert(data.error || '대시보드 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Render dashboard
function renderDashboard(data) {
    const container = document.getElementById('dashboard-content');
    let html = '';
    
    if (currentUser.role === 'admin') {
        html = `
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">총 사용자</h5>
                        <h2 class="text-primary">${data.total_users}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">활성 여유 운송</h5>
                        <h2 class="text-success">${data.active_tolerances}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">대기 중인 요청</h5>
                        <h2 class="text-warning">${data.pending_requests}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">완료된 매칭</h5>
                        <h2 class="text-info">${data.completed_matches}</h2>
                    </div>
                </div>
            </div>
        `;
    } else if (currentUser.role === 'carrier') {
        html = `
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">내 여유 운송</h5>
                        <h2 class="text-primary">${data.my_tolerances}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">내 운송 요청</h5>
                        <h2 class="text-success">${data.my_requests}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">내 매칭</h5>
                        <h2 class="text-info">${data.my_matches}</h2>
                    </div>
                </div>
            </div>
        `;
    } else if (currentUser.role === 'driver') {
        html = `
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">할당된 작업</h5>
                        <h2 class="text-primary">${data.assigned_matches}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">완료된 작업</h5>
                        <h2 class="text-success">${data.completed_matches}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">현재 상태</h5>
                        <h2 class="text-info">${getStatusText(data.current_status)}</h2>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Load tolerances
async function loadTolerances() {
    const res = await fetch('/api/tolerances');
    let tolerances = await res.json();
    if(window.currentUser && window.currentUser.role === 'carrier' && window.currentUser.carrier_id) {
        tolerances = tolerances.filter(t => t.carrier_id == window.currentUser.carrier_id);
    }
    renderTolerances(tolerances);
}

// Render tolerances
function renderTolerances(tolerances) {
    const container = document.getElementById('tolerances-list');
    
    if (tolerances.length === 0) {
        document.getElementById('tolerances-list').innerHTML = '<p class="text-muted">등록된 여유 운송이 없습니다.</p>';
        return;
    }
    
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>운송사</th>
                    <th>출발지</th>
                    <th>도착지</th>
                    <th>출발시간</th>
                    <th>컨테이너</th>
                    <th>가격</th>
                    <th>상태</th>
                    <th>등록일</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    tolerances.forEach(tolerance => {
        html += `
            <tr>
                <td>${tolerance.carrier_name}</td>
                <td>${tolerance.origin}</td>
                <td>${tolerance.destination}</td>
                <td>${formatDateTime(tolerance.departure_time)}</td>
                <td>${tolerance.container_type} × ${tolerance.container_count}</td>
                <td>₩${tolerance.price.toLocaleString()}</td>
                <td><span class="badge ${getStatusBadgeClass(tolerance.status)}">${getStatusText(tolerance.status)}</span></td>
                <td>${formatDateTime(tolerance.created_at)}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Load requests
async function loadRequests() {
    try {
        const response = await fetch('/api/delivery-requests');
        const data = await response.json();
        
        if (response.ok) {
            renderRequests(data);
        } else {
            showAlert(data.error || '운송 요청 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Render requests
function renderRequests(requests) {
    const container = document.getElementById('requests-list');
    
    if (requests.length === 0) {
        container.innerHTML = '<p class="text-muted">등록된 운송 요청이 없습니다.</p>';
        return;
    }
    
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>운송사</th>
                    <th>출발지</th>
                    <th>도착지</th>
                    <th>픽업시간</th>
                    <th>컨테이너</th>
                    <th>예산</th>
                    <th>상태</th>
                    <th>등록일</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    requests.forEach(request => {
        html += `
            <tr>
                <td>${request.carrier_name}</td>
                <td>${request.origin}</td>
                <td>${request.destination}</td>
                <td>${formatDateTime(request.pickup_time)}</td>
                <td>${request.container_type} × ${request.container_count}</td>
                <td>₩${request.budget.toLocaleString()}</td>
                <td><span class="badge ${getStatusBadgeClass(request.status)}">${getStatusText(request.status)}</span></td>
                <td>${formatDateTime(request.created_at)}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Load matches
async function loadMatches() {
    try {
        const response = await fetch('/api/matches');
        const data = await response.json();
        
        if (response.ok) {
            renderMatches(data);
        } else {
            showAlert(data.error || '매칭 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Render matches
function renderMatches(matches) {
    const container = document.getElementById('matches-list');
    
    if (matches.length === 0) {
        container.innerHTML = '<p class="text-muted">매칭된 항목이 없습니다.</p>';
        return;
    }
    
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>여유 운송</th>
                    <th>운송 요청</th>
                    <th>기사</th>
                    <th>상태</th>
                    <th>매칭일</th>
                    <th>작업</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    matches.forEach(match => {
        html += `
            <tr>
                <td>
                    <strong>${match.tolerance.carrier_name}</strong><br>
                    ${match.tolerance.origin} → ${match.tolerance.destination}<br>
                    <small class="text-muted">${formatDateTime(match.tolerance.departure_time)}</small>
                </td>
                <td>
                    <strong>${match.delivery_request.carrier_name}</strong><br>
                    ${match.delivery_request.origin} → ${match.delivery_request.destination}<br>
                    <small class="text-muted">${formatDateTime(match.delivery_request.pickup_time)}</small>
                </td>
                <td>${match.driver.name || '미배정'}<br><small class="text-muted">${match.driver.vehicle_number || ''}</small></td>
                <td><span class="badge ${getStatusBadgeClass(match.status)}">${getStatusText(match.status)}</span></td>
                <td>${formatDateTime(match.created_at)}</td>
                <td>${getMatchActions(match)}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Get match actions
function getMatchActions(match) {
    if (match.status === 'pending') {
        return `
            <button class="btn btn-success btn-sm me-1" onclick="acceptMatch(${match.id})">수락</button>
            <button class="btn btn-danger btn-sm" onclick="rejectMatch(${match.id})">거절</button>
        `;
    }
    return '-';
}

// Load carriers
async function loadCarriers() {
    try {
        const response = await fetch('/api/carriers');
        const data = await response.json();
        
        if (response.ok) {
            const select = document.getElementById('carrier-id-select');
            select.innerHTML = '<option value="">운송사를 선택하세요</option>';
            
            data.forEach(carrier => {
                select.innerHTML += `<option value="${carrier.id}">${carrier.company_name}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading carriers:', error);
    }
}

// Show tolerance form
function showToleranceForm() {
    const modal = new bootstrap.Modal(document.getElementById('toleranceModal'));
    modal.show();
}

// Show request form
function showRequestForm() {
    const modal = new bootstrap.Modal(document.getElementById('requestModal'));
    modal.show();
}

// Submit tolerance
async function submitTolerance() {
    const origin = document.getElementById('tolerance-origin-1').value;
    const destination = document.getElementById('tolerance-destination-1').value;
    const departure = document.getElementById('tolerance-departure-1').value;
    const arrival = document.getElementById('tolerance-arrival-1').value;
    const containerType = document.getElementById('tolerance-container-type-1').value;
    const containerCount = document.getElementById('tolerance-container-count-1').value;
    const price = document.getElementById('tolerance-price-1').value;
    const isEmptyRun = document.getElementById('tolerance-empty-run-1').checked;
    
    const formData = {
        origin: origin,
        destination: destination,
        departure_time: departure,
        arrival_time: arrival,
        container_type: containerType,
        container_count: containerCount,
        price: price,
        is_empty_run: isEmptyRun
    };
    
    try {
        const response = await fetch('/api/tolerances', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('여유 운송이 등록되었습니다!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('toleranceModal')).hide();
            loadTolerances();
        } else {
            showAlert(data.error || '여유 운송 등록에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Submit request
async function submitRequest() {
    const formData = {
        origin: document.getElementById('request-origin').value,
        destination: document.getElementById('request-destination').value,
        pickup_time: document.getElementById('request-pickup').value,
        delivery_time: document.getElementById('request-delivery').value,
        container_type: document.getElementById('request-container-type').value,
        container_count: parseInt(document.getElementById('request-container-count').value),
        budget: parseFloat(document.getElementById('request-budget').value) || 0,
        cargo_details: document.getElementById('request-cargo-details').value
    };
    
    try {
        const response = await fetch('/api/delivery-requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('운송 요청이 등록되었습니다!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('requestModal')).hide();
            loadRequests();
        } else {
            showAlert(data.error || '운송 요청 등록에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Accept match
async function acceptMatch(matchId) {
    try {
        const response = await fetch(`/api/matches/${matchId}/accept`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('매칭이 수락되었습니다!', 'success');
            loadMatches();
        } else {
            showAlert(data.error || '매칭 수락에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Reject match
async function rejectMatch(matchId) {
    const reason = prompt('거절 사유를 입력하세요:');
    if (!reason) return;
    
    try {
        const response = await fetch(`/api/matches/${matchId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reason })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('매칭이 거절되었습니다.', 'success');
            loadMatches();
        } else {
            showAlert(data.error || '매칭 거절에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Auto match
async function autoMatch() {
    try {
        const response = await fetch('/api/auto-match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(data.message, 'success');
            loadMatches();
        } else {
            showAlert(data.error || '자동 매칭에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

// Update location (for drivers)
function updateLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async function(position) {
            const formData = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            };
            
            try {
                const response = await fetch('/api/location/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAlert('위치가 업데이트되었습니다.', 'success');
                } else {
                    showAlert(data.error || '위치 업데이트에 실패했습니다.', 'danger');
                }
            } catch (error) {
                showAlert('서버 오류가 발생했습니다.', 'danger');
            }
        });
    } else {
        showAlert('위치 서비스를 사용할 수 없습니다.', 'warning');
    }
}

// Show alert
function showAlert(message, type) {
    const alertContainer = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Utility functions
function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR');
}

function getRoleText(role) {
    const roleMap = {
        'admin': '관리자',
        'carrier': '운송사',
        'driver': '기사'
    };
    return roleMap[role] || role;
}

function getStatusText(status) {
    const statusMap = {
        'available': '사용 가능',
        'pending': '대기 중',
        'matched': '매칭됨',
        'proposed': '제안됨',
        'accepted': '수락됨',
        'rejected': '거절됨',
        'in_progress': '진행 중',
        'completed': '완료됨',
        'active': '활성'
    };
    return statusMap[status] || status;
}

function getStatusBadgeClass(status) {
    const classMap = {
        'available': 'bg-success',
        'pending': 'bg-warning',
        'matched': 'bg-info',
        'proposed': 'bg-primary',
        'accepted': 'bg-success',
        'rejected': 'bg-danger',
        'in_progress': 'bg-warning',
        'completed': 'bg-success',
        'active': 'bg-success'
    };
    return classMap[status] || 'bg-secondary';
}

// Admin Functions
async function loadAdminStatistics() {
    try {
        const response = await fetch('/api/admin/statistics');
        const data = await response.json();
        
        if (response.ok) {
            renderAdminStatistics(data);
        } else {
            showAlert(data.error || '통계 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

function renderAdminStatistics(data) {
    const container = document.getElementById('admin-statistics');
    
    let html = `
        <div class="row mb-4">
            <div class="col-12">
                <h6>전체 개요</h6>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">총 사용자</h5>
                        <h2 class="text-primary">${data.overview.total_users}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">총 운송사</h5>
                        <h2 class="text-info">${data.overview.total_carriers}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">총 기사</h5>
                        <h2 class="text-warning">${data.overview.total_drivers}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">총 매칭</h5>
                        <h2 class="text-success">${data.overview.total_matches}</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-12">
                <h6>이번 달 활동</h6>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">여유 운송</h5>
                        <h2 class="text-primary">${data.monthly.tolerances}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">운송 요청</h5>
                        <h2 class="text-info">${data.monthly.requests}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">매칭 성공</h5>
                        <h2 class="text-success">${data.monthly.matches}</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6>상태별 여유 운송</h6>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item d-flex justify-content-between">
                                <span>사용 가능</span>
                                <span class="badge bg-success">${data.status_breakdown.tolerances.available || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between">
                                <span>매칭됨</span>
                                <span class="badge bg-info">${data.status_breakdown.tolerances.matched || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between">
                                <span>완료됨</span>
                                <span class="badge bg-success">${data.status_breakdown.tolerances.completed || 0}</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6>상태별 운송 요청</h6>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item d-flex justify-content-between">
                                <span>대기 중</span>
                                <span class="badge bg-warning">${data.status_breakdown.requests.pending || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between">
                                <span>매칭됨</span>
                                <span class="badge bg-info">${data.status_breakdown.requests.matched || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between">
                                <span>운송 중</span>
                                <span class="badge bg-warning">${data.status_breakdown.requests.in_transit || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between">
                                <span>완료됨</span>
                                <span class="badge bg-success">${data.status_breakdown.requests.completed || 0}</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h6>상위 성과 운송사</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>운송사</th>
                                        <th>매칭 수</th>
                                    </tr>
                                </thead>
                                <tbody>
    `;
    
    data.top_carriers.forEach(carrier => {
        html += `
            <tr>
                <td>${carrier.name}</td>
                <td><span class="badge bg-success">${carrier.matches}</span></td>
            </tr>
        `;
    });
    
    html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

async function loadAdminUsers() {
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        
        if (response.ok) {
            renderAdminUsers(data);
        } else {
            showAlert(data.error || '사용자 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

function renderAdminUsers(users) {
    const container = document.getElementById('users-list');
    
    if (users.length === 0) {
        container.innerHTML = '<p class="text-muted">등록된 사용자가 없습니다.</p>';
        return;
    }
    
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>사용자명</th>
                    <th>이메일</th>
                    <th>이름</th>
                    <th>역할</th>
                    <th>전화번호</th>
                    <th>상태</th>
                    <th>가입일</th>
                    <th>작업</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    users.forEach(user => {
        html += `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${user.full_name}</td>
                <td><span class="badge ${getRoleBadgeClass(user.role)}">${getRoleText(user.role)}</span></td>
                <td>${user.phone || '-'}</td>
                <td><span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">${user.is_active ? '활성' : '비활성'}</span></td>
                <td>${formatDateTime(user.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editUser(${user.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${user.role !== 'admin' ? `<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id})">
                        <i class="fas fa-trash"></i>
                    </button>` : ''}
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

async function loadAdminCarriers() {
    try {
        const response = await fetch('/api/admin/carriers');
        const data = await response.json();
        
        if (response.ok) {
            renderAdminCarriers(data);
        } else {
            showAlert(data.error || '운송사 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

function renderAdminCarriers(carriers) {
    const container = document.getElementById('carriers-list');
    
    if (carriers.length === 0) {
        container.innerHTML = '<p class="text-muted">등록된 운송사가 없습니다.</p>';
        return;
    }
    
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>사용자명</th>
                    <th>회사명</th>
                    <th>사업자등록번호</th>
                    <th>담당자</th>
                    <th>주소</th>
                    <th>상태</th>
                    <th>등록일</th>
                    <th>작업</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    carriers.forEach(carrier => {
        html += `
            <tr>
                <td>${carrier.id}</td>
                <td>${carrier.username}</td>
                <td>${carrier.company_name}</td>
                <td>${carrier.business_license || '-'}</td>
                <td>${carrier.contact_person || '-'}</td>
                <td>${carrier.address || '-'}</td>
                <td><span class="badge ${getStatusBadgeClass(carrier.status)}">${getStatusText(carrier.status)}</span></td>
                <td>${formatDateTime(carrier.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editCarrier(${carrier.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteCarrier(${carrier.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

async function loadAdminDrivers() {
    try {
        const response = await fetch('/api/admin/drivers');
        const data = await response.json();
        
        if (response.ok) {
            renderAdminDrivers(data);
        } else {
            showAlert(data.error || '기사 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

function renderAdminDrivers(drivers) {
    const container = document.getElementById('drivers-list');
    
    if (drivers.length === 0) {
        container.innerHTML = '<p class="text-muted">등록된 기사가 없습니다.</p>';
        return;
    }
    
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>사용자명</th>
                    <th>소속 운송사</th>
                    <th>면허번호</th>
                    <th>차량 종류</th>
                    <th>차량 번호</th>
                    <th>상태</th>
                    <th>등록일</th>
                    <th>작업</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    drivers.forEach(driver => {
        html += `
            <tr>
                <td>${driver.id}</td>
                <td>${driver.username}</td>
                <td>${driver.carrier_name}</td>
                <td>${driver.license_number}</td>
                <td>${driver.vehicle_type || '-'}</td>
                <td>${driver.vehicle_number || '-'}</td>
                <td><span class="badge ${getStatusBadgeClass(driver.status)}">${getStatusText(driver.status)}</span></td>
                <td>${formatDateTime(driver.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editDriver(${driver.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDriver(${driver.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

function getRoleBadgeClass(role) {
    const classMap = {
        'admin': 'bg-danger',
        'carrier': 'bg-primary',
        'driver': 'bg-success'
    };
    return classMap[role] || 'bg-secondary';
}

// Admin action functions (placeholders for now)
function editUser(userId) {
    showAlert('사용자 편집 기능은 구현 중입니다.', 'info');
}

function deleteUser(userId) {
    if (confirm('정말로 이 사용자를 삭제하시겠습니까?')) {
        showAlert('사용자 삭제 기능은 구현 중입니다.', 'info');
    }
}

function editCarrier(carrierId) {
    showAlert('운송사 편집 기능은 구현 중입니다.', 'info');
}

function deleteCarrier(carrierId) {
    if (confirm('정말로 이 운송사를 삭제하시겠습니까?')) {
        showAlert('운송사 삭제 기능은 구현 중입니다.', 'info');
    }
}

function editDriver(driverId) {
    showAlert('기사 편집 기능은 구현 중입니다.', 'info');
}

function deleteDriver(driverId) {
    if (confirm('정말로 이 기사를 삭제하시겠습니까?')) {
        showAlert('기사 삭제 기능은 구현 중입니다.', 'info');
    }
}

// Admin 차량 관리 불러오기
async function loadAdminVehicles() {
    try {
        const response = await fetch('/api/admin/vehicles');
        const data = await response.json();
        if (response.ok) {
            renderAdminVehicles(data);
        } else {
            showAlert(data.error || '차량 로드에 실패했습니다.', 'danger');
        }
    } catch (error) {
        showAlert('서버 오류가 발생했습니다.', 'danger');
    }
}

function renderAdminVehicles(vehicles) {
    const container = document.getElementById('vehicles-list');
    if (!vehicles || vehicles.length === 0) {
        container.innerHTML = '<p class="text-muted">등록된 차량이 없습니다.</p>';
        return;
    }
    let html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>운송사</th>
                    <th>차량번호</th>
                    <th>차량종류</th>
                    <th>상태</th>
                    <th>설명</th>
                    <th>등록일</th>
                </tr>
            </thead>
            <tbody>
    `;
    vehicles.forEach(vehicle => {
        html += `
            <tr>
                <td>${vehicle.id}</td>
                <td>${vehicle.carrier_name || '-'}</td>
                <td>${vehicle.vehicle_number}</td>
                <td>${vehicle.vehicle_type}</td>
                <td><span class="badge ${getStatusBadgeClass(vehicle.status)}">${getStatusText(vehicle.status)}</span></td>
                <td>${vehicle.description || '-'}</td>
                <td>${formatDateTime(vehicle.created_at)}</td>
            </tr>
        `;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function onLoginSuccess() {
    document.getElementById('main-section').style.display = '';
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('register-section').style.display = 'none';
    setupRoleBasedUI();
}

function onLogoutOrLoginFail() {
    document.getElementById('main-section').style.display = 'none';
    document.getElementById('login-section').style.display = '';
    document.getElementById('register-section').style.display = 'none';
    document.getElementById('add-tolerance-btn').style.display = 'none';
}