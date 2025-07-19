from concurrent.futures import ThreadPoolExecutor
import aiohttp
import asyncio
from json_request import get_json, get_json_async, async_connector, async_semaphore
import csv
from io import StringIO, BytesIO
from orjson import loads
from math import ceil

#Ledger compter thing
#Comp doesnt exist / No regged ppl / Private comp
#Search combo thing  
#Phase reg
#Variables, functions names
#Error thing for not enough competitors
#Function  returrrnss nothing
#secret key
#404
#home paage
#define elementst in js
#Clean up html/js/css

API = 'https://api.worldcubeassociation.org'
COMPS_PER_PAGE = 25
MAX_WORKERS = 20

async def get_psych_sheet(competitors, event, solves):
    psych_sheet = []

    connector = async_connector()
    semaphore = async_semaphore()

    async def get_avg(session, wca_id):
        results = await get_json_async(session, f'{API}/persons/{wca_id}/results?event_id={event}')

        if results == 'error':
            return
        
        time_list = [a for result in results for a in result.get('attempts', []) if a > 0][-solves:]
    
        if not time_list:
            return
        
        if event == '333mbf':
            mbld_encoded = [int(str(result)[:2]) for result in time_list]
            time_list = [99 - result for result in mbld_encoded]

        if len(time_list) > 3:
            trim = ceil(len(time_list) * 0.05)
            time_list = sorted(time_list)[trim:-trim]

        avg = round(sum(time_list) / len(time_list) / (100 if event not in ['333mbf', '333fm'] else 1), 2)

        return avg if time_list else None

    async def process_competitor(session, competitor):
        async with semaphore:
            wca_id = competitor.get("wcaId")
            name = competitor.get("name")
            events = competitor.get("eventIds")
            
            if event in events:
                avg = await get_avg(session, wca_id)

                return (avg, name, wca_id) if avg is not None else None

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(process_competitor(session, c)) for c in competitors]
        results = list(filter(None, await asyncio.gather(*tasks)))

    results.sort(reverse=(event == '333mbf'))
    
    def sec_to_hms(sec):
        hours, remainder = divmod(sec, 3600)
        min, sec = divmod(remainder, 60)
        sec = round(sec, 2)

        if hours:
            return f"{int(hours)}:{int(min):02}:{sec:05.2f}" #HH:MM:SS.ss
        if min:
            return f"{int(min)}:{sec:05.2f}" #MM:SS.ss
        
        return f"{sec:.2f}" if sec < 10 else f"{sec:05.2f}" #SS.ss
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        if event == '333mbf':
            results = [(f'{avg:.2f} Pts', name, wca_id) for avg, name, wca_id in results]
        elif event == '333fm':
            results = [(f'{avg:.2f}', name, wca_id) for avg, name, wca_id in results]
        else:
            results = list(executor.map(lambda t: (sec_to_hms(t[0]) if t[0] > 60 else f"{t[0]:.2f}", t[1], t[2]), results))

    prev_rank, prev_avg = 0, None

    for rank, (avg, name, wca_id) in enumerate(results, start=1):
        if avg == prev_avg:
            psych_sheet.append([prev_rank, name, avg, wca_id])
        else:
            psych_sheet.append([rank, name, avg, wca_id])
            prev_rank, prev_avg = rank, avg
            
    return psych_sheet

def get_comps(when, now=None, page=1, user_id=None, search=None):    
    if when == 'user':
        comps = get_json(f'{API}/users/{user_id}?upcoming_competitions=true&ongoing_competitions=true&include_cancelled=false')

        if comps == 'error':
            return []
        
        upcoming = sorted(comps.get("upcoming_competitions", []), key=lambda c: c["start_date"])
        ongoing = sorted(comps.get("ongoing_competitions", []), key=lambda c: c["start_date"])
        comps = ongoing + upcoming

        if not comps:
            return 'No Comps User'

    elif when == 'search':
        today = now[:10]

        comps = get_json(f"{API}/competitions?ongoing_and_future={today}&sort=start_date,end_date,name&per_page={COMPS_PER_PAGE}&page={page}&q={search}&include_cancelled=false")

        if comps == 'error':
            return []

        comps = [c for c in comps if c["registration_open"] <= now]
    
    MONTHS = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    
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

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        comps = list(executor.map(extract_attributes, comps))

    return comps

def get_comp_data(comp_id):
    comp = get_json(f'{API}/competitions/{comp_id}/wcif/public')

    if comp == 'error':
        return {}
    
    return {
        "name": comp["name"],
        "short_name": comp["shortName"],
        "event_ids": [event['id'] for event in comp['events']],
        "competitors": [
            {
                "wcaId": c["wcaId"],
                "name": c["name"],
                "eventIds": (c.get("registration") or {}).get("eventIds", [])
            }
            for c in comp.get("persons", [])
            if c.get("wcaId") and (c.get("registration") or {}).get("isCompeting")
        ],
        "advancement_conditions": {
            event['id']: [
                round['advancementCondition']
                for round in event['rounds']
                if round['advancementCondition']
            ]
            for event in comp['events']
        }
    }

def download_csv(psych_sheet):
    psych_sheet = loads(psych_sheet)
    output = StringIO()
    csv.writer(output).writerows([["Seed", "Name", "Seed Result"]] + [row[:3] for row in psych_sheet])
    csv_file = BytesIO(output.getvalue().encode('utf-8'))

    return csv_file