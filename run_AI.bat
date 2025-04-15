@echo off
chcp 65001 >nul
title 🤖 Запуск AI-English-Tutor
cd /d F:\AI-English-Tutor

echo 🔄 Активируем виртуальное окружение...
call venv\Scripts\activate

echo 🚀 Запускаем ассистента...
python main.py

echo.
echo ✅ Работа завершена. Нажмите любую клавишу для выхода.
pause >nul
