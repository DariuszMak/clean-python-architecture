@echo off
docker system df
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)
docker system prune -a
docker system df

docker-compose build
docker-compose up -d app
