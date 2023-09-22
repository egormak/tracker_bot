# Build Project
```shell
docker build -t egorm/tracker-bot:v0.1.1 .
docker push egorm/tracker-bot:v0.1.1
```

# Run Project
## Dev
```shell
docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml egorm/tracker-bot:v0.1.1
```
## Prod
```shell
docker stop tracker-bot
docker rm tracker-bot
docker run -d --name tracker-bot --network=tracker -v /etc/tracker-bot/config.yaml:/usr/src/app/config.yaml egorm/tracker-bot:v0.1.1
```
