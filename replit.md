# Laem Chabang Port Shared Logistics System

## Overview

This is a Flask-based web application for a shared logistics system at Laem Chabang Port. The system appears to be designed for managing logistics operations with user authentication, role-based access control, and real-time features. The application supports multiple user roles (admin, carrier, driver) and includes features for tracking, requests, and dashboard management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with PostgreSQL as the primary database
- **Authentication**: JWT (JSON Web Tokens) for session management with bcrypt for password hashing
- **Session Management**: Flask sessions with server-side secret key
- **Deployment**: WSGI-compatible with ProxyFix middleware for reverse proxy support

### Frontend Architecture
- **Framework**: Vanilla JavaScript with Bootstrap 5.1.3 for UI components
- **Styling**: Bootstrap CSS with Font Awesome icons
- **Architecture Pattern**: Single Page Application (SPA) with dynamic content loading
- **State Management**: Client-side JavaScript with global variables for user state

### Database Schema
The application uses a User model with the following structure:
- User roles: admin, carrier, driver
- Authentication fields: username, email, password_hash
- Profile information: full_name, phone, is_active status
- Timestamps: created_at for user registration tracking

## Key Components

### Authentication System
- **JWT Implementation**: Custom JWT handling with configurable expiration (24 hours default)
- **Role-Based Access**: Three-tier user system (admin, carrier, driver)
- **Password Security**: bcrypt hashing for secure password storage
- **Session Management**: Flask sessions combined with JWT for stateful authentication

### User Interface
- **Responsive Design**: Bootstrap-based responsive layout
- **Modal System**: Bootstrap modals for tolerance and request management
- **Tab Navigation**: Multi-tab interface for different system sections
- **Real-time Updates**: JavaScript-based dynamic content updates

### Database Layer
- **ORM**: SQLAlchemy with DeclarativeBase for modern Python database operations
- **Connection Management**: Connection pooling with pre-ping and recycle configuration
- **Migration Support**: SQLAlchemy model definitions ready for Alembic migrations

## Data Flow

1. **User Authentication**: Client submits credentials → Flask validates → JWT generated → Client stores token
2. **Role-Based Access**: Each request includes role verification → Content filtered by user permissions
3. **Data Operations**: Client requests → Flask routes → SQLAlchemy ORM → PostgreSQL database
4. **Real-time Updates**: JavaScript polls server → JSON responses → DOM updates

## External Dependencies

### Backend Dependencies
- Flask ecosystem (Flask, Flask-SQLAlchemy)
- JWT handling (PyJWT)
- Password hashing (bcrypt)
- Database connectivity (psycopg2 for PostgreSQL)

### Frontend Dependencies
- Bootstrap 5.1.3 (UI framework)
- Font Awesome 6.0.0 (icon library)
- Native JavaScript (no additional frameworks)

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session encryption key
- `JWT_SECRET_KEY`: JWT token signing key

## Deployment Strategy

### Production Configuration
- **Reverse Proxy Support**: ProxyFix middleware configured for deployment behind nginx/Apache
- **Environment-Based Config**: All sensitive configuration via environment variables
- **Database Connection**: Production-ready PostgreSQL with connection pooling
- **Security**: Configurable secret keys and JWT expiration

### Development Setup
- **Local Database**: Falls back to local PostgreSQL instance
- **Debug Mode**: Logging configured for development debugging
- **Hot Reload**: Standard Flask development server support

### Infrastructure Requirements
- **Database**: PostgreSQL server with connection pooling support
- **Web Server**: WSGI-compatible server (Gunicorn, uWSGI)
- **Reverse Proxy**: Nginx or Apache for static file serving and SSL termination
- **Environment**: Python 3.x environment with pip package management

The system is designed for scalability with proper database connection management and stateless JWT authentication, making it suitable for containerized deployment or traditional server environments.