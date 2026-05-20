# EDA template - Python

### Project structure diagrams

##### Modular perspective

<p align="center">
  <img src="images/structure_module.svg" alt="Modular perspective" width="600">
</p>

##### Library dependencies perspective

<p align="center">
  <img src="images/structure_module_clustered.svg" alt="Library dependencies perspective" width="600">
</p>

## Requirements

- [UV](https://github.com/astral-sh/uv) package manager
- [Task](https://taskfile.dev/docs/installation) runner
- [Docker Desktop](https://www.docker.com/products/docker-desktop)

### Fast Windows dev

```commandline
task full-dev-windows ; 
```

### Full analysis

```commandline
task full-static-analyzis ; 
```

### Fast local refactor

```
clear ; .\scripts\format_and_lint.ps1 ; uv run pytest tests/ --cov=src --cov-report=html --cov-report=xml -vv ; Start-Process .\htmlcov\index.html ; 
```