# Clean Python Architecture

## Setup entire project from scratch

Make sure, that everything is committed or stashed and (optionally):

```commandline
deactivate ; 
clear; 

docker system df ; 
docker stop $(docker ps -a -q) ; 
docker rm -f $(docker ps -a -q) ; 
docker system prune --volumes -a -f ; 
docker system df ; 

git reset --hard HEAD ; 
git clean -x -d -f ; 

make all ; 
```
