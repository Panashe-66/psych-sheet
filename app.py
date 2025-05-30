from flask import Flask, request, render_template as html, session as cookie, redirect, url_for, jsonify
from secrets import token_urlsafe as secret_key
from psych import get_psych_sheet, get_comps, get_comp_info, get_competitors, utc_now, comps_duplicate_lock, EVENT_SETTINGS_DATA
from oauth import get_token, get_user_info
from cache import get_cache, save_cache, extend_cache

app = Flask(__name__)
app.secret_key = secret_key(32)

#--Oauth--

@app.route('/auth')
def auth():
    code = request.args.get('code')
    url = request.args.get('state')

    if code:
        access_token = get_token(code)

        if access_token:
            cookie['access_token'] = access_token
            cookie['logged_in'] = True
            cookie['pfp'] = get_user_info(access_token, 'thumb_url', avatar=True)
            cookie['user_id'] = get_user_info(access_token, 'id')
            cookie['name'] = get_user_info(access_token, 'name')

        return redirect(url or url_for('home'))

@app.route('/deauth')
def deauth():
    url = request.args.get('url', url_for('home'))

    cookie.pop('access_token', None)
    cookie.pop('logged_in', None)
    cookie.pop('pfp', None)
    cookie.pop('user_id', None)
    cookie.pop('name', None)

    return redirect(url or url_for('home'))

#--Home-

@app.route('/')
def home():
    return '"Skibidi Toilet Rizzlers" - Leland Pak ❤️'

#--Psych Sheet-

@app.route("/psych_sheet/", methods=["GET", "POST"])
def comps():
    if request.method == "POST":
        now = get_cache('utc_now', lambda: utc_now(), 600)

        if request.form['type'] == 's':
            searched_comps = get_comps('search', 25, request.form['page'], search=request.form['search'], now=now)

            return jsonify(searched_comps)
        
        elif request.form['type'] == 'm':
            with comps_duplicate_lock():
                if get_cache('comps_done', lambda: False, 600) == False:
                    page = int(request.form.get("page", 2))

                    upcoming_comps = get_comps('upcoming', 25, page, now=now)
                    extend_cache('upcoming_comps', upcoming_comps, 600)
                    save_cache('comps_page', page + 1, 600)

                    if upcoming_comps == []:
                        save_cache('comps_done', True, 600)
                else:
                    upcoming_comps = []

            return jsonify(upcoming_comps)
    
    logged_in = cookie.get('logged_in', False)

    now = get_cache('utc_now', lambda: utc_now(), 600)
    
    if logged_in:
        your_comps = get_comps('user', user_id=cookie.get('user_id'), now=now)
    else:
        your_comps = None

    ongoing_comps = get_cache('ongoing_comps', lambda: get_comps('ongoing', now=now), 600)
    upcoming_comps = get_cache('upcoming_comps', lambda: get_comps('upcoming', 25, 1, now=now), 600)

    page = get_cache('comps_page', lambda: 2, 600)

    breadcrumbs = zip(
        ['Home', 'Psych Sheet'],
        [url_for('home'), '']
    )

    return html('comps.html',
                            comps={'your': your_comps, 'ongoing': ongoing_comps, 'upcoming': upcoming_comps},
                            breadcrumbs=breadcrumbs,
                            page=page
                        )

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
