from time import time

caches = {}

def save_cache(name, value, expiration=600):
    expiry_time = time() + expiration
    caches[name] = (value, expiry_time)

def get_cache(name, func, expiration=600):
    if name in caches:
        value, expiry_time = caches[name]
        if time() < expiry_time:
            return value
        else: #Expired
            del caches[name]

    value = func()
    save_cache(name, value, expiration)
    return value

def extend_cache(name, value, expiration):
    if name in caches:
        old_value, _ = caches[name]
        value = old_value + value

    save_cache(name, value, expiration)