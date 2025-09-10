#!/usr/bin/env python3
"""
Post-deployment verification script for Media Management Service
"""

import requests
import time
import sys
import os
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostDeploymentVerifier:
    """Verify service health after deployment"""
    
    def __init__(self, service_url: str, timeout: int = 300):
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = 10
    
    def wait_for_service(self) -> bool:
        """Wait for service to become available"""
        logger.info(f"⏳ Waiting for service to become available: {self.service_url}")
        
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                response = self.session.get(f"{self.service_url}/health")
                if response.status_code in [200, 503]:  # 503 is acceptable during startup
                    logger.info("✅ Service is responding")
                    return True
            except Exception as e:
                logger.debug(f"Service not ready: {e}")
            
            time.sleep(10)
        
        logger.error(f"❌ Service did not become available within {self.timeout} seconds")
        return False
    
    def check_health_endpoints(self) -> bool:
        """Check all health endpoints"""
        logger.info("🏥 Checking health endpoints...")
        
        endpoints = [
            ('/health', 'Basic health check'),
            ('/health/detailed', 'Detailed health check')
        ]
        
        for endpoint, description in endpoints:
            try:
                response = self.session.get(f"{self.service_url}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'healthy':
                        logger.info(f"✅ {description}: healthy")
                    else:
                        logger.warning(f"⚠️  {description}: {data.get('status', 'unknown')}")
                elif response.status_code == 503:
                    logger.warning(f"⚠️  {description}: service unavailable (startup)")
                else:
                    logger.error(f"❌ {description}: HTTP {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ {description} failed: {e}")
                return False
        
        return True
    
    def check_api_endpoints(self) -> bool:
        """Check critical API endpoints"""
        logger.info("🛣️  Checking API endpoints...")
        
        endpoints = [
            ('/api/media/', 'GET', 'Media service index'),
            ('/api/media/upload/status', 'GET', 'Upload status')
        ]
        
        for endpoint, method, description in endpoints:
            try:
                if method == 'GET':
                    response = self.session.get(f"{self.service_url}{endpoint}")
                else:
                    response = self.session.request(method, f"{self.service_url}{endpoint}")
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get('success'):
                        logger.info(f"✅ {description}: working")
                    else:
                        logger.warning(f"⚠️  {description}: {data.get('error', 'unknown error')}")
                else:
                    logger.error(f"❌ {description}: HTTP {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ {description} failed: {e}")
                return False
        
        return True
    
    def check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        logger.info("🗄️  Checking database connectivity...")
        
        try:
            response = self.session.get(f"{self.service_url}/health/detailed")
            
            if response.status_code == 200:
                data = response.json()
                checks = data.get('checks', {})
                
                if checks.get('database') == 'connected':
                    logger.info("✅ Database connectivity: healthy")
                    return True
                else:
                    logger.error(f"❌ Database connectivity: {checks.get('database', 'unknown')}")
                    return False
            else:
                logger.error(f"❌ Database check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database check failed: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Initialize database if needed"""
        logger.info("🔧 Initializing database...")
        
        try:
            # First check if database is already initialized
            response = self.session.get(f"{self.service_url}/health/detailed")
            if response.status_code == 200:
                data = response.json()
                if data.get('checks', {}).get('database') == 'connected':
                    logger.info("✅ Database already initialized")
                    return True
            
            # Try to initialize
            response = self.session.post(f"{self.service_url}/admin/init-db")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info("✅ Database initialized successfully")
                    return True
                else:
                    logger.error(f"❌ Database initialization failed: {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ Database initialization request failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def check_file_upload_capability(self) -> bool:
        """Check file upload capability (without actually uploading)"""
        logger.info("📁 Checking file upload capability...")
        
        try:
            # Check upload status endpoint
            response = self.session.get(f"{self.service_url}/api/media/upload/status")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    config = data.get('upload_config', {})
                    logger.info(f"✅ Upload capability: max size {config.get('max_file_size', 'unknown')}")
                    return True
                else:
                    logger.error(f"❌ Upload capability check failed: {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ Upload capability check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Upload capability check failed: {e}")
            return False
    
    def check_service_performance(self) -> bool:
        """Check service performance metrics"""
        logger.info("⚡ Checking service performance...")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.service_url}/health")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                if response_time < 2.0:
                    logger.info(f"✅ Response time: {response_time:.2f}s (good)")
                elif response_time < 5.0:
                    logger.warning(f"⚠️  Response time: {response_time:.2f}s (acceptable)")
                else:
                    logger.warning(f"⚠️  Response time: {response_time:.2f}s (slow)")
                
                return True
            else:
                logger.error(f"❌ Performance check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Performance check failed: {e}")
            return False
    
    def run_full_verification(self) -> bool:
        """Run complete post-deployment verification"""
        logger.info("🚀 Starting post-deployment verification...")
        
        checks = [
            ("Service Availability", self.wait_for_service),
            ("Health Endpoints", self.check_health_endpoints),
            ("Database Initialization", self.initialize_database),
            ("Database Connectivity", self.check_database_connectivity),
            ("API Endpoints", self.check_api_endpoints),
            ("File Upload Capability", self.check_file_upload_capability),
            ("Service Performance", self.check_service_performance)
        ]
        
        failed_checks = []
        
        for check_name, check_func in checks:
            logger.info(f"\n📋 Running check: {check_name}")
            try:
                if not check_func():
                    failed_checks.append(check_name)
            except Exception as e:
                logger.error(f"❌ {check_name} failed with exception: {e}")
                failed_checks.append(check_name)
        
        # Summary
        logger.info("\n📊 Verification Summary:")
        logger.info(f"   Total checks: {len(checks)}")
        logger.info(f"   Passed: {len(checks) - len(failed_checks)}")
        logger.info(f"   Failed: {len(failed_checks)}")
        
        if failed_checks:
            logger.error("\n❌ Failed checks:")
            for check in failed_checks:
                logger.error(f"   - {check}")
            return False
        else:
            logger.info("\n🎉 All verification checks passed!")
            return True

def main():
    """Main verification process"""
    service_url = os.getenv('SERVICE_URL')
    
    if not service_url:
        if len(sys.argv) > 1:
            service_url = sys.argv[1]
        else:
            logger.error("❌ SERVICE_URL environment variable or command line argument required")
            logger.info("Usage: python post_deploy_verify.py <service_url>")
            sys.exit(1)
    
    # Remove trailing slash
    service_url = service_url.rstrip('/')
    
    logger.info(f"🎯 Target service: {service_url}")
    
    verifier = PostDeploymentVerifier(service_url)
    
    if verifier.run_full_verification():
        logger.info("✅ Post-deployment verification completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Post-deployment verification failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()

