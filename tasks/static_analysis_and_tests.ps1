.\scripts\format_and_lint.ps1 ; 

docker-compose up -d --build --remove-orphans ; 
docker-compose run --rm --no-deps --entrypoint=uv api run pytest /tests --cov=src --cov-report=html --cov-report=xml --cov-config=.coveragerc -vv ; 
docker-compose logs --tail=25 api kafka_eventconsumer ; 

Start-Process .\htmlcov\index.html ; 
Start-Process "http://127.0.0.1:5005" ; 
