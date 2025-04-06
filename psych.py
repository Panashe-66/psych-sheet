import requests
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from flag import flag
import time

API = 'https://api.worldcubeassociation.org'

EVENT_SETTINGS_DATA = [
    ('333', '3x3', 50),
    ('222', '2x2', 40),
    ('444', '4x4', 25),
    ('555', '5x5', 20),
    ('666', '6x6', 10),
    ('777', '7x7', 10),
    ('333bf', '3x3 Blindfolded', 12),
    ('333fm', '3x3 Fewest Moves', 6),
    ('333oh', '3x3 One-Handed', 20),
    ('clock', 'Clock', 20),
    ('minx', 'Megaminx', 20),
    ('pyram', 'Pyraminx', 30),
    ('skewb', 'Skewb', 30),
    ('sq1', 'Square-1', 20),
    ('444bf', '4x4 Blindfolded', 5),
    ('555bf', '5x5 Blindfolded', 5),
    ('333mbf', '3x3 Multi-Blind', 5)
]

def sec_to_hms(sec):
    hours, sec = divmod(sec, 3600)
    min, sec = divmod(sec, 60)
    sec = round(sec, 2)

    if hours:
        return f"{int(hours)}:{int(min):02}:{sec:05.2f}"
    elif min:
        return f"{int(min)}:{sec:05.2f}"
    else:
        return f"{sec:.2f}" if sec < 10 else f"{sec:05.2f}"

def date_range(start, end):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    start_year, start_month, start_date = start[:4], months[int(start[5:7])-1], start[8:10].lstrip('0')
    end_year, end_month, end_date = end[:4], months[int(end[5:7])-1], end[8:10].lstrip('0')

    if start == end: #One Day
        return f'{start_month} {start_date}, {start_year}'
    
    elif start_year != end_year: #Multiyear
        return f'{start_month} {start_date}, {start_year} - {end_month} {end_date}, {end_year}'
    
    elif start_month == end_month: #Multiday
        return f'{start_month} {start_date} - {end_date}, {start_year}'
    
    else: #Multimonth
        return f'{start_month} {start_date} - {end_month} {end_date}, {start_year}'

def get_avg(wca_id, event, solves):
    url = f'{API}/persons/{wca_id}/results'
    response = requests.get(url)

    if response.status_code != 200:
        return None
    
    time_list = [
        result["average"] if result.get("average", 0) > 0 
        else (attempt * 100 if event == '333fm' else attempt)
        for result in response.json()
        if result["event_id"] == event
        for attempt in (result.get("attempts", []) if result.get("average", 0) <= 0 else [result["average"]])
        if attempt > 0
    ][::-1][:solves]

    if event == '333mbf':
        mbld_encoded = [[int(str(result)[:2]), int(str(result)[-2:])] for result in time_list]
        time_list = [(99 - result[0]) + result[1] - result[1] for result in mbld_encoded]

    else:
        time_list = [time / 100 for time in time_list]
    
    time_list.sort()

    avg = round(sum(time_list) / len(time_list), 2) if time_list else None

    return avg

def get_psych_sheet(competitors, event, solves):
    psych_sheet = []

    def process_competitor(competitor):
        wca_id = competitor.get("wcaId")
        name = competitor.get("name")
        events = (competitor.get("registration") or {}).get("eventIds", [])

        if wca_id and events and event in events:
            avg =  get_avg(wca_id, event, solves)

            if avg:
                return avg, name
            return None

    with ThreadPoolExecutor(max_workers=75) as executor:
        results = [
            result for result in executor.map(process_competitor, competitors) if result
        ]

    results.sort(reverse=True if event == '333mbf' else False)
    results = [(sec_to_hms(avg), name) for avg, name in results]

    prev_rank, prev_avg = 0, 0

    for rank, (avg, name) in enumerate(results, start=1):
        psych_sheet.append([prev_rank if avg == prev_avg else rank, name, avg])
        prev_rank, prev_avg = (rank, avg) if avg != prev_avg else (prev_rank, prev_avg)
            
    return psych_sheet

def get_comps(when, per_page=100, page=1, user_id=None):
    today = datetime.today().strftime('%Y-%m-%d')
    now = datetime.utcnow().strftime('%Y-%m-%d')

    comps = []
    
    if when == 'ongoing':
        four_days_ago = (datetime.today() - timedelta(days=4)).strftime('%Y-%m-%d')

        url = f"{API}/competitions?start={four_days_ago}&end={today}&sort=start_date&per_page={per_page}&page={page}"
    elif when == 'upcoming':
        tomorrow = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')

        url = f"{API}/competitions?start={tomorrow}&sort=start_date&per_page={per_page}&page={page}"
    elif when == 'user':
        url = f'{API}/users/{user_id}?upcoming_competitions=true&ongoing_competitions=true'
    
    response = requests.get(url)

    if response.status_code != 200:
        return []
    
    comps = response.json()

    if when == 'user':
        upcoming_comps = comps.get("upcoming_competitions", [])
        ongoing_comps = comps.get("ongoing_competitions", [])

        upcoming_comps = sorted(upcoming_comps, key=lambda comp: comp["start_date"])
        ongoing_comps = sorted(ongoing_comps, key=lambda comp: comp["start_date"])

        comps = ongoing_comps + upcoming_comps
    elif when == 'ongoing':
        comps = [comp for comp in comps if comp["end_date"] >= now]
    elif when =='upcoming':
        comps = [comp for comp in comps if "registration_open" in comp and comp["registration_open"] <= now]


    def extract_attributes(comp):
        return {
            "name": comp.get('name', ''),
            "id": comp.get('id', ''),
            "city": comp.get('city', ''),
            "date": date_range(comp.get('start_date', ''), comp.get('end_date', '')),
            "flag": '🌐' if comp.get('country_iso2', '').startswith('X') else flag(comp.get('country_iso2', ''))
        }

    with ThreadPoolExecutor(max_workers=50) as executor:
        comps = list(executor.map(extract_attributes, comps))

    return comps

def get_event_ids(comp_id):
    event_ids = []

    url = f'{API}/competitions/{comp_id}'
    response = requests.get(url)

    if response.status_code != 200:
        return []
    
    event_ids = response.json().get('event_ids')

    return event_ids

def get_comp_name(comp_id, short=False):
    name = ''
    
    url = f'{API}/competitions/{comp_id}'
    response = requests.get(url)

    if response.status_code != 200:
        return ''
    
    if short:
        name = response.json().get('short_name')
    else:
        name = response.json().get('name')

    return name

def get_competitors(comp_id):
    url = f'{API}/competitions/{comp_id}/wcif/public'
    response = requests.get(url)
    
    if response.status_code != 200:
        return []

    competitors = response.json().get("persons", [])

    def valid_competitor(competitor):
        return (
            competitor.get("wcaId") and
            competitor.get("registration") and
            competitor["registration"].get("isCompeting")
        )

    with ThreadPoolExecutor(max_workers=50) as executor:
        competitors = list(executor.map(lambda c: c if valid_competitor(c) else None, competitors))

    return [c for c in competitors if c]
