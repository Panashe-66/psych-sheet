import requests

REDIRECT_URI = 'https://flask-ry9l.onrender.com/auth'
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
    
    if response.status_code == 200:
        access_token = response.json().get("access_token")

        return access_token
    else:
        return None
    

def get_user_info(token, info, avatar=False):
    url = f'https://api.worldcubeassociation.org/me?access_token={token}'

    response = requests.get(url)

    if response.status_code != 200:
        return

    data = response.json().get('me')

    if avatar:
        info = data.get('avatar').get(info)
    else:
        info = data.get(info)

    return info
