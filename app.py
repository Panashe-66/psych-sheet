from flask import Flask, request, jsonify, session, redirect, url_for, render_template as html, Response
from psych import get_psych_sheet, get_comps, get_comp_data, download_csv
from oauth import get_access_token, get_user_data
from cache import get_cache
import asyncio
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = 'vgMKTGYE5rUDUzVAY517TsaJcNSoM57iVHKwwKBjCiU' #Remove Later

#--Oauth--
@app.route('/oauth')
def oauth():
    code = request.args['code']
    url = request.args['state']

    if code:
        access_token = get_access_token(code)

        if access_token:
            session['user_data'] = get_user_data(access_token)

        return redirect(url)

@app.route('/logout')
def logout():
    url = request.args['url']

    session.pop('user_data', None)

    return redirect(url)

#--Home-

@app.route('/')
def home():
    return '"Skibidi Toilet Rizzlers" - Leland Pak ❤️'

#--Psych Sheet-

@app.route('/psych_sheet/', methods=['GET', 'POST'])
def psych_comps():
    if request.method == "POST":
        if 'utc_now' not in session:
            session['utc_now'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        comps = get_comps('search', now=session['utc_now'], page=request.form['page'], search=request.form['search'])
        return jsonify(comps)

    session.pop('utc_now', None)

    your_comps = get_comps('user', user_id=session['user_data']['user_id']) if session.get('user_data') else None

    breadcrumbs = zip(
        ['Home', 'Psych Sheet'],
        [url_for('home'), '']
    )

    return html('psych_comps.html', your_comps=your_comps, breadcrumbs=breadcrumbs)

@app.route('/psych_sheet/<comp>', methods=['GET', 'POST'])
def psych_sheet(comp):
    comp_data = get_cache(f'{comp} data', lambda: get_comp_data(comp), 600)
    competitors = comp_data.get("competitors", {})

    if request.method == "POST":
        if request.form['action'] == 'psych_sheet':
            solves = int(request.form["solves"])
            event = request.form['event']

            psych_sheet = asyncio.run(get_psych_sheet(competitors, event, solves))
            return jsonify(psych_sheet)
        elif request.form['action'] == 'csv':
            psych_sheet = request.form['psych_sheet']
            csv = download_csv(psych_sheet)

            event = request.form['event']
            solves = request.form['solves']

            return Response(
                csv.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename={comp}_{event}_Ao{solves}.csv"}
            )

    name = comp_data.get("name", '')
    short_name = comp_data.get("short_name", '')
    events = comp_data.get("event_ids", [])
    advancement_conditions = comp_data.get("advancement_conditions", {})

    breadcrumbs = zip(
        ['Home', 'Psych Sheet', short_name],
        [url_for('home'), url_for('psych_comps'), '']
    )

    return html('psych_sheet.html',
                events=events,
                comp_id=comp, comp_name=name,
                competitors=range(len(competitors)),
                breadcrumbs=breadcrumbs,
                short_name=short_name,
                advancement_conditions=advancement_conditions
    )

if __name__ == "__main__":
    app.run(debug=True)