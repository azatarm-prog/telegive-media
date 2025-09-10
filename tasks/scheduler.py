import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from flask import current_app

from .cleanup_tasks import cleanup_tasks
from .validation_tasks import validation_tasks

class TaskScheduler:
    """Background task scheduler for media management"""
    
    def __init__(self):
        self.scheduler = None
        self.is_running = False
    
    def init_app(self, app):
        """Initialize scheduler with Flask app"""
        
        # Configure job stores
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config.get('DATABASE_URL'))
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(max_workers=app.config.get('SCHEDULER_MAX_WORKERS', 4))
        }
        
        # Job defaults
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Initialize task instances
        cleanup_tasks.init_app(app)
        validation_tasks.init_app(app)
        
        # Register cleanup on app shutdown
        atexit.register(self.shutdown)
    
    def start(self):
        """Start the scheduler and add jobs"""
        if self.is_running:
            return
        
        try:
            # Add scheduled jobs
            self._add_cleanup_jobs()
            self._add_validation_jobs()
            self._add_maintenance_jobs()
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            # Use print instead of current_app.logger during startup
            print('Task scheduler started successfully')
            
        except Exception as e:
            # Use print instead of current_app.logger during startup
            print(f'Failed to start task scheduler: {e}')
            # Don't raise the exception to prevent deployment failure
            # raise
    
    def _add_cleanup_jobs(self):
        """Add cleanup-related scheduled jobs"""
        
        # Scheduled file cleanup - every 5 minutes
        self.scheduler.add_job(
            func=cleanup_tasks.cleanup_scheduled_files,
            trigger='interval',
            minutes=5,
            id='cleanup_scheduled_files',
            name='Clean up scheduled files',
            replace_existing=True
        )
        
        # Orphaned file cleanup - every 6 hours
        self.scheduler.add_job(
            func=cleanup_tasks.cleanup_orphaned_files,
            trigger='interval',
            hours=6,
            id='cleanup_orphaned_files',
            name='Clean up orphaned files',
            replace_existing=True
        )
        
        # Old inactive file cleanup - daily at 2 AM
        self.scheduler.add_job(
            func=cleanup_tasks.cleanup_old_inactive_files,
            trigger='cron',
            hour=2,
            minute=0,
            id='cleanup_old_inactive_files',
            name='Clean up old inactive files',
            replace_existing=True
        )
    
    def _add_validation_jobs(self):
        """Add validation-related scheduled jobs"""
        
        # Pending file validation - every 2 minutes
        self.scheduler.add_job(
            func=validation_tasks.validate_pending_files,
            trigger='interval',
            minutes=2,
            id='validate_pending_files',
            name='Validate pending files',
            replace_existing=True
        )
        
        # Failed file revalidation - every 30 minutes
        self.scheduler.add_job(
            func=validation_tasks.revalidate_failed_files,
            trigger='interval',
            minutes=30,
            id='revalidate_failed_files',
            name='Revalidate failed files',
            replace_existing=True
        )
    
    def _add_maintenance_jobs(self):
        """Add maintenance-related scheduled jobs"""
        
        # Log cleanup statistics - every hour
        self.scheduler.add_job(
            func=self._log_statistics,
            trigger='interval',
            hours=1,
            id='log_statistics',
            name='Log system statistics',
            replace_existing=True
        )
        
        # Database maintenance - daily at 3 AM
        self.scheduler.add_job(
            func=self._database_maintenance,
            trigger='cron',
            hour=3,
            minute=0,
            id='database_maintenance',
            name='Database maintenance',
            replace_existing=True
        )
    
    def _log_statistics(self):
        """Log system statistics"""
        try:
            # Get cleanup statistics
            cleanup_stats = cleanup_tasks.get_cleanup_statistics()
            if cleanup_stats['success']:
                current_app.logger.info(f'Cleanup stats: {cleanup_stats["statistics"]}')
            
            # Get validation statistics
            validation_stats = validation_tasks.get_validation_statistics()
            if validation_stats['success']:
                current_app.logger.info(f'Validation stats: {validation_stats["statistics"]}')
                
        except Exception as e:
            current_app.logger.error(f'Failed to log statistics: {e}')
    
    def _database_maintenance(self):
        """Perform database maintenance tasks"""
        try:
            from models import db
            
            # Clean up old validation logs (older than 30 days)
            from datetime import datetime, timedelta
            from models import FileValidationLog, FileCleanupLog
            
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Delete old validation logs
            old_validation_logs = FileValidationLog.query.filter(
                FileValidationLog.validated_at < cutoff_date
            ).delete()
            
            # Delete old cleanup logs
            old_cleanup_logs = FileCleanupLog.query.filter(
                FileCleanupLog.cleanup_timestamp < cutoff_date
            ).delete()
            
            db.session.commit()
            
            current_app.logger.info(
                f'Database maintenance completed: {old_validation_logs} validation logs, '
                f'{old_cleanup_logs} cleanup logs removed'
            )
            
        except Exception as e:
            current_app.logger.error(f'Database maintenance failed: {e}')
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            print('Task scheduler stopped')
    
    def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            print('Task scheduler shutdown completed')
    
    def get_job_status(self):
        """Get status of all scheduled jobs"""
        if not self.scheduler:
            return {'error': 'Scheduler not initialized'}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'scheduler_running': self.is_running,
            'jobs': jobs
        }
    
    def run_job_now(self, job_id):
        """Run a specific job immediately"""
        if not self.scheduler:
            return {'success': False, 'error': 'Scheduler not initialized'}
        
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return {'success': False, 'error': f'Job {job_id} not found'}
            
            # Run job immediately
            job.modify(next_run_time=None)
            
            return {'success': True, 'message': f'Job {job_id} scheduled to run immediately'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Global task scheduler instance
task_scheduler = TaskScheduler()

