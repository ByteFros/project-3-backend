@echo off
echo ===========================================
echo EJECUTANDO TEST DE TOTAL ACTIVO POR CODIGOS
echo ===========================================
echo.

cd /d "C:\Users\alejo\Desktop\repositorios\analisisFacturas\project-3-backend\analisis_facturas"

echo Activando entorno virtual...
call .venv\Scripts\activate.bat

echo.
echo Ejecutando el comando de test...
python manage.py test_total_activo_codigos

echo.
echo ===========================================
echo TEST COMPLETADO
echo ===========================================
pause
