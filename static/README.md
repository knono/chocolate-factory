# Static Dashboard - Chocolate Factory

## Descripción

Dashboard estático profesional para el sistema Chocolate Factory. Consume los mismos endpoints de datos que el dashboard dinámico, proporcionando una interfaz limpia y moderna.

## Estructura

```
static/
├── index.html              # Página principal
├── css/
│   ├── main.css           # Estilos principales
│   └── components/        # Estilos de componentes
│       ├── alerts.css     # Alertas y notificaciones
│       ├── cards.css      # Tarjetas de información
│       └── heatmap.css    # Heatmap semanal
├── js/
│   ├── app.js            # Aplicación principal
│   ├── components/       # Componentes JavaScript
│   │   ├── alerts.js     # Componente de alertas
│   │   ├── heatmap.js    # Componente de heatmap
│   │   └── recommendations.js  # Componente de recomendaciones
│   ├── services/
│   │   └── dashboard-service.js  # Servicio de datos
│   └── utils/
│       ├── api.js        # Cliente API
│       └── formatters.js # Formateadores de datos
└── assets/               # Recursos estáticos (imágenes, etc.)
```

## Características

### 🎨 Diseño Moderno
- **Tema oscuro**: Optimizado para visualización prolongada
- **Responsive**: Adaptable a diferentes tamaños de pantalla
- **Animaciones suaves**: Transiciones y efectos visuales elegantes

### 📊 Componentes Principales

#### 1. Información del Sistema
- Estado operativo en tiempo real
- Fuentes de datos conectadas
- Características Enhanced ML activas

#### 2. Información Actual
- Precio energía actual (REE)
- Condiciones meteorológicas (AEMET/OpenWeatherMap)
- Estado de la fábrica
- Índice de producción de chocolate

#### 3. Heatmap Semanal
- Pronóstico de 7 días
- Codificación por colores según precio energía
- Información meteorológica integrada
- Recomendaciones de producción por día

#### 4. Predicciones ML Enhanced
- Score de optimización energética
- Nivel de producción recomendado
- Costo estimado por kg
- Modelo activo

#### 5. Recomendaciones Operativas
- Recomendaciones de producción
- Optimización energética
- Guía operacional

#### 6. Alertas y Notificaciones
- Alertas en tiempo real
- Clasificación por prioridad
- Iconos visuales

#### 7. Análisis Histórico
- Costo total histórico
- Consumo total en MWh
- Precio mínimo/máximo histórico

## Endpoints Consumidos

El dashboard consume los siguientes endpoints de FastAPI:

- `GET /dashboard/complete` - Datos completos del dashboard
- `GET /ree/prices` - Precios REE en tiempo real
- `GET /weather/hybrid` - Datos meteorológicos híbridos
- `GET /predict/energy-optimization` - Predicciones de optimización energética
- `GET /predict/production-recommendation` - Recomendaciones de producción

## Funcionalidades

### Auto-Refresh
- **Intervalo**: 30 segundos
- **Inteligente**: Se pausa cuando la pestaña está oculta
- **Manual**: Click en el header para actualizar inmediatamente

### Gestión de Estado
- Estado de conexión en tiempo real
- Indicadores visuales de carga
- Manejo de errores robusto

### Visualización de Datos
- Formateo automático de números y fechas
- Códigos de color para estados (success, warning, danger, info)
- Tooltips informativos

## Acceso

### Local
```
http://localhost:8000/
http://localhost:8000/static/index.html
```

### Tailscale (remoto)
```
https://${TAILSCALE_DOMAIN}/
https://${TAILSCALE_DOMAIN}/static/index.html
```

## Tecnologías

- **HTML5**: Estructura semántica
- **CSS3**: Estilos modernos con variables CSS
- **JavaScript ES6+**: Código modular y orientado a objetos
- **Fetch API**: Comunicación con backend
- **Grid/Flexbox**: Layout responsive

## Desarrollo

### Modificar Estilos
Edita los archivos en `css/` y `css/components/`

### Añadir Componentes
1. Crea el archivo JS en `js/components/`
2. Crea el CSS correspondiente en `css/components/`
3. Importa en `index.html`
4. Instancia en `js/app.js`

### Formatear Datos
Utiliza el objeto `Formatters` en `js/utils/formatters.js`

## Sprint 05: Optimización y Pulido

Este dashboard forma parte del Sprint 05, que incluye:

- ✅ **Static Dashboard**: Interfaz moderna y profesional
- ✅ **Rate Limiter**: Protección de endpoints (`src/api/middleware/rate_limiter.py`)
- ✅ **Cache Manager**: Sistema de caché in-memory (`src/core/cache/cache_manager.py`)
- ✅ **Health Checks**: Sistema de salud del servicio (`src/core/health/health_checks.py`)
- ✅ **Production Service Optimized**: Servicio optimizado con caché (`src/services/production_service_optimized.py`)

## Notas

- El dashboard utiliza los mismos datos que `/dashboard/complete`
- Todos los tiempos están en zona horaria Europe/Madrid
- Los precios son en EUR (€)
- Las temperaturas en Celsius (°C)

## Mantenimiento

Para actualizar el dashboard:

1. Modifica los archivos necesarios en `static/`
2. Los cambios se reflejan inmediatamente (bind mount en Docker)
3. No requiere rebuild del contenedor
4. Usa Ctrl+F5 para hard refresh en el navegador
