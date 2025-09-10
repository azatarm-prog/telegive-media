# Tasks package initialization

from .cleanup_tasks import cleanup_tasks
from .validation_tasks import validation_tasks
from .scheduler import task_scheduler

# Export all task instances
__all__ = [
    'cleanup_tasks',
    'validation_tasks',
    'task_scheduler'
]

def init_tasks(app):
    """Initialize all tasks with Flask app"""
    
    # Only initialize scheduler if enabled (disabled by default in production)
    scheduler_enabled = app.config.get('SCHEDULER_ENABLED', False)
    testing_mode = app.config.get('TESTING', False)
    
    if not testing_mode and scheduler_enabled:
        try:
            task_scheduler.init_app(app)
            
            # Start scheduler in a separate thread to avoid blocking
            import threading
            def start_scheduler():
                try:
                    with app.app_context():
                        task_scheduler.start()
                except Exception as e:
                    print(f'Failed to start task scheduler: {e}')
            
            scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
            scheduler_thread.start()
            
            print('Task scheduler initialization started')
        except Exception as e:
            print(f'Failed to initialize task scheduler: {e}')
    else:
        if testing_mode:
            print('Task scheduler disabled (testing mode)')
        else:
            print('Task scheduler disabled (SCHEDULER_ENABLED=false)')

