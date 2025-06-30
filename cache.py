from time import monotonic as now
from threading import Lock

caches = {}
cache_lock = Lock()

def save_cache(name, value, expiration=600):
    expiry_time = now() + expiration

    with cache_lock:
        caches[name] = (value, expiry_time)

def get_cache(name, func, expiration=600):
    with cache_lock:
        if name in caches:
            value, expiry_time = caches[name]
            if now() < expiry_time:
                return value
            else: #Expired
                del caches[name]

    value = func()
    save_cache(name, value, expiration)
    return value