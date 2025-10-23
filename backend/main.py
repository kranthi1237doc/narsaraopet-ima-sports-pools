from fastapi import FastAPI
import pandas as pd
import re
import requests
from collections import defaultdict

app = FastAPI()

# --- 1. SET YOUR GOOGLE SHEET CSV LINK! ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/{sheet_id}/pub?output=csv"

# --- 2. Paste/Pull Full Last-Year Medalists Summary Here ---
BOOK1_SUMMARY = """
Events Events Sushrutha Dhanvantari B C Roy Charaka Badminton Male gold Suresh SuS 10 Male Silver SudheerBhargav Dha 6 Male Doubles Gold Suresh sus Vinod Sus 10 Male Doubles Silver Nikhilesh Cha Kranthi Cha 6 Female gold Swathi Cha 10 Female Silver ChandanaDha 6 Female Doubles Gold Chandana Dha Sobha GayatriDha 10 Female Doubles Silver Swathi Cha Sireesh Cha 6 Mixed doubles Gold Sudheer Bhargav Dha Chandana Dha 10 Mixed doubles silver Kranthi Cha Swathi Cha 6 Table tennis Male gold Raviteja Cha 10 Male Silver Nikhilesh Cha 6 Male Doubles Gold Aditya Dhan Kareem BC R 5 5 Male Doubles Silver Ravi teja Cha Gowtham Cha 6 Female gold Kavitha Sus 10 Female Silver Santhi Sus 6 Female Doubles Gold Kavitha Santhi Sus 10 Female Doubles Silver Hinduja Lakshmi B C Roy 6 Mixed doubles Gold Santhi Vinod Sus 10 Mixed doubles silver Sudheer Hinduja B C Roy 6 Chess Gold RaVI TEJA Cha 10 Silver Vinod SuSSureshSus 6 Carroms Male gold Vinod SuS 10 Male Silver Ramprasad SuS 6 Female gold Hinduja BCRoy 10 Female Silver Divya Cha 6 Swimming FEMALE 25 METERS GOLD Dharani BC roy 10 FEMALE 25 METERS SILVER Bharathi Cha 6 Male below 50 years gold Avinash Cha 10 Male below 50 years silver Jayabharat Dha 6 Male above 50 years gold Sudhakar reddy Dha 10 Male above 50 years silver Ramlinga reddy Sus 6 Volley ball Gold Dhanvantri 10 Silver Sushrutha 6 Relay running Male Gold Dhanvantari 10 Male Silver Charaka 6 Female Gold Charaka 10 Female Silver Dhanvantari 6 Female 50 years gold Dhanvantri 10 Female 50 years silver BC Roy 6 Female 50 years bronze Charaka Throwball Gold BC Roy 10 Silver Sushrutha 6 Tennicoit Single Gold Sushrutha 10 Singles Silver Charaka 6 Doubles gold Sushrutha 10 Doubles silver Charaka 6 Tennis Gold D Venkateswara rao BC Roy 10 Silver M Chandrakiran Dha 6 Cricket Gold Dhanvantari 10 Silver Sushrutha 6 Bronze Charaka
"""

# --- 3. Finalists Event Mapping Extraction ---
def extract_medalist_map(text):
    return re.findall(
        r'([A-Za-z ]+(?:doubles|mixed doubles|single|singles|below 50 years|above 50 years|female 50 years|25 meters)?) (gold|silver|bronze) ([A-Za-z .]+)',
        text, re.I
    )

def build_finalist_event_dict(medalists):
    finalist_events = defaultdict(set)
    for event, medal, names in medalists:
        event = event.strip().lower()
        # handle multiple names in doubles, etc.
        for name in re.findall(r'[A-Za-z.]+', names):
            name = name.strip().lower()
            finalist_events[name].add(event)
    return finalist_events

# Global: built once at app start
finalist_event_dict = build_finalist_event_dict(extract_medalist_map(BOOK1_SUMMARY))

def load_players():
    response = requests.get(SHEET_CSV_URL)
    response.raise_for_status()
    df = pd.read_csv(pd.compat.StringIO(response.text))
    return df

# Check if player is a finalist in any of the games they registered for
def event_finalist_status(name, games):
    name_key = name.strip().split()[0].lower()  # first name match for simplicity
    player_game_set = set(g.strip().lower() for g in str(games).split(','))
    finalist_games = finalist_event_dict.get(name_key, set())
    # Flag is True if any sporting interest this year matches finalist event last year
    return any(game in finalist_games for game in player_game_set)

def assign_pools(df):
    # Build new column 'EventFinalist': True only if player finalist in any registered game
    df['EventFinalist'] = [event_finalist_status(n, g) for n, g in zip(df['Name'], df['Sports Interested'])]
    # Sort by Sex, EventFinalist, Age
    df_sorted = df.sort_values(['Sex', 'EventFinalist', 'Age'], ascending=[True, False, True]).reset_index(drop=True)
    pool_size = 4
    total = len(df_sorted)
    df_sorted['Pool'] = [i % pool_size + 1 for i in range(total)]
    return df_sorted

@app.get("/api/pools")
def get_pools():
    players = load_players()
    pools = assign_pools(players)
    out = []
    for n in range(1,5):
        pool_players = pools[pools['Pool']==n]
        pool_data = pool_players.to_dict(orient='records')
        out.append({'pool': n, 'players': pool_data})
    return {"pools": out}

@app.get("/api/games/{game}")
def get_game_players(game: str):
    players = load_players()
    pools = assign_pools(players)
    game = game.lower()
    result = []
    for n in range(1,5):
        pool_players = pools[(pools['Pool']==n) & (pools['Sports Interested'].str.lower().str.contains(game))]
        pool_data = pool_players.to_dict(orient='records')
        result.append({'pool': n, 'players': pool_data})
    return {"game": game, "pools": result}
