from flask import Flask, request, jsonify, session, redirect, url_for, render_template as html
from psych import get_psych_sheet, get_comps, get_comp_data
from oauth import get_token, get_user_info
from cache import get_cache
import asyncio


app = Flask(__name__)
app.secret_key = 'vgMKTGYE5rUDUzVAY517TsaJcNSoM57iVHKwwKBjCiU'


#--Oauth--
@app.route('/auth')
def auth():
    code = request.args.get('code')
    url = request.args.get('state')

    if code:
        access_token = get_token(code)

        if access_token:
            session['access_token'] = access_token
            session['logged_in'] = True
            session['pfp'] = get_user_info(access_token, 'thumb_url', avatar=True)
            session['user_id'] = get_user_info(access_token, 'id')
            session['name'] = get_user_info(access_token, 'name')
            session['wca_id'] = get_user_info(access_token, 'wca_id')

        return redirect(url or url_for('home'))

@app.route('/deauth')
def deauth():
    url = request.args.get('url', url_for('home'))

    session.pop('access_token', None)
    session.pop('logged_in', None)
    session.pop('pfp', None)
    session.pop('user_id', None)
    session.pop('name', None)
    session.pop('wca_id', None)

    return redirect(url or url_for('home'))

#--Home-

@app.route('/')
def home():
    return '"Skibidi Toilet Rizzlers" - Leland Pak ❤️'

#--Psych Sheet-

@app.route("/psych_sheet/", methods=["GET", "POST"])
def comps():
    if request.method == "POST":
        comps = get_comps('search', 25, request.form['page'], search=request.form['search'])
        return jsonify(comps)

    if session.get('logged_in', False):
        your_comps = get_comps('user', user_id=session.get('user_id'))
    else:
        your_comps = None

    breadcrumbs = zip(
        ['Home', 'Psych Sheet'],
        [url_for('home'), '']
    )

    return html('comps.html', your_comps=your_comps, breadcrumbs=breadcrumbs)

@app.route("/psych_sheet/<comp>", methods=["GET", "POST"])
def psych_sheet(comp):
    comp_data = get_cache(f'{comp} data', lambda: get_comp_data(comp), 600)
    competitors = comp_data["competitors"]

    if request.method == "POST":
        solves = int(request.form["solves"])
        event = request.form.get('event')

        psych_sheet = asyncio.run(get_psych_sheet(competitors, event, solves))
        return jsonify(psych_sheet)

    name = comp_data["name"]
    short_name = comp_data["short_name"]
    events = comp_data["event_ids"]

    has_regged_competitors = True if competitors else False

    breadcrumbs = zip(
        ['Home', 'Psych Sheet', short_name],
        [url_for('home'), url_for('comps'), '']
    )

    return html('psych.html',
                events=events,
                comp_id=comp, comp_name=name,
                competitors=range(len(competitors)),
                breadcrumbs=breadcrumbs,
                short_name=short_name,
                regged=has_regged_competitors
                )

if __name__ == "__main__":
    app.run(port=8000)