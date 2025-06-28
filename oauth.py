import requests
from orjson import loads
from json_request import get_json

REDIRECT_URI = 'https://psych-sheet.vercel.app/auth'
CLIENT_ID = 'bes-w8tmmAylNkgxN-2OcvrRdOR-m5ooQ9ktrX6zaqs'
CLIENT_SECRET = 'z78nXhWnFKVuzY66aYS6nVSKSiayJPkTdtdqordWCkU'
TOKEN_URL = "https://www.worldcubeassociation.org/oauth/token"

def get_token(code):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(TOKEN_URL, data=data)
    
    if response.status_code != 200:
        return
    
    access_token = loads(response.content).get("access_token")

    return access_token
    
def get_user_info(token, info, avatar=False):
    user_data = get_json(f'https://api.worldcubeassociation.org/me?access_token={token}')

    if user_data == 'error':
        return
    
    user_data = user_data.get('me')

    if avatar:
        pfp = user_data.get('avatar', {}).get(info)

        if 'missing_avatar_thumb' in pfp:
            return 'no pfp'
        
        return pfp
    else:
        return user_data.get(info)