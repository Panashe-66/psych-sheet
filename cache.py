from time import monotonic as now
from threading import Lock

DEFAULT_CACHE_EXPIRATION = 600

caches = {}
cache_lock = Lock()

def save_cache(key, value, expiration=DEFAULT_CACHE_EXPIRATION):
    if not value:
        return
    
    expiry_time = now() + expiration

    with cache_lock:
        caches[key] = (value, expiry_time)

def get_cache(key, func, expiration=DEFAULT_CACHE_EXPIRATION):
    with cache_lock:
        if key in caches:
            value, expiry_time = caches[key]
            if now() < expiry_time:
                return value
            else: #Expired
                del caches[key]

    value = func()
    save_cache(key, value, expiration)
    return value