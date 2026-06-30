set dotenv-load := true

generate:
    uv run --env-file .env compute_steam_hours.py

deploy:
    rsync -avz compute_steam_hours.py $SERVER:~/opt/steamhours

first_deploy:
    rsync -avz .env run.sh $SERVER:~/opt/steamhours
    just deploy
