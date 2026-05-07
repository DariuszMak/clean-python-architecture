# EDA template - Python

### Project structure diagram

<p align="center">
  <img src="images/structure_module.svg" alt="Project Structure Diagram" width="600">
</p>

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

$ports = 5005, 54321, 6378, 11025, 18025

foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        $conns | Select-Object -ExpandProperty OwningProcess -Unique |
            Where-Object { $_ -gt 0 } |
            ForEach-Object {
                Write-Host "Port $port is used by PID $_. Killing..."
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
    } else {
        Write-Host "No process is using port $port."
    }
}

uv self update ; 
uv cache clean ; 

git reset --hard HEAD ; 
git clean -x -d -f ; 

#####

uv python install 3.14 ; 
uv python pin 3.14 ; 
uv sync --dev --no-cache ; 
uv lock ; 

#####

.venv\Scripts\Activate.ps1 ; 
$env:UV_ENV_FILE = ".dev.env" ; 

.\scripts\format_and_lint.ps1 ; 

# uv run pydeps src\allocation\entrypoints\flask_app.py --noshow -T svg -o images\structure_runner_clustered.svg --max-bacon 100 --max-module-depth 100 --rankdir LR --cluster ; 
# uv run pydeps src\allocation\entrypoints\flask_app.py --noshow -T svg -o images\structure_runner.svg --max-bacon 2 --max-module-depth 100 --rankdir LR ; 
# uv run pydeps src\allocation\entrypoints\flask_app.py --noshow -T svg -o images\structure_runner_pylib.svg --max-bacon 2 --max-module-depth 100 --rankdir LR --pylib ; 
 
# uv run pydeps src\allocation\entrypoints --noshow -T svg -o images\structure_module_clustered.svg --max-bacon 100 --max-module-depth 100 --rankdir LR --cluster ; 
# uv run pydeps src\allocation\entrypoints --noshow -T svg -o images\structure_module.svg --max-bacon 2 --max-module-depth 100 --rankdir LR ; 
# uv run pydeps src\allocation\entrypoints --noshow -T svg -o images\structure_module_pylib.svg --max-bacon 2 --max-module-depth 100 --rankdir LR --pylib ; 

#####

make all ; 
uv run pytest tests/ --cov=src --cov-report=html --cov-report=xml -vv ; 
Start-Process .\htmlcov\index.html ; 
```

### Fast local refactor

```
clear ; .\scripts\format_and_lint.ps1 ; uv run pytest tests/ -vv ; 
```