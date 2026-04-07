from .base import *  # noqa: F403,F401
from .base import env_bool

DEBUG = False

# SSL settings — disable via DISABLE_SSL=True for droplets behind plain HTTP
# (e.g., initial DigitalOcean setup before configuring nginx/TLS)
_ssl_enabled = not env_bool("DISABLE_SSL", False)
SECURE_SSL_REDIRECT = _ssl_enabled
SESSION_COOKIE_SECURE = _ssl_enabled
CSRF_COOKIE_SECURE = _ssl_enabled
if _ssl_enabled:
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}
