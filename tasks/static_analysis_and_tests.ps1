.\scripts\format_and_lint.ps1 ; 

docker-compose down --remove-orphans ; 
docker-compose build ; 
docker-compose up -d ; 
docker-compose run --rm --no-deps --entrypoint=pytest api /tests ; 
docker-compose logs --tail=25 api kafka_eventconsumer ; 

docker-compose down --remove-orphans ; 
docker-compose build ; 
docker-compose up -d ; 
uv run pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-config=.coveragerc -vv ; 
docker-compose logs --tail=25 api kafka_eventconsumer ; 

Start-Process .\htmlcov\index.html ; 
