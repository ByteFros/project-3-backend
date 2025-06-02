@echo off
echo ===========================================
echo EJECUTANDO TEST MEJORADO DE TOTAL ACTIVO
echo ===========================================
echo.

cd /d "C:\Users\alejo\Desktop\repositorios\analisisFacturas\project-3-backend\analisis_facturas"

echo Activando entorno virtual...
call .venv\Scripts\activate.bat

echo.
echo Ejecutando el comando de test mejorado...
python manage.py test_total_activo_codigos_mejorado

echo.
echo ===========================================
echo Si funciona, ejecutemos el original...
echo ===========================================
echo.
pause

echo Ejecutando test original...
python manage.py test_total_activo_codigos

echo.
echo ===========================================
echo TESTS COMPLETADOS
echo ===========================================
pause
