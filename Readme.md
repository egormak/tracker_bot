# Build Project
```shell
docker build -t ghcr.io/egormak/tracker-bot:v0.5.0 .
docker push ghcr.io/egormak/tracker-bot:v0.5.0
```

# Run Project
## Dev
```shell
docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml ghcr.io/egormak/tracker-bot:v0.5.0
```
## Prod
```shell
docker stop tracker-bot
docker rm tracker-bot
docker run -d --name tracker-bot --network=tracker -v /etc/tracker-bot/config.yaml:/usr/src/app/config.yaml ghcr.io/egormak/tracker-bot:v0.5.0
```
