from flask import Flask, request, jsonify, Response, session, redirect, url_for, render_template as html
from secrets import token_urlsafe as secret_key
from psych import get_psych_sheet, get_comps, get_comp_info, get_competitors, utc_now, remove_comp_duplicates, EVENT_SETTINGS_DATA
from oauth import get_token, get_user_info
from cache import get_cache, save_cache, extend_cache


app = Flask(__name__)
app.secret_key = '123abcpspsych'


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

        return redirect(url or url_for('home'))

@app.route('/deauth')
def deauth():
    url = request.args.get('url', url_for('home'))

    session.pop('access_token', None)
    session.pop('logged_in', None)
    session.pop('pfp', None)
    session.pop('user_id', None)
    session.pop('name', None)

    return redirect(url or url_for('home'))

#--Home-

@app.route('/')
def home():
    return '"Skibidi Toilet Rizzlers" - Leland Pak ❤️'

#--Psych Sheet-

@app.route("/psych_sheet/", methods=["GET", "POST"])
def comps():
    now = get_cache('utc_now', lambda: utc_now(), 600)

    if request.method == "POST":
        searched_comps = get_comps('search', 25, request.form['page'], search=request.form['search'], now=now)

        return jsonify(searched_comps)
    
    logged_in = session.get('logged_in', False)

    if logged_in:
        your_comps = get_comps('user', user_id=session.get('user_id'), now=now)
    else:
        your_comps = None

    breadcrumbs = zip(
        ['Home', 'Psych Sheet'],
        [url_for('home'), '']
    )

    return html('comps.html', your_comps=your_comps, breadcrumbs=breadcrumbs)

@app.route("/psych_sheet/<comp>", methods=["GET", "POST"])
def psych_sheet(comp):
    if request.method == "POST":
        competitors = get_cache(f'{comp} competitors', lambda: get_competitors(comp), 600)

        solves = int(request.form["solves"])
        event = request.form.get('event')

        psych_sheet = get_psych_sheet(competitors, event, solves)

        return jsonify(psych_sheet)

    competitors = get_cache(f'{comp} competitors', lambda: get_competitors(comp), 600)

    name, short_name, events = get_comp_info(comp)

    breadcrumbs = zip(
        ['Home', 'Psych Sheet', short_name],
        [url_for('home'), url_for('comps'), '']
    )

    return html('psych.html',
                            psych_sheet=None,
                            events=events,
                            all_events=EVENT_SETTINGS_DATA,
                            comp_id=comp, comp_name=name,
                            competitors=range(len(competitors)),
                            breadcrumbs=breadcrumbs,
                            short_name=short_name
                        )


if __name__ == "__main__":
    app.run(port=8000)