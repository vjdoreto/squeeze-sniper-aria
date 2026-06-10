@echo off
chcp 65001 >nul
title eAssets Dashboard — Doreto Squeeze Sniper
cd /d "%~dp0"
python iniciar_dashboard.py
pause
