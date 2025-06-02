@echo off
echo =====================================================
echo SUITE EXHAUSTIVA DE TESTS - TotalActivoCodigosView
echo =====================================================
echo.
echo Selecciona el tipo de test que quieres ejecutar:
echo.
echo 1. Test basico rapido
echo 2. Suite exhaustiva completa
echo 3. Validacion contable empresarial  
echo 4. Benchmark de performance
echo 5. TODOS los tests (completo)
echo 6. Ver ayuda de comandos
echo.
set /p choice="Ingresa tu opcion (1-6): "

cd /d "C:\Users\alejo\Desktop\repositorios\analisisFacturas\project-3-backend\analisis_facturas"
call .venv\Scripts\activate.bat

if "%choice%"=="1" goto test_basico
if "%choice%"=="2" goto test_exhaustivo
if "%choice%"=="3" goto test_contable
if "%choice%"=="4" goto test_benchmark
if "%choice%"=="5" goto test_completo
if "%choice%"=="6" goto ayuda
goto error

:test_basico
echo.
echo ===============================
echo EJECUTANDO TEST BASICO RAPIDO
echo ===============================
python manage.py test_total_activo_forzado
goto fin

:test_exhaustivo
echo.
echo ================================
echo EJECUTANDO SUITE EXHAUSTIVA
echo ================================
python manage.py test_exhaustivo --test=all
goto fin

:test_contable
echo.
echo ====================================
echo EJECUTANDO VALIDACION CONTABLE
echo ====================================
python manage.py test_validacion_contable
goto fin

:test_benchmark
echo.
echo ===============================
echo EJECUTANDO BENCHMARK PERFORMANCE
echo ===============================
echo Selecciona el tamaño del dataset:
echo 1. Small (100 registros)
echo 2. Medium (1,000 registros) 
echo 3. Large (5,000 registros)
echo 4. XLarge (10,000 registros)
set /p size_choice="Tamaño (1-4): "

if "%size_choice%"=="1" python manage.py test_benchmark --size=small
if "%size_choice%"=="2" python manage.py test_benchmark --size=medium
if "%size_choice%"=="3" python manage.py test_benchmark --size=large
if "%size_choice%"=="4" python manage.py test_benchmark --size=xlarge
goto fin

:test_completo
echo.
echo ==============================
echo EJECUTANDO SUITE COMPLETA
echo ==============================
echo ⚠️ ATENCION: Esto puede tomar varios minutos
set /p confirm="¿Continuar? (s/n): "
if /i "%confirm%"=="s" (
    python manage.py test_suite_completa --test=all
) else (
    echo Test cancelado.
)
goto fin

:ayuda
echo.
echo ===============================
echo AYUDA - COMANDOS DISPONIBLES
echo ===============================
echo.
echo TESTS INDIVIDUALES:
echo python manage.py test_total_activo_codigos
echo python manage.py test_total_activo_forzado
echo python manage.py test_exhaustivo --test=basic
echo python manage.py test_exhaustivo --test=edge
echo python manage.py test_exhaustivo --test=performance
echo python manage.py test_validacion_contable
echo python manage.py test_benchmark --size=medium
echo.
echo SUITE COMPLETA:
echo python manage.py test_suite_completa --test=all
echo python manage.py test_suite_completa --test=basic
echo python manage.py test_suite_completa --test=benchmark
echo.
echo PARAMETROS DE BENCHMARK:
echo --size=small    (100 registros)
echo --size=medium   (1,000 registros)
echo --size=large    (5,000 registros)
echo --size=xlarge   (10,000 registros)
echo.
goto fin

:error
echo.
echo ❌ Opcion invalida. Por favor selecciona 1-6.
goto fin

:fin
echo.
echo ===============================
echo TESTS COMPLETADOS
echo ===============================
pause
