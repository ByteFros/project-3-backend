# Análisis de Facturas

Sistema de análisis de facturas desarrollado con Django REST Framework para procesar y analizar datos financieros.

## 🚀 Características

- Carga y procesamiento de facturas desde archivos Excel
- Cálculo automático de IVA y totales
- Análisis de estado de resultados financieros
- API REST para integración con frontends
- Clasificación automática de riesgo financiero

## 📋 Requisitos

- Python 3.12+
- Django 5.2+
- Django REST Framework

## 🛠️ Instalación

1. **Clonar el repositorio:**
```bash
git clone https://github.com/tuusuario/analisis_facturas.git
cd analisis_facturas
```

2. **Crear entorno virtual:**
```bash
python -m venv .venv
```

3. **Activar entorno virtual:**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

4. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

5. **Ejecutar migraciones:**
```bash
cd analisis_facturas
python manage.py migrate
```

6. **Ejecutar servidor:**
```bash
python manage.py runserver
```

## 📊 API Endpoints

### Facturas
- `POST /facturas/subir/` - Subir archivo Excel con facturas
- `GET /facturas/listar/` - Listar facturas procesadas
- `GET /facturas/detalle/<id>/` - Detalle de factura específica
- `POST /facturas/factura_json/` - Procesar facturas desde JSON

### Estado de Resultados
- `POST /facturas/estado_resultados/` - Calcular estado de resultados
- `GET /facturas/estado_resultados2/` - Listar análisis guardados
- `GET /facturas/estado_resultados/<id>/` - Detalle de análisis específico

## 🏗️ Estructura del Proyecto

```
analisis_facturas/
├── core/                    # Configuración Django
├── facturas/               # App principal
│   ├── models/            # Modelos de datos
│   ├── views/             # Vistas de la API
│   ├── serializers/       # Serializadores DRF
│   └── urls.py           # URLs del app
├── manage.py
└── requirements.txt
```

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-feature`)
3. Commit tus cambios (`git commit -am 'Agrega nueva feature'`)
4. Push a la rama (`git push origin feature/nueva-feature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.
