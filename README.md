# EDA template - Python

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

uv self update ; 
uv cache clean ; 

git reset --hard HEAD ; 
git clean -x -d -f ; 

uv python install 3.14 ; 
uv python pin 3.14 ; 
uv sync --dev --no-cache ; 
uv lock ; 

.venv\Scripts\Activate.ps1 ; 
$env:UV_ENV_FILE = ".dev.env" ; 

.\scripts\format_and_lint.ps1 ; 

# uv run pytest tests/ --cov=src -vv ; 
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