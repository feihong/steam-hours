# /// script
# requires-python = ">=3.13"
# dependencies = ["requests", "htpy"]
# ///

import os
import json
from pathlib import Path
import sqlite3
import datetime
import itertools
from dataclasses import dataclass
from typing import Dict

import requests
from htpy import html, head, meta, title, body, h1, h2, ul, li, a as anchor


STEAM_ID = os.environ['STEAM_ID']
API_KEY = os.environ['API_KEY']
OUTPUT_DIR = os.environ['OUTPUT_DIR']

output_file = Path(OUTPUT_DIR) / 'index.html'
con = sqlite3.connect(Path(__file__).parent / 'data.sqlite', autocommit=True)
cur = con.cursor()
games_dict: Dict[int, str] = None


@dataclass
class Gameplay:
    date: datetime.date
    name: str
    game_id: int
    minutes: int # minutes played on that date

    @staticmethod
    def from_row(date_ordinal, game_id, minutes):
        date = datetime.date.fromordinal(date_ordinal)
        name = games_dict[game_id]
        return Gameplay(date, name, game_id, minutes)


def main():
    setup()
    games = pull()
    update(games)
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


def pull():
    url = 'https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/'
    response = requests.get(f'{url}?key={API_KEY}&steamid={STEAM_ID}&format=json')
    games = response.json()['response']['games']
    for game in games:
        print(f'{game['appid']} {game['name']}: {game['playtime_forever']}')
    return games


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
        ON CONFLICT (game_id, date) DO UPDATE SET minutes = excluded.minutes;
        ''', (appid, today.toordinal(), game['playtime_forever']))

    global games_dict
    games_dict = get_games_dict()



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
            LEAD(date) OVER win AS next_date,
            LEAD(minutes) OVER win AS next_minutes
        FROM gameplay
        WINDOW win AS (PARTITION BY game_id ORDER BY date)
    )
    SELECT
        next_date AS date,
        game_id,
        next_minutes - minutes AS minutes_played
    FROM RankedGameplay
    WHERE next_date BETWEEN ? AND ?;
    ''', (start_date.toordinal(), end_date.toordinal()))

    def generate():
        for row in cur.fetchall():
            yield Gameplay.from_row(*row)

    return itertools.groupby(generate(), lambda gp: gp.date)


def layout(content):
    title_text = 'Steam Gameplay Report'

    return html[
        head[
            meta(charset='utf-8'),
            meta(name='viewport', content='width=device-width,initial-scale=1'),
            title[title_text],
        ],
        body[
            h1[title_text],
            *content,
        ]
    ]


def generate_report(stats):
    def item(play):
        return li[
            anchor(href=f'https://store.steampowered.com/app/{play.game_id}')[
                play.name
            ],
            ': ',
            show_minutes(play.minutes),
        ]

    def content():
        for date, plays in stats:
            yield h2[date.strftime('%B %d, %Y')]

            yield ul[[item(play) for play in plays]]

    with open(output_file, 'w') as fp:
        fp.write(str(layout(content())))

    print(f'Generated report to {output_file}')


def show_minutes(minutes : int):
    """
    Convert minutes to string with H:MM format
    """
    td = datetime.timedelta(minutes=minutes)
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes = remainder // 60
    return f'{hours:.0f}:{minutes:02.0f}'


def cleanup():
    """
    Delete gameplay rows older than a month, but leave the last row for a game no matter how old
    """
    month_ago = datetime.date.today() - datetime.timedelta(days=30)

    cur.execute('''
    DELETE FROM gameplay
    WHERE date < ?
      AND EXISTS (
            SELECT 1
            FROM gameplay g2
            WHERE gameplay.game_id = g2.game_id
            AND g2.date > gameplay.date
          );
    ''', (month_ago.toordinal(),))


if __name__ == '__main__':
    main()
