# Clean Python Architecture

## Setup entire project from scratch

Make sure, that everything is committed or stashed and (optionally):


### Local environment

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

python3 -m pip install --upgrade pip
python3 -m pip install virtualenv
python3 -m virtualenv venv

venv\Scripts\Activate.ps1

python3 -m pip install -r requirements.txt
```

### Docker container

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