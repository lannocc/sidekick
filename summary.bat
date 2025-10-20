@echo off
set model=deepseek-r1:8b
if "%~1"=="" (
    echo Usage: summary file.txt or summary folder
    exit /b
)

if exist "%~1\" (
    for %%f in ("%~1\*.txt") do ollama run %model% "Summarize this: " < "%%f" > "%%f.summary.txt"
) else (
    ollama run %model% "Summarize this: " < "%~1" > "%~1.summary.txt"
    echo Summary saved to %~1.summary.txt
)

