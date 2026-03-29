from .base import *  # noqa: F403,F401

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Always run Celery tasks synchronously in tests — prevents tasks
# dispatching to Redis and never completing during captureOnCommitCallbacks
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
