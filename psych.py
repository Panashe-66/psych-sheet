from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Lock
from orjson import loads

from http_session import session

API = 'https://api.worldcubeassociation.org'

EVENT_SETTINGS_DATA = [
    ('333', '3x3', 10),
    ('222', '2x2', 9),
    ('444', '4x4', 5),
    ('555', '5x5', 4),
    ('666', '6x6', 3),
    ('777', '7x7', 3),
    ('333bf', '3x3 Blindfolded', 12),
    ('333fm', '3x3 Fewest Moves', 3),
    ('333oh', '3x3 One-Handed', 4),
    ('clock', 'Clock', 4),
    ('minx', 'Megaminx', 4),
    ('pyram', 'Pyraminx', 6),
    ('skewb', 'Skewb', 6),
    ('sq1', 'Square-1', 4),
    ('444bf', '4x4 Blindfolded', 6),
    ('555bf', '5x5 Blindfolded', 6),
    ('333mbf', '3x3 Multi-Blind', 6)
]

def remove_comp_duplicates():
    if not hasattr(remove_comp_duplicates, "_lock"):
        remove_comp_duplicates._lock = Lock()

    return remove_comp_duplicates._lock

def utc_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

def get_psych_sheet(competitors, event, solves):
    psych_sheet = []

    type = 'single' if event in ['333bf', '444bf', '555bf', '333mbf'] else 'avg'

    def get_avg(wca_id, event, solves, type):
        url = f'{API}/persons/{wca_id}/results'
        response = session.get(url)

        if response.status_code != 200:
            return None
        
        time_list = [
            (attempt / 100 if event != '333mbf' else attempt)
            for result in loads(response.content)
            if result["event_id"] == event
            for attempt in (result.get('attempts', []) if type == 'single' else [result.get('average', 0)])
            if attempt > 0
        ][::-1][:solves]

        if event == '333mbf':
            mbld_encoded = [[int(str(result)[:2]), int(str(result)[-2:])] for result in time_list]
            time_list = [(99 - result[0]) + result[1] - result[1] for result in mbld_encoded]

        avg = round(sum(time_list) / len(time_list), 2) if time_list else None
        
        return avg

    def process_competitor(competitor):
        wca_id = competitor.get("wcaId")
        name = competitor.get("name")
        events = (competitor.get("registration") or {}).get("eventIds", [])
        

        if wca_id and events and event in events:
            avg =  get_avg(wca_id, event, solves, type)

            if avg:
                return avg, name
            return None

    with ThreadPoolExecutor(max_workers=40) as executor:
        results = [
            result for result in executor.map(process_competitor, competitors) if result
        ]

    results.sort(reverse=(event == '333mbf'))
    
    if event == '333mbf':
        results = [(f'{avg:.2f} Pts', name) for avg, name in results]
    elif event == '333fm':
        results = [(f'{avg:.2f}', name) for avg, name in results]
    else:
        def sec_to_hms(sec):
            hours, sec = divmod(sec, 3600)
            min, sec = divmod(sec, 60)
            sec = round(sec, 2)

            return (
                f"{int(hours)}:{int(min):02}:{sec:05.2f}" if hours else #HH:MM:SS.ss
                f"{int(min)}:{sec:05.2f}" if min else #MM:SS.ss
                f"{sec:.2f}" if sec < 10 else f"{sec:05.2f}" #SS.ss
            )
        
        results = [(sec_to_hms(avg), name) for avg, name in results]

    prev_rank, prev_avg = 0, 0

    for rank, (avg, name) in enumerate(results, start=1):
        psych_sheet.append([prev_rank if avg == prev_avg else rank, name, avg])
        prev_rank, prev_avg = (rank, avg) if avg != prev_avg else (prev_rank, prev_avg)
            
    return psych_sheet

def get_comps(when, per_page=25, page=1, user_id=None, search=None, now=None):
    today = now[:10]

    comps = []
    
    if when == 'ongoing':
        url = f"{API}/competitions?ongoing_and_future={today}&sort=start_date,end_date,name&per_page=100&page={page}&include_cancelled=false"
    elif when == 'upcoming':
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')

        url = f"{API}/competitions?start={tomorrow}&sort=start_date,end_date,name&per_page={per_page}&page={page}&include_cancelled=false"
    elif when == 'user':
        url = f'{API}/users/{user_id}?upcoming_competitions=true&ongoing_competitions=true&include_cancelled=false'
    elif when == 'search':
        url = f"{API}/competitions?ongoing_and_future={today}&sort=start_date,end_date,name&per_page={per_page}&page={page}&q={search}&include_cancelled=false"
    
    response = session.get(url)

    if response.status_code != 200:
        return []
    
    comps = loads(response.content)

    if when == 'user':
        upcoming_comps = comps.get("upcoming_competitions", [])
        ongoing_comps = comps.get("ongoing_competitions", [])

        upcoming_comps = sorted(upcoming_comps, key=lambda comp: comp["start_date"])
        ongoing_comps = sorted(ongoing_comps, key=lambda comp: comp["start_date"])

        comps = ongoing_comps + upcoming_comps
        
        if not comps:
            return 'No Comps User'
        
    elif when == 'ongoing':
        comps = [comp for comp in comps if comp["end_date"] >= today and comp["start_date"] <= today]
    elif when =='upcoming' or when == 'search':
        comps = [comp for comp in comps if comp["registration_open"] <= now]
    

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

    def extract_attributes(comp):
        return {
            "name": comp['name'],
            "id": comp['id'],
            "city": comp['city'],
            "date": date_range(comp['start_date'], comp['end_date']),
            "flag": '🌐' if comp['country_iso2'].startswith('X') else 
            chr(0x1F1E6 + ord(comp['country_iso2'][0].upper()) - ord('A')) + chr(0x1F1E6 + ord(comp['country_iso2'][1].upper()) - ord('A'))
        }

    with ThreadPoolExecutor(max_workers=50) as executor:
        comps = list(executor.map(extract_attributes, comps))

    if when == 'ongoing' and len(comps) == 100:
        comps.extend(get_comps('ongoing', 100, page+1))

    return comps

def get_comp_info(comp_id):
    data = []
    
    url = f'{API}/competitions/{comp_id}'
    response = session.get(url)

    if response.status_code != 200:
        return []
    
    comp = loads(response.content)

    data.extend([comp['name'], comp['short_name'], comp['event_ids']])
        
    return data

def get_competitors(comp_id):
    url = f'{API}/competitions/{comp_id}/wcif/public'
    response = session.get(url)
    
    if response.status_code != 200:
        return []
    
    data = loads(response.content)
    competitors = data.get("persons", [])

    return [
        {
            "wcaId": c["wcaId"],
            "name": c["name"],
            "registration": c["registration"]
        }
        for c in competitors
        if (reg := c.get("registration")) and
            c.get("wcaId") and
            reg.get("isCompeting") and
            reg.get("status") == 'accepted'
    ]