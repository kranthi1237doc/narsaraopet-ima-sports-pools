from fastapi import FastAPI
import pandas as pd
import re
import requests

app = FastAPI()

# Replace with your published Google Sheet CSV link:
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/https://docs.google.com/spreadsheets/d/e/2PACX-1vRcZEe2xMz2sP-Q97GPw4VQONJOUZj66KxPQ67lWkN8Ora6gZmEElPff2Mo-q2YcCC2hTsCI4nUAXWg/pub?output=csv/pub?output=csv"

def load_players():
    response = requests.get(SHEET_CSV_URL)
    response.raise_for_status()
    df = pd.read_csv(pd.compat.StringIO(response.text))
    return df

def load_finalists():
    with open('finalists.txt', 'r') as f:
        names = set(re.findall(r'[A-Za-z]+', f.read()))
    return names

def assign_pools(df, finalists):
    def is_finalist(name):
        return any(part in finalists for part in re.findall(r'[A-Za-z]+', name))
    df['Finalist'] = df['Name'].apply(is_finalist)
    df_sorted = df.sort_values(['Sex','Finalist','Age'], ascending=[True,False,True]).reset_index(drop=True)
    pool_size = 4
    total = len(df_sorted)
    df_sorted['Pool'] = [i % pool_size + 1 for i in range(total)]
    return df_sorted

@app.get("/api/pools")
def get_pools():
    players = load_players()
    finalists = load_finalists()
    pools = assign_pools(players, finalists)
    out = []
    for n in range(1,5):
        pool_players = pools[pools['Pool']==n]
        pool_data = pool_players.to_dict(orient='records')
        out.append({'pool': n, 'players': pool_data})
    return {"pools": out}

@app.get("/api/games/{game}")
def get_game_players(game: str):
    players = load_players()
    finalists = load_finalists()
    pools = assign_pools(players, finalists)
    game = game.lower()
    result = []
    for n in range(1,5):
        pool_players = pools[(pools['Pool']==n) & (pools['Sports Interested'].str.lower().str.contains(game))]
        pool_data = pool_players.to_dict(orient='records')
        result.append({'pool': n, 'players': pool_data})
    return {"game": game, "pools": result}
