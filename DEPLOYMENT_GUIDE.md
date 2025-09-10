# Media Management Service - Deployment Guide

This guide provides comprehensive instructions for deploying the Media Management Service with proactive measures to prevent common deployment issues.

## 🚀 Quick Deployment Checklist

### Pre-Deployment Validation
```bash
# 1. Run pre-deployment validation
./scripts/pre-deploy-validate.sh

# 2. Validate requirements
python scripts/validate_requirements.py

# 3. Test database connection
python scripts/db_manager.py check
```

### Railway Deployment
```bash
# 1. Connect repository to Railway
# 2. Set environment variables (see .env.example)
# 3. Deploy automatically

# 4. Post-deployment verification
python scripts/post_deploy_verify.py https://your-service.railway.app
```

## 📋 Environment Variables

### Required Variables
```bash
# Service Configuration
SERVICE_NAME=media-service
SERVICE_PORT=8005
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# File Storage
UPLOAD_FOLDER=/app/uploads
MAX_CONTENT_LENGTH=52428800
MAX_IMAGE_SIZE=10485760
MAX_VIDEO_SIZE=52428800
```

### Optional Variables
```bash
# External Services
TELEGIVE_AUTH_URL=https://telegive-auth-production.up.railway.app
TELEGIVE_GIVEAWAY_URL=https://telegive-giveaway-production.up.railway.app

# Performance
REDIS_URL=redis://localhost:6379
RATELIMIT_STORAGE_URL=memory://

# Security
SECURITY_SCAN_ENABLED=false
FLASK_DEBUG=false
```

## 🔧 Proactive Deployment Features

### 1. Pre-Deployment Validation
- **Script**: `scripts/pre-deploy-validate.sh`
- **Purpose**: Validates environment, dependencies, and configuration before deployment
- **Checks**:
  - Python environment
  - Requirements installability
  - Environment variables
  - Flask application structure
  - Database models
  - Health endpoints
  - API routes
  - File upload structure
  - Utility modules
  - Test suite

### 2. Post-Deployment Verification
- **Script**: `scripts/post_deploy_verify.py`
- **Purpose**: Verifies service health after deployment
- **Checks**:
  - Service availability
  - Health endpoints
  - Database connectivity
  - API endpoints
  - File upload capability
  - Performance metrics

### 3. Requirements Validation
- **Script**: `scripts/validate_requirements.py`
- **Purpose**: Validates Python dependencies
- **Features**:
  - Package existence verification
  - Version compatibility checks
  - Security vulnerability detection
  - Installation testing

### 4. Database Management
- **Script**: `scripts/db_manager.py`
- **Purpose**: Database operations and migrations
- **Commands**:
  ```bash
  python scripts/db_manager.py migrate    # Run migrations
  python scripts/db_manager.py check     # Check connection
  python scripts/db_manager.py info      # Schema information
  python scripts/db_manager.py backup    # Backup schema
  ```

### 5. Health Monitoring
- **Module**: `monitoring/health_monitor.py`
- **Purpose**: Comprehensive health monitoring
- **Features**:
  - Service discovery
  - Health status tracking
  - Performance metrics
  - Alert management

### 6. Environment Management
- **Module**: `config/environment.py`
- **Purpose**: Centralized configuration management
- **Features**:
  - Environment-specific settings
  - Service discovery
  - Configuration validation
  - Dynamic engine options

## 🏥 Health Endpoints

### Basic Health Check
```bash
GET /health
```
Returns overall service health status.

### Detailed Health Check
```bash
GET /health/detailed
```
Returns comprehensive health information including:
- Database status
- Storage status
- System metrics
- Configuration details

### Liveness Probe
```bash
GET /health/live
```
Kubernetes liveness probe endpoint.

### Readiness Probe
```bash
GET /health/ready
```
Kubernetes readiness probe endpoint.

## 🔧 Admin Endpoints

### Database Initialization
```bash
POST /admin/init-db
```
Initialize database tables.

### Database Status
```bash
GET /admin/db-status
```
Check database status and table information.

### Service Statistics
```bash
GET /admin/stats
```
Get comprehensive service statistics.

### Cleanup Operations
```bash
POST /admin/cleanup-orphaned
```
Clean up orphaned file records.

### Admin Health Check
```bash
GET /admin/health-check
```
Comprehensive admin health check.

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```bash
# Check database URL
echo $DATABASE_URL

# Test connection
python scripts/db_manager.py check

# Initialize database
curl -X POST https://your-service.railway.app/admin/init-db
```

#### 2. File Upload Issues
```bash
# Check upload folder
ls -la /app/uploads

# Check permissions
ls -la /app/uploads

# Verify configuration
curl https://your-service.railway.app/api/media/upload/status
```

#### 3. Health Check Failures
```bash
# Check detailed health
curl https://your-service.railway.app/health/detailed

# Check admin health
curl https://your-service.railway.app/admin/health-check
```

#### 4. Performance Issues
```bash
# Check system metrics
curl https://your-service.railway.app/health/detailed

# Monitor response times
python scripts/post_deploy_verify.py https://your-service.railway.app
```

### Deployment Validation Failures

#### Requirements Issues
```bash
# Validate requirements
python scripts/validate_requirements.py

# Update outdated packages
pip install -r requirements.txt --upgrade
```

#### Configuration Issues
```bash
# Check environment variables
./scripts/pre-deploy-validate.sh

# Verify .env.example
cat .env.example
```

#### Application Issues
```bash
# Test Flask app import
python -c "from app import create_app; app = create_app('testing')"

# Check syntax
python -m py_compile app.py
```

## 📊 Monitoring and Alerts

### Health Monitoring
The service includes comprehensive health monitoring:
- Automatic service discovery
- Health status tracking
- Performance metrics collection
- Alert management with cooldown

### Metrics Collection
- Response times
- Success rates
- Error rates
- Resource usage

### Alert Conditions
- Service unavailability
- High error rates
- Performance degradation
- Resource exhaustion

## 🔒 Security Measures

### Pre-Deployment Security
- Requirements vulnerability scanning
- Code quality checks
- Configuration validation

### Runtime Security
- Rate limiting
- Input validation
- File type verification
- Security scanning (optional)

### Post-Deployment Security
- Health monitoring
- Error tracking
- Performance monitoring

## 📈 Performance Optimization

### Database Optimization
- Connection pooling
- Query optimization
- Index management

### File Storage Optimization
- Efficient file handling
- Cleanup automation
- Storage monitoring

### Caching
- Redis integration
- Rate limit caching
- Response caching

## 🔄 Continuous Deployment

### Automated Validation
1. Pre-deployment validation
2. Requirements checking
3. Security scanning
4. Test execution

### Deployment Process
1. Code validation
2. Environment setup
3. Database migration
4. Service deployment
5. Post-deployment verification

### Rollback Strategy
1. Health check failures
2. Automatic rollback triggers
3. Manual rollback procedures
4. Data recovery processes

## 📚 Additional Resources

- [API Documentation](README.md#api-endpoints)
- [Configuration Reference](.env.example)
- [Testing Guide](tests/README.md)
- [Development Setup](README.md#development)

## 🆘 Support

For deployment issues:
1. Check this guide
2. Review logs
3. Run diagnostic scripts
4. Contact development team

Remember: Always run pre-deployment validation before deploying to production!

