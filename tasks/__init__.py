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
    task_scheduler.init_app(app)
    
    # Start scheduler if not in testing mode
    if not app.config.get('TESTING', False):
        task_scheduler.start()

