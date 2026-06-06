@echo off
cd /d C:\Users\Admin\Documents\Codex\Демо
set DJANGO_ALLOWED_HOSTS=*
set DJANGO_DEBUG=1
echo Django demo server starting...
echo Open in browser: http://127.0.0.1:8000/accounts/login/
echo Demo login: demo_commission / Demo2026!
"C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" manage.py runserver 0.0.0.0:8000
