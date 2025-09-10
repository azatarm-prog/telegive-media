"""
Health monitoring system for Media Management Service
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class HealthMetric:
    timestamp: datetime
    service_name: str
    endpoint: str
    status_code: int
    response_time: float
    healthy: bool
    error: Optional[str] = None

@dataclass
class ServiceHealth:
    name: str
    url: str
    last_check: datetime
    healthy: bool
    consecutive_failures: int
    total_checks: int
    success_rate: float
    avg_response_time: float
    last_error: Optional[str] = None

class HealthMonitor:
    """Comprehensive health monitoring for all services"""
    
    def __init__(self, services: Dict[str, str], check_interval: int = 30):
        self.services = services  # {name: url}
        self.check_interval = check_interval
        self.metrics: List[HealthMetric] = []
        self.service_status: Dict[str, ServiceHealth] = {}
        self.alerts_sent: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=15)
        
        self._running = False
        self._thread = None
        
        # Initialize service status
        for name, url in services.items():
            self.service_status[name] = ServiceHealth(
                name=name,
                url=url,
                last_check=datetime.utcnow(),
                healthy=False,
                consecutive_failures=0,
                total_checks=0,
                success_rate=0.0,
                avg_response_time=0.0
            )
    
    def start_monitoring(self):
        """Start background health monitoring"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            self.check_all_services()
            self._cleanup_old_metrics()
            time.sleep(self.check_interval)
    
    def check_service_health(self, service_name: str) -> HealthMetric:
        """Check health of a specific service"""
        service_url = self.services.get(service_name)
        if not service_url:
            return HealthMetric(
                timestamp=datetime.utcnow(),
                service_name=service_name,
                endpoint="unknown",
                status_code=0,
                response_time=0.0,
                healthy=False,
                error="Service URL not configured"
            )
        
        start_time = time.time()
        endpoint = f"{service_url}/health"
        
        try:
            response = requests.get(endpoint, timeout=10)
            response_time = time.time() - start_time
            
            healthy = response.status_code == 200
            error = None if healthy else f"HTTP {response.status_code}"
            
            metric = HealthMetric(
                timestamp=datetime.utcnow(),
                service_name=service_name,
                endpoint=endpoint,
                status_code=response.status_code,
                response_time=response_time,
                healthy=healthy,
                error=error
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            metric = HealthMetric(
                timestamp=datetime.utcnow(),
                service_name=service_name,
                endpoint=endpoint,
                status_code=0,
                response_time=response_time,
                healthy=False,
                error=str(e)
            )
        
        # Update service status
        self._update_service_status(service_name, metric)
        
        # Store metric
        self.metrics.append(metric)
        
        return metric
    
    def _update_service_status(self, service_name: str, metric: HealthMetric):
        """Update service status based on health check result"""
        status = self.service_status[service_name]
        
        status.last_check = metric.timestamp
        status.total_checks += 1
        
        if metric.healthy:
            status.healthy = True
            status.consecutive_failures = 0
            status.last_error = None
        else:
            status.healthy = False
            status.consecutive_failures += 1
            status.last_error = metric.error
        
        # Calculate success rate (last 100 checks)
        recent_metrics = [m for m in self.metrics 
                         if m.service_name == service_name 
                         and m.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        if recent_metrics:
            successful_checks = sum(1 for m in recent_metrics if m.healthy)
            status.success_rate = successful_checks / len(recent_metrics)
            
            # Calculate average response time
            response_times = [m.response_time for m in recent_metrics if m.healthy]
            status.avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
    
    def check_all_services(self):
        """Check health of all services"""
        for service_name in self.services:
            try:
                self.check_service_health(service_name)
            except Exception as e:
                logger.error(f"Failed to check health of {service_name}: {e}")
    
    def _cleanup_old_metrics(self):
        """Remove old metrics to prevent memory growth"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
    
    def get_service_status(self, service_name: str) -> Optional[ServiceHealth]:
        """Get current status of a service"""
        return self.service_status.get(service_name)
    
    def get_all_statuses(self) -> Dict[str, ServiceHealth]:
        """Get status of all services"""
        return self.service_status.copy()
    
    def get_healthy_services(self) -> List[str]:
        """Get list of healthy service names"""
        return [name for name, status in self.service_status.items() if status.healthy]
    
    def get_unhealthy_services(self) -> List[str]:
        """Get list of unhealthy service names"""
        return [name for name, status in self.service_status.items() if not status.healthy]
    
    def get_health_summary(self) -> Dict:
        """Get comprehensive health summary"""
        healthy_services = self.get_healthy_services()
        unhealthy_services = self.get_unhealthy_services()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy' if len(unhealthy_services) == 0 else 'degraded',
            'total_services': len(self.services),
            'healthy_services': len(healthy_services),
            'unhealthy_services': len(unhealthy_services),
            'services': {
                name: {
                    'healthy': status.healthy,
                    'success_rate': status.success_rate,
                    'avg_response_time': status.avg_response_time,
                    'consecutive_failures': status.consecutive_failures,
                    'last_check': status.last_check.isoformat(),
                    'last_error': status.last_error
                }
                for name, status in self.service_status.items()
            }
        }
    
    def get_metrics_for_service(self, service_name: str, hours: int = 1) -> List[HealthMetric]:
        """Get recent metrics for a specific service"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [m for m in self.metrics 
                if m.service_name == service_name and m.timestamp > cutoff_time]
    
    def export_metrics(self, filename: str):
        """Export metrics to JSON file"""
        try:
            metrics_data = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'metrics': [asdict(m) for m in self.metrics],
                'service_status': {
                    name: asdict(status) for name, status in self.service_status.items()
                }
            }
            
            # Convert datetime objects to strings
            for metric in metrics_data['metrics']:
                metric['timestamp'] = metric['timestamp'].isoformat()
            
            for status in metrics_data['service_status'].values():
                status['last_check'] = status['last_check'].isoformat()
            
            with open(filename, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            logger.info(f"Metrics exported to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

class SelfHealthMonitor:
    """Monitor health of the current service"""
    
    def __init__(self, app):
        self.app = app
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
    
    def record_request(self):
        """Record a successful request"""
        self.request_count += 1
    
    def record_error(self, error: str):
        """Record an error"""
        self.error_count += 1
        self.last_error = error
    
    def get_health_status(self) -> Dict:
        """Get current health status"""
        uptime = datetime.utcnow() - self.start_time
        error_rate = self.error_count / max(self.request_count, 1)
        
        return {
            'status': 'healthy' if error_rate < 0.1 else 'degraded',
            'uptime_seconds': uptime.total_seconds(),
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': error_rate,
            'last_error': self.last_error,
            'memory_usage': self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict:
        """Get memory usage information"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent()
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': str(e)}

# Global instances
health_monitor = None
self_health_monitor = None

def initialize_health_monitoring(services: Dict[str, str], app=None):
    """Initialize health monitoring"""
    global health_monitor, self_health_monitor
    
    health_monitor = HealthMonitor(services)
    health_monitor.start_monitoring()
    
    if app:
        self_health_monitor = SelfHealthMonitor(app)
    
    logger.info("Health monitoring initialized")
    return health_monitor, self_health_monitor

