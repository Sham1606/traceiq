@echo off
setlocal
title TRACEIQ Project Bootstrap
set "ROOT=%~dp0"
for %%D in (
"docs\tasks" "backend\app\api" "backend\app\core" "backend\app\models" "backend\app\schemas"
"backend\app\services\incident" "backend\app\services\investigation" "backend\app\services\collaboration"
"backend\app\services\recovery" "backend\app\services\audit" "backend\app\ai\graph" "backend\app\ai\agents"
"backend\app\ai\prompts" "backend\app\ai\providers" "backend\app\ai\schemas"
"backend\app\evidence\collectors" "backend\app\evidence\analyzers" "backend\app\scenarios"
"backend\tests\unit" "backend\tests\integration" "backend\tests\ai" "backend\tests\scenarios"
"frontend\src\components" "frontend\src\features\incidents" "frontend\src\features\investigation"
"frontend\src\features\findings" "frontend\src\features\evidence" "frontend\src\features\rca"
"frontend\src\features\recovery" "frontend\src\features\audit" "frontend\src\pages" "frontend\src\services"
"frontend\src\hooks" "frontend\src\types" "frontend\src\lib" "frontend\tests\unit" "frontend\tests\e2e"
"data\scenarios\bad-deployment" "data\scenarios\database-degradation"
"data\scenarios\external-dependency" "data\scenarios\configuration-regression" "scripts" "tests\e2e"
) do if not exist "%ROOT%%%~D" mkdir "%ROOT%%%~D"
echo TRACEIQ structure created.
pause
endlocal
