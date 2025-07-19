from requests import post
from orjson import loads
from json_request import get_json

REDIRECT_URI = 'https://psych-sheet.vercel.app/auth'
CLIENT_ID = 'bes-w8tmmAylNkgxN-2OcvrRdOR-m5ooQ9ktrX6zaqs'
CLIENT_SECRET = 'z78nXhWnFKVuzY66aYS6nVSKSiayJPkTdtdqordWCkU' #Remove later
TOKEN_URL = "https://www.worldcubeassociation.org/oauth/token"

def get_access_token(code):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        response = post(TOKEN_URL, data=data)
        response.raise_for_status()
        return loads(response.content).get("access_token")
    except Exception:
        return
    
def get_user_data(token):
    user_profile = get_json(f'https://api.worldcubeassociation.org/me?access_token={token}')

    if user_profile == 'error':
        return
    
    user_data = user_profile.get('me')

    if not user_data:
        return

    pfp = user_data['avatar']['thumb_url']
    pfp = pfp if pfp and 'missing_avatar_thumb' not in pfp else 'no pfp'

    return {
        "pfp": pfp,
        "user_id": user_data['id'],
        "wca_id": user_data['wca_id']
    }