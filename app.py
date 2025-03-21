from flask import Flask, request, render_template, session, redirect, url_for, jsonify
from psych import get_psych_sheet, get_comps, get_event_ids, get_comp_name, get_competitors, EVENT_SETTINGS_DATA
from login import get_token, get_user_info

app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = 'pspsych'

comps_per_load = 75

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


@app.route('/')
def home():
    return redirect(url_for('comps'))

@app.route("/psych_sheet/", methods=["GET", "POST"])
def comps():
    logged_in = session.get('logged_in', False)

    if logged_in:
        your_comps = get_comps('user', user_id=session.get('user_id'))
    else:
        your_comps = None

    ongoing_comps = get_comps('ongoing')
    upcoming_comps = get_comps('upcoming', comps_per_load, 1)

    breadcrumbs = zip(['Home', 'Psych Sheet'], [url_for('home'), ''])
    
    return render_template('comps.html', comps={'your': your_comps, 'ongoing': ongoing_comps, 'upcoming': upcoming_comps}, breadcrumbs=breadcrumbs)


@app.route("/more_comps", methods=["GET"])
def more_comps():
    page = int(request.args.get("page", 2))
    upcoming_comps = get_comps('upcoming', comps_per_load, page)

    return jsonify(upcoming_comps)

@app.route("/psych_sheet/<comp>", methods=["GET", "POST"])
def psych_sheet(comp):
    competitors = get_competitors(comp)
    name = get_comp_name(comp)
    events = get_event_ids(comp)

    if request.method == "POST":
        solves = int(request.form["solves"])
        event = request.form.get('event')

        if event in events:
            psych_sheet = get_psych_sheet(competitors, event, solves)

            return jsonify(psych_sheet)

    psych_sheet = session.get('psych_sheet', None)

    breadcrumbs = zip(['Home', 'Psych Sheet', get_comp_name(comp, short=True)], [url_for('home'), url_for('comps'), ''])

    return render_template('psych.html', psych_sheet=psych_sheet, events=events, all_events=EVENT_SETTINGS_DATA, comp_id=comp, comp_name=name, competitors=range(len(competitors)), breadcrumbs=breadcrumbs )


if __name__ == "__main__":
    app.run(debug=True, port=8000)
