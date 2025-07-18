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
    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        return loads(response.content).get("access_token")
    except Exception:
        return
    
def get_user_info(token):
    user_data = get_json(f'https://api.worldcubeassociation.org/me?access_token={token}')

    if user_data == 'error':
        return
    
    user_data = user_data.get('me')
    if not user_data:
        return
    
    '''session['access_token'] = access_token
    session['logged_in'] = True
    session['pfp'] = get_user_info(access_token, 'thumb_url', avatar=True)
    session['user_id'] = get_user_info(access_token, 'id')
    session['name'] = get_user_info(access_token, 'name')
    session['wca_id'] = get_user_info(access_token, 'wca_id')'''

    pfp = user_data['avatar']['thumb_url']

    if not pfp or 'missing_avatar_thumb' in pfp:
        pfp = 'no pfp'

    return {
        "pfp": pfp,
        "user_id": user_data['id'],
        "wca_id": user_data['wca_id']
    }