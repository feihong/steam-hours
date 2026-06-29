# /// script
# requires-python = ">=3.13"
# dependencies = ["requests", "python-dotenv", "htpy"]
# ///

import os
import json
from pathlib import Path
import sqlite3
import datetime
import itertools
from dataclasses import dataclass
from typing import Dict

import dotenv
import requests
from htpy import html, head, meta, title, body, h1, h2, li, ul


dotenv.load_dotenv()
STEAM_ID = os.environ['STEAM_ID']
API_KEY = os.environ['API_KEY']
OUTPUT_FILE = os.environ['OUTPUT_FILE']

con = sqlite3.connect('data.sqlite', autocommit=True)
cur = con.cursor()
games_dict: Dict[int, str] = None


@dataclass
class Gameplay:
    date: datetime.date
    name: str
    minutes: int # minutes played on that date

    @staticmethod
    def from_row(date_ordinal, game_id, minutes):
        date = datetime.date.fromordinal(date_ordinal)
        name = games_dict[game_id]
        return Gameplay(date, name, minutes)


def main():
    setup()

    url = 'https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/'
    response = requests.get(f'{url}?key={API_KEY}&steamid={STEAM_ID}&format=json')
    games = response.json()['response']['games']
    update(games)

    global games_dict
    games_dict = get_games_dict()
    stats = get_gameplay_stats()
    generate_report(stats)

    cleanup()


def setup():
    cur.execute('''
    CREATE TABLE IF NOT EXISTS game (
        appid INTEGER PRIMARY KEY, -- matches appid from Steam API
        name  TEXT
    );
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS gameplay (
        game_id INTEGER,
        date    INTEGER,
        minutes INTEGER, -- total minutes played
        FOREIGN KEY(game_id) REFERENCES game(appid),
        UNIQUE(game_id, date)
    );
    ''')


def update(games):
    today = datetime.date.today()

    for game in games:
        appid = game['appid']

        cur.execute('''
        INSERT INTO game (appid, name) VALUES (?, ?)
        ON CONFLICT (appid) DO NOTHING;
        ''', (appid, game['name']))

        cur.execute('''
        INSERT INTO gameplay (game_id, date, minutes) VALUES (?, ?, ?)
        ON CONFLICT (game_id, date) DO UPDATE SET minutes=excluded.minutes;
        ''', (appid, today.toordinal(), game['playtime_forever']))


def get_games_dict():
    cur.execute('SELECT appid, name FROM game')
    return {k: v for k, v in cur.fetchall()}


def get_gameplay_stats():
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)

    cur.execute('''
    WITH RankedGameplay AS (
        SELECT
            game_id,
            date,
            minutes,
            -- Gets the very next chronological date for this specific game
            LEAD(date) OVER (PARTITION BY game_id ORDER BY date) AS next_date,
            LEAD(minutes) OVER (PARTITION BY game_id ORDER BY date) AS next_minutes
        FROM gameplay
    )
    SELECT
        next_date AS date,
        game_id,
        next_minutes - minutes AS minutes_played
    FROM RankedGameplay
    WHERE next_date >= ? AND next_date <= ?;
    ''', (start_date.toordinal(), end_date.toordinal()))

    def generate():
        for row in cur.fetchall():
            yield Gameplay.from_row(*row)

    return itertools.groupby(generate(), lambda gp: gp.date)


def layout(content):
    title_text = 'Steam Gameplay Report'

    return html(
        head[
            meta(charset='utf-8'),
            title[title_text],
        ],
        body[
            h1[title_text],
            *content,
        ]
    )


def generate_report(stats):
    # def content():
    #     pass

    # with open(OUTPUT_FILE, 'w') as fp:
    #     fp.write(layout(content()))

    for date, plays in stats:
        print(date)
        for p in plays:
            print(p)


def cleanup():
    """
    Clean up gameplay rows older than a month
    """
    pass


if __name__ == '__main__':
    main()
