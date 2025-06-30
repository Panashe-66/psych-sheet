from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import aiohttp
import asyncio
from json_request import get_json, get_json_async
from operator import itemgetter
from statistics import mean

#Search Competititors

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


async def get_psych_sheet(competitors, event, solves):
    psych_sheet = []
    is_single = event in ['333bf', '444bf', '555bf', '333mbf']

    connector = aiohttp.TCPConnector(limit=100)
    semaphore = asyncio.Semaphore(50)

    async def get_avg(session, wca_id):
        results = await get_json_async(session, f'{API}/persons/{wca_id}/results')

        if results == 'error':
            return []
        
        time_list = []

        for result in results:
            if result["event_id"] == event:

                if is_single:
                    time_list += [a for a in result.get('attempts', []) if a > 0]
                else:
                    avg = result.get('average', 0)
                    if avg > 0:
                        time_list.append(avg)

        time_list = time_list[-solves:]

        if not time_list:
            return []

        if event == '333mbf':
            mbld_encoded = [int(str(result)[:2]) for result in time_list]
            time_list = [99 - result for result in mbld_encoded]
        else:
            time_list = [a / 100 for a in time_list]

        return round(mean(time_list), 2)

    async def process_competitor(session, competitor):
        async with semaphore:
            wca_id = competitor.get("wcaId")
            name = competitor.get("name")
            events = (competitor.get("registration") or {}).get("eventIds", [])
            
            if wca_id and event in events:
                avg = await get_avg(session, wca_id)
                return (avg, name) if avg is not None else None

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(process_competitor(session, c)) for c in competitors]
        results = list(filter(None, await asyncio.gather(*tasks)))

    results.sort(reverse=(event == '333mbf'))
    
    if event == '333mbf':
        results = [(f'{avg:.2f} Pts', name) for avg, name in results]
    elif event == '333fm':
        results = [(f'{avg:.2f}', name) for avg, name in results]
    else:
        def sec_to_hms(sec):
            hours, remainder = divmod(sec, 3600)
            min, sec = divmod(remainder, 60)
            sec = round(sec, 2)

            if hours:
                return f"{int(hours)}:{int(min):02}:{sec:05.2f}" #HH:MM:SS.ss
            if min:
                return f"{int(min)}:{sec:05.2f}" #MM:SS.ss
            
            return f"{sec:.2f}" if sec < 10 else f"{sec:05.2f}" #SS.ss
        
        results = [(sec_to_hms(avg), name) for avg, name in results]

    prev_rank, prev_avg = 0, None

    for rank, (avg, name) in enumerate(results, start=1):
        if avg == prev_avg:
            psych_sheet.append([prev_rank, name, avg])
        else:
            psych_sheet.append([rank, name, avg])
            prev_rank, prev_avg = rank, avg
            
    return psych_sheet

def get_comps(when, per_page=25, page=1, user_id=None, search=None):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    today = now[:10]
    
    if when == 'user':
        comps = get_json(f'{API}/users/{user_id}?upcoming_competitions=true&ongoing_competitions=true&include_cancelled=false')

        if comps == 'error':
            return []
        
        upcoming = sorted(comps.get("upcoming_competitions", []), key=itemgetter("start_date"))
        ongoing = sorted(comps.get("ongoing_competitions", []), key=itemgetter("start_date"))
        comps = ongoing + upcoming

        if not comps:
            return 'No Comps User'

    elif when == 'search':
        comps = get_json(f"{API}/competitions?ongoing_and_future={today}&sort=start_date,end_date,name&per_page={per_page}&page={page}&q={search}&include_cancelled=false")

        if comps == 'error':
            return []

        comps = [c for c in comps if c["registration_open"] <= now]
    
    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    def date_range(start, end):
        s_year, s_month, s_date = start[:4], MONTHS[int(start[5:7])-1], start[8:10].lstrip('0')
        e_year, e_month, e_date = end[:4], MONTHS[int(end[5:7])-1], end[8:10].lstrip('0')

        if start == end: #One Day
            return f'{s_month} {s_date}, {s_year}'

        elif s_year != e_year: #Multiyear
            return f'{s_month} {s_date}, {s_year} - {e_month} {e_date}, {e_year}'
        
        elif s_month == e_month: #Multiday
            return f'{s_month} {s_date} - {e_date}, {s_year}'
        
        else: #Multimonth
            return f'{s_month} {s_date} - {e_month} {e_date}, {s_year}'

    def extract_attributes(comp):
        country_code = comp['country_iso2'].upper()

        if country_code.startswith('X'):
            flag = '🌐'
        else:
            flag = chr(0x1F1E6 + ord(country_code[0]) - ord('A')) + chr(0x1F1E6 + ord(country_code[1]) - ord('A'))

        return {
            "name": comp['name'],
            "id": comp['id'],
            "city": comp['city'],
            "date": date_range(comp['start_date'], comp['end_date']),
            "flag": flag
        }

    with ThreadPoolExecutor(max_workers=20) as executor:
        comps = list(executor.map(extract_attributes, comps))

    return comps

def get_comp_info(comp_id):
    comp = get_json(f'{API}/competitions/{comp_id}')

    if comp == 'error':
        return []

    return [comp['name'], comp['short_name'], comp['event_ids']]

def get_competitors(comp_id):
    data = get_json(f'{API}/competitions/{comp_id}/wcif/public')
    
    if data == 'error':
        return []

    return [
        {
            "wcaId": c["wcaId"],
            "name": c["name"],
            "registration": c["registration"]
        }
        for c in data.get("persons", [])
        if (reg := c.get("registration")) and
            c.get("wcaId") and
            reg.get("isCompeting") and
            reg.get("status") == 'accepted'
    ]