from requests import Session
from orjson import loads
import aiohttp

session = Session()

def get_json(url):
    try:
        response = session.get(url)
        response.raise_for_status()
        return loads(response.content)
    except Exception:
        return 'error'
    
async def get_json_async(session, url):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            content = await response.read()
            return loads(content)
    except Exception:
        return 'error'