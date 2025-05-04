import time

caches = {}

def save_cache(name, value, expiration=600):
    expiry_time = time.time() + expiration
    caches[name] = (value, expiry_time)

def cache(name, func, expiration=600):
    if name in caches:
        value, expiry_time = caches[name]
        if time.time() < expiry_time:
            return value
        else: #Expired
            del caches[name]

    value = func()
    save_cache(name, value, expiration)
    return value
            