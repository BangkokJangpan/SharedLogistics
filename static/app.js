// Global variables
let currentUser = null;
let toleranceModal = null;
let requestModal = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    toleranceModal = new bootstrap.Modal(document.getElementById('toleranceModal'));
    requestModal = new bootstrap.Modal(document.getElementById('requestModal'));
    
    // Check if user is logged in
    checkAuthStatus();
    
    // Setup event listeners
    setupEventListeners();
});

// Check authentication status
function checkAuthStatus() {
    // Check if user data is passed from server
    if (typeof user !== 'undefined' && user) {
        currentUser = user;
        showMainSection();
    } else {
        showLoginSection();
    }
}

// Setup event listeners
function setupEventListeners() {
    // Login form
    document.getElementById('login-form').addEventListener('submit', function(e) {
        e.preventDefault();
        login();
    });
    
    // Register form
    document.getElementById('register-form').addEventListener('submit', function(e) {
        e.preventDefault();
        register();
    });
    
    // Role change in registration
    document.getElementById('reg-role').addEventListener('change', function() {
        toggleRoleFields();
    });
    
    // Tab change event
    document.querySelectorAll('#main-tabs button').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const target = event.target.getAttribute('data-bs-target');
            if (target === '#dashboard') {
                loadDashboard();
            } else if (target === '#tolerances') {
                loadTolerances();
            } else if (target === '#requests') {
                loadRequests();
            } else if (target === '#matches') {
                loadMatches();
            }
        });
    });
}

// Login function
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            showMainSection();
            showAlert('로그인 성공', 'success');
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('로그인 중 오류가 발생했습니다', 'danger');
        console.error('Login error:', error);
    }
}

// Register function
async function register() {
    const formData = {
        username: document.getElementById('reg-username').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        full_name: document.getElementById('reg-full-name').value,
        role: document.getElementById('reg-role').value,
        phone: document.getElementById('reg-phone').value
    };
    
    // Add role-specific fields
    if (formData.role === 'carrier') {
        formData.company_name = document.getElementById('reg-company-name').value;
        formData.business_license = document.getElementById('reg-business-license').value;
        formData.address = document.getElementById('reg-address').value;
    } else if (formData.role === 'driver') {
        formData.carrier_id = document.getElementById('reg-carrier-id').value;
        formData.license_number = document.getElementById('reg-license-number').value;
        formData.vehicle_type = document.getElementById('reg-vehicle-type').value;
        formData.vehicle_number = document.getElementById('reg-vehicle-number').value;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(data.message, 'success');
            showLoginForm();
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('등록 중 오류가 발생했습니다', 'danger');
        console.error('Register error:', error);
    }
}

// Show different sections
function showLoginSection() {
    document.getElementById('login-section').classList.remove('hidden');
    document.getElementById('register-section').classList.add('hidden');
    document.getElementById('main-section').classList.add('hidden');
    document.getElementById('user-menu').classList.add('hidden');
}

function showRegisterSection() {
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('register-section').classList.remove('hidden');
    document.getElementById('main-section').classList.add('hidden');
    document.getElementById('user-menu').classList.add('hidden');
    
    // Load carriers for driver registration
    loadCarriers();
}

function showMainSection() {
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('register-section').classList.add('hidden');
    document.getElementById('main-section').classList.remove('hidden');
    document.getElementById('user-menu').classList.remove('hidden');
    
    // Update user info
    document.getElementById('user-name').textContent = currentUser.full_name;
    document.getElementById('user-role').textContent = getRoleText(currentUser.role);
    
    // Show/hide tabs based on role
    setupRoleBasedUI();
    
    // Load dashboard
    loadDashboard();
}

// Form navigation
function showLoginForm() {
    showLoginSection();
}

function showRegisterForm() {
    showRegisterSection();
}

// Role-based UI setup
function setupRoleBasedUI() {
    const roleElements = document.querySelectorAll('.role-admin, .role-carrier, .role-driver');
    
    roleElements.forEach(element => {
        element.classList.add('hidden');
    });
    
    // Show elements for current user role
    const currentRoleElements = document.querySelectorAll(`.role-${currentUser.role}`);
    currentRoleElements.forEach(element => {
        element.classList.remove('hidden');
    });
}

// Toggle role-specific fields in registration
function toggleRoleFields() {
    const role = document.getElementById('reg-role').value;
    
    document.getElementById('carrier-fields').classList.add('hidden');
    document.getElementById('driver-fields').classList.add('hidden');
    
    if (role === 'carrier') {
        document.getElementById('carrier-fields').classList.remove('hidden');
    } else if (role === 'driver') {
        document.getElementById('driver-fields').classList.remove('hidden');
    }
}

// Load dashboard data
async function loadDashboard() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        if (response.ok) {
            renderDashboard(data);
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('대시보드 로드 중 오류가 발생했습니다', 'danger');
        console.error('Dashboard error:', error);
    }
}

// Render dashboard
function renderDashboard(data) {
    const container = document.getElementById('dashboard-stats');
    container.innerHTML = '';
    
    if (currentUser.role === 'admin') {
        container.innerHTML = `
            <div class="col-md-3">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">전체 사용자</h5>
                        <h2 class="text-primary">${data.total_users}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">활성 여유 운송</h5>
                        <h2 class="text-success">${data.active_tolerances}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">대기 중인 요청</h5>
                        <h2 class="text-warning">${data.pending_requests}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">완료된 매칭</h5>
                        <h2 class="text-info">${data.completed_matches}</h2>
                    </div>
                </div>
            </div>
        `;
    } else if (currentUser.role === 'carrier') {
        container.innerHTML = `
            <div class="col-md-4">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">내 여유 운송</h5>
                        <h2 class="text-primary">${data.my_tolerances}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">내 운송 요청</h5>
                        <h2 class="text-success">${data.my_requests}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">내 매칭</h5>
                        <h2 class="text-info">${data.my_matches}</h2>
                    </div>
                </div>
            </div>
        `;
    } else if (currentUser.role === 'driver') {
        container.innerHTML = `
            <div class="col-md-4">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">배정된 운송</h5>
                        <h2 class="text-warning">${data.assigned_matches}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">완료된 운송</h5>
                        <h2 class="text-success">${data.completed_matches}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card dashboard-card">
                    <div class="card-body">
                        <h5 class="card-title">현재 상태</h5>
                        <h2 class="text-info">${getStatusText(data.current_status)}</h2>
                    </div>
                </div>
            </div>
        `;
    }
}

// Load tolerances
async function loadTolerances() {
    try {
        const response = await fetch('/api/tolerances');
        const data = await response.json();
        
        if (response.ok) {
            renderTolerances(data);
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('여유 운송 로드 중 오류가 발생했습니다', 'danger');
        console.error('Tolerances error:', error);
    }
}

// Render tolerances
function renderTolerances(tolerances) {
    const tbody = document.getElementById('tolerances-table');
    tbody.innerHTML = '';
    
    tolerances.forEach(tolerance => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${tolerance.carrier_name}</td>
            <td>${tolerance.origin}</td>
            <td>${tolerance.destination}</td>
            <td>${formatDateTime(tolerance.departure_time)}</td>
            <td>${tolerance.container_type}</td>
            <td>${tolerance.container_count}</td>
            <td>${tolerance.is_empty_run ? '예' : '아니오'}</td>
            <td>${tolerance.price ? tolerance.price.toLocaleString() + ' THB' : '-'}</td>
            <td><span class="badge ${getStatusBadgeClass(tolerance.status)}">${getStatusText(tolerance.status)}</span></td>
        `;
        tbody.appendChild(row);
    });
}

// Load requests
async function loadRequests() {
    try {
        const response = await fetch('/api/delivery-requests');
        const data = await response.json();
        
        if (response.ok) {
            renderRequests(data);
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('운송 요청 로드 중 오류가 발생했습니다', 'danger');
        console.error('Requests error:', error);
    }
}

// Render requests
function renderRequests(requests) {
    const tbody = document.getElementById('requests-table');
    tbody.innerHTML = '';
    
    requests.forEach(request => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${request.carrier_name}</td>
            <td>${request.origin}</td>
            <td>${request.destination}</td>
            <td>${formatDateTime(request.pickup_time)}</td>
            <td>${request.container_type}</td>
            <td>${request.container_count}</td>
            <td>${request.budget ? request.budget.toLocaleString() + ' THB' : '-'}</td>
            <td><span class="badge ${getStatusBadgeClass(request.status)}">${getStatusText(request.status)}</span></td>
        `;
        tbody.appendChild(row);
    });
}

// Load matches
async function loadMatches() {
    try {
        const response = await fetch('/api/matches');
        const data = await response.json();
        
        if (response.ok) {
            renderMatches(data);
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('매칭 로드 중 오류가 발생했습니다', 'danger');
        console.error('Matches error:', error);
    }
}

// Render matches
function renderMatches(matches) {
    const container = document.getElementById('matches-container');
    container.innerHTML = '';
    
    matches.forEach(match => {
        const card = document.createElement('div');
        card.className = 'card mb-3';
        card.innerHTML = `
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <h6>여유 운송</h6>
                        <p class="mb-1"><strong>경로:</strong> ${match.tolerance.origin} → ${match.tolerance.destination}</p>
                        <p class="mb-1"><strong>출발:</strong> ${formatDateTime(match.tolerance.departure_time)}</p>
                        <p class="mb-0"><strong>타입:</strong> ${match.tolerance.container_type}</p>
                    </div>
                    <div class="col-md-4">
                        <h6>운송 요청</h6>
                        <p class="mb-1"><strong>경로:</strong> ${match.request.origin} → ${match.request.destination}</p>
                        <p class="mb-1"><strong>픽업:</strong> ${formatDateTime(match.request.pickup_time)}</p>
                        <p class="mb-0"><strong>타입:</strong> ${match.request.container_type}</p>
                    </div>
                    <div class="col-md-4">
                        <h6>매칭 정보</h6>
                        <p class="mb-1"><strong>기사:</strong> ${match.driver.name || '미배정'}</p>
                        <p class="mb-1"><strong>차량:</strong> ${match.driver.vehicle_number || '미배정'}</p>
                        <p class="mb-1"><strong>상태:</strong> <span class="badge ${getStatusBadgeClass(match.status)}">${getStatusText(match.status)}</span></p>
                        <div class="mt-2">
                            ${getMatchActions(match)}
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// Get match actions based on status and user role
function getMatchActions(match) {
    if (currentUser.role === 'carrier' && match.status === 'proposed') {
        return `
            <button class="btn btn-success btn-sm me-2" onclick="acceptMatch(${match.id})">
                <i class="fas fa-check me-1"></i>수락
            </button>
            <button class="btn btn-danger btn-sm" onclick="rejectMatch(${match.id})">
                <i class="fas fa-times me-1"></i>거절
            </button>
        `;
    } else if (currentUser.role === 'driver' && match.status === 'accepted') {
        return `
            <button class="btn btn-primary btn-sm" onclick="acceptMatch(${match.id})">
                <i class="fas fa-play me-1"></i>운송 시작
            </button>
        `;
    }
    return '';
}

// Load carriers for registration
async function loadCarriers() {
    try {
        const response = await fetch('/api/carriers');
        const data = await response.json();
        
        if (response.ok) {
            const select = document.getElementById('reg-carrier-id');
            select.innerHTML = '<option value="">선택하세요</option>';
            
            data.forEach(carrier => {
                const option = document.createElement('option');
                option.value = carrier.id;
                option.textContent = carrier.company_name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Carriers load error:', error);
    }
}

// Show tolerance form
function showToleranceForm() {
    document.getElementById('tolerance-form').reset();
    toleranceModal.show();
}

// Show request form
function showRequestForm() {
    document.getElementById('request-form').reset();
    requestModal.show();
}

// Submit tolerance
async function submitTolerance() {
    const formData = {
        origin: document.getElementById('tolerance-origin').value,
        destination: document.getElementById('tolerance-destination').value,
        departure_time: document.getElementById('tolerance-departure').value,
        arrival_time: document.getElementById('tolerance-arrival').value,
        container_type: document.getElementById('tolerance-container-type').value,
        container_count: parseInt(document.getElementById('tolerance-count').value),
        price: parseFloat(document.getElementById('tolerance-price').value) || 0,
        is_empty_run: document.getElementById('tolerance-empty').checked
    };
    
    try {
        const response = await fetch('/api/tolerances', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            toleranceModal.hide();
            showAlert(data.message, 'success');
            loadTolerances();
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('여유 운송 등록 중 오류가 발생했습니다', 'danger');
        console.error('Submit tolerance error:', error);
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
        container_count: parseInt(document.getElementById('request-count').value),
        budget: parseFloat(document.getElementById('request-budget').value) || 0,
        cargo_details: {
            type: document.getElementById('request-cargo-type').value,
            weight: parseFloat(document.getElementById('request-cargo-weight').value) || 0
        }
    };
    
    try {
        const response = await fetch('/api/delivery-requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            requestModal.hide();
            showAlert(data.message, 'success');
            loadRequests();
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('운송 요청 등록 중 오류가 발생했습니다', 'danger');
        console.error('Submit request error:', error);
    }
}

// Accept match
async function acceptMatch(matchId) {
    try {
        const response = await fetch(`/api/matches/${matchId}/accept`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(data.message, 'success');
            loadMatches();
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('매칭 수락 중 오류가 발생했습니다', 'danger');
        console.error('Accept match error:', error);
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
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(data.message, 'success');
            loadMatches();
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('매칭 거절 중 오류가 발생했습니다', 'danger');
        console.error('Reject match error:', error);
    }
}

// Auto match (admin only)
async function autoMatch() {
    try {
        const response = await fetch('/api/auto-match', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`${data.matches_created}개의 매칭이 생성되었습니다`, 'success');
            loadMatches();
        } else {
            showAlert(data.error, 'danger');
        }
    } catch (error) {
        showAlert('자동 매칭 중 오류가 발생했습니다', 'danger');
        console.error('Auto match error:', error);
    }
}

// Update location (driver only)
function updateLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            async function(position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                
                try {
                    const response = await fetch('/api/location', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ latitude, longitude })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showAlert(data.message, 'success');
                        document.getElementById('location-status').innerHTML = `
                            <small class="text-success">
                                <i class="fas fa-map-marker-alt me-1"></i>
                                위치 업데이트됨<br>
                                위도: ${latitude.toFixed(6)}<br>
                                경도: ${longitude.toFixed(6)}
                            </small>
                        `;
                    } else {
                        showAlert(data.error, 'danger');
                    }
                } catch (error) {
                    showAlert('위치 업데이트 중 오류가 발생했습니다', 'danger');
                    console.error('Location update error:', error);
                }
            },
            function(error) {
                showAlert('위치 정보를 가져올 수 없습니다', 'danger');
            }
        );
    } else {
        showAlert('이 브라우저는 위치 정보를 지원하지 않습니다', 'danger');
    }
}

// Utility functions
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the container
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

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
        'in_transit': '운송 중',
        'completed': '완료',
        'proposed': '제안됨',
        'accepted': '수락됨',
        'rejected': '거절됨',
        'in_progress': '진행 중',
        'active': '활성'
    };
    return statusMap[status] || status;
}

function getStatusBadgeClass(status) {
    const classMap = {
        'available': 'bg-success',
        'pending': 'bg-warning',
        'matched': 'bg-info',
        'in_transit': 'bg-primary',
        'completed': 'bg-secondary',
        'proposed': 'bg-info',
        'accepted': 'bg-success',
        'rejected': 'bg-danger',
        'in_progress': 'bg-primary',
        'active': 'bg-success'
    };
    return classMap[status] || 'bg-secondary';
}
