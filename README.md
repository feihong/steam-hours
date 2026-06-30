# Steam Hours

## Example .env file

```
STEAM_ID=123456789
API_KEY=ABCDEFGHIJKLMNOPQRSTUVWXYZ
OUTPUT_DIR=/home/me/steamhours

SERVER=myserver.com
```

## Tables

```
CREATE TABLE IF NOT EXISTS game (
    id   INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS game_play (
    game_id INTEGER
    date    INTEGER,
    minutes INTEGER,
    FOREIGN KEY(game_id) REFERENCES game(id)
);
```

## Example Steam API output

```json
{
  "response": {
    "total_count": 5,
    "games": [
      {
        "appid": 1671210,
        "name": "The Farmer Was Replaced",
        "playtime_2weeks": 288,
        "playtime_forever": 1723,
        "img_icon_url": "f76969de63cf2f4eb11bc4a1c17e67beb590a9c5",
        "playtime_windows_forever": 0,
        "playtime_mac_forever": 0,
        "playtime_linux_forever": 1723,
        "playtime_deck_forever": 1723
      },
      {
        "appid": 792100,
        "name": "7 Billion Humans",
        "playtime_2weeks": 224,
        "playtime_forever": 276,
        "img_icon_url": "8e2fdc7d54960f91f3b3eca36d30e32d8fdb590f",
        "playtime_windows_forever": 0,
        "playtime_mac_forever": 131,
        "playtime_linux_forever": 144,
        "playtime_deck_forever": 144
      },
      {
        "appid": 1313140,
        "name": "Replicube",
        "playtime_2weeks": 97,
        "playtime_forever": 97,
        "img_icon_url": "337223c1a97705aee1714ad9534c7d6cfabd92b0",
        "playtime_windows_forever": 0,
        "playtime_mac_forever": 0,
        "playtime_linux_forever": 97,
        "playtime_deck_forever": 97
      }
    ]
  }
}
```

## Fetch gameplay data for specific date range

Use a common table expression that uses LEAD window function.

```sql

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
    game_id,
    next_date AS date,
    next_minutes - minutes AS minutes_played
FROM RankedGameplay
WHERE next_date >= ? AND next_date <= ?;
```

## Set up cron job

1. Create `~/opt/steamhours/.env` on your server
1. `just first_deploy` (use `just deploy` for subsequent deploys)
1. `chmod u+v ~/opt/steamhours/run.sh`
1. Edit the `OUTPUT_DIR` value inside `.env` to generate your report inside a published web directory
1. `crontab -e`
1. Add line `@hourly /home/me/opt/steamhours/run.sh`
1. `crontab -l` to see your jobs

## Links

- [GetRecentlyPlayedGames endpoint](https://developer.valvesoftware.com/wiki/Steam_Web_API#GetRecentlyPlayedGames_(v0001))
