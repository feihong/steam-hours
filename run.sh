#!/bin/bash
cd /home/me/opt/steamhours
/usr/local/bin/uv run --env-file .env compute_steam_hours.py
