from requests import Session
from orjson import loads

session = Session()

def get_json(url):
    response = session.get(url)

    if response.status_code != 200:
        return 'error'
    
    return loads(response.content)