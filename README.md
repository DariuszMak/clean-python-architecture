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

$files = Get-ChildItem "images" -Filter "*.svg"

foreach ($file in $files) {
    $svg = Get-Content $file.FullName -Raw
    $svg = $svg -replace '<polygon fill="white"', '<polygon fill="#141414"'
    $svg = $svg -replace '<svg', '<svg style="background-color:#141414"'
    $svg = $svg -replace 'fill="blue"', 'fill="#5a5a5a"'
    $svg = $svg -replace 'fill="#ffffff"', 'fill="#2e2e2e"'
    $svg = $svg -replace 'stroke="black"', 'stroke="#ffffff"'
    $svg = $svg -replace 'stroke="#000000"', 'stroke="#5f5f5f"'
    $svg = $svg -replace '<text([^>]*)fill="[^"]+"', '<text$1fill="#e0e0e0"'
    $svg = $svg -replace '<g class="cluster">', '<g class="cluster" style="opacity:0.85"'

    Set-Content -Path $file.FullName -Value $svg -Encoding UTF8
    Write-Host "Structure preserved: $($file.Name)"
}

#####

make all ; 
uv run pytest tests/ --cov=src --cov-report=html --cov-report=xml -vv ; 
Start-Process .\htmlcov\index.html ; 
```

### Fast local refactor

```
clear ; .\scripts\format_and_lint.ps1 ; uv run pytest tests/ -vv ; 
```