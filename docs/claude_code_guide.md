# Claude Code Guide - Chocolate Factory Project

## 🎯 Objetivo
Esta guía explica cómo usar los nuevos prompts y comandos de Claude Code para refactorizar el proyecto chocolate-factory de manera incremental y determinista.

## 📁 Nueva Estructura de .claude

```
.claude/
├── prompts/           # Instrucciones para Claude Code
│   ├── architects/    # Expertos por dominio
│   └── guidelines/    # Estándares y mejores prácticas
└── commands/          # Comandos ejecutables
    ├── refactor/      # Comandos de refactorización
    └── features/      # Comandos para nuevas funcionalidades
```

## 🏗️ Architects - Expertos por Dominio

### 1. ML Architect (`ml_architect.md`)
**Propósito**: Experto en machine learning y procesamiento de datos de chocolate.

**Cuándo usarlo**:
- Refactorizar lógica de ML desde `main.py`
- Añadir nuevos modelos de predicción
- Optimizar pipelines de entrenamiento
- Implementar feature engineering

**Ejemplo de uso en Claude Code**:
```bash
# Comando para Claude Code
"Usa el ml_architect para extraer la lógica de ML de main.py líneas 145-289 
y crear el módulo src/ml/ siguiendo la arquitectura definida"
```

### 2. Dashboard Architect (`dashboard_architect.md`)
**Propósito**: Experto en frontend vanilla JS y visualización de datos.

**Cuándo usarlo**:
- Separar el dashboard HTML/JS de `main.py`
- Crear componentes web reutilizables
- Implementar actualizaciones en tiempo real
- Mejorar la experiencia de usuario

**Ejemplo de uso**:
```bash
"Siguiendo el dashboard_architect, extrae el código del dashboard 
de main.py y créalo como componentes web en static/"
```

### 3. API Architect (`api_architect.md`)
**Propósito**: Experto en FastAPI y arquitectura de servicios.

**Cuándo usarlo**:
- Restructurar endpoints de `main.py`
- Implementar validación con Pydantic
- Añadir capa de servicios
- Configurar middleware y seguridad

**Ejemplo de uso**:
```bash
"Aplica el api_architect para crear la estructura src/api/ 
y migrar los endpoints de producción con validación Pydantic"
```

## 📝 Commands - Tareas Específicas

### Comandos de Refactorización

#### `extract_ml_module.md`
```bash
# Extrae toda la lógica ML a un módulo separado
"Ejecuta extract_ml_module para mover el código ML de main.py a src/ml/"
```

#### `create_service_layer.md`
```bash
# Crea la capa de servicios para separar lógica de negocio
"Ejecuta create_service_layer para production endpoints"
```

#### `extract_dashboard.md`
```bash
# Separa el dashboard a archivos estáticos
"Ejecuta extract_dashboard para crear static/ con componentes web"
```

### Comandos de Features

#### `add_ml_model.md`
```bash
# Añade un nuevo modelo ML al sistema
"Ejecuta add_ml_model para crear un modelo de predicción de defectos"
```

#### `add_api_endpoint.md`
```bash
# Crea un nuevo endpoint con todas las capas
"Ejecuta add_api_endpoint para crear GET /api/v1/analytics/trends"
```

## 🔄 Flujo de Trabajo con Git Flow

### Sprint 1: Foundation
```bash
# 1. Crear branch
git checkout -b feature/claude-architecture-foundation

# 2. En Claude Code
"Lee los architects en .claude/prompts/architects/ y prepara 
la estructura base de directorios según la arquitectura target"

# 3. Commit y merge
git add .
git commit -m "feat: add claude architects and base structure"
git checkout develop
git merge feature/claude-architecture-foundation
```

### Sprint 2: ML Refactoring
```bash
# 1. Crear branch
git checkout -b feature/ml-module-extraction

# 2. En Claude Code
"Usando ml_architect, ejecuta extract_ml_module para 
refactorizar todo el código ML de main.py"

# 3. Verificar tests
pytest tests/test_ml/

# 4. Commit y merge
git add src/ml/
git commit -m "refactor: extract ML logic to separate module"
```

### Sprint 3: API Layer
```bash
# 1. Crear branch
git checkout -b feature/api-service-layer

# 2. En Claude Code
"Aplica api_architect para implementar la capa de servicios 
y repositorios para los endpoints de producción"

# 3. Verificar que todo funciona
uvicorn src.api.main:app --reload
```

## 🎯 Mejores Prácticas

### 1. Siempre proporciona contexto
```bash
# ❌ Mal
"Refactoriza el código"

# ✅ Bien
"Usando api_architect, refactoriza los endpoints de producción 
(líneas 300-400 de main.py) aplicando el patrón Repository"
```

### 2. Trabaja incrementalmente
```bash
# Primero extrae configuración
"Extrae todas las constantes y configuraciones de main.py a core/config.py"

# Luego crea modelos
"Crea los modelos SQLAlchemy basándote en el esquema actual"

# Finalmente migra lógica
"Migra la lógica de negocio a la capa de servicios"
```

### 3. Verifica después de cada cambio
```bash
# Después de cada refactorización
pytest tests/
uvicorn src.api.main:app --reload
```

## 🚀 Comandos Rápidos para Claude Code

### Análisis inicial
```bash
"Analiza main.py y lista todos los componentes que deben ser extraídos 
según los architects (ML, Dashboard, API)"
```

### Crear estructura
```bash
"Crea la estructura completa de directorios según los tres architects"
```

### Refactorización guiada
```bash
"Guíame paso a paso para refactorizar main.py siguiendo los architects, 
empezando por el componente más simple"
```

### Generar tests
```bash
"Genera tests unitarios para el módulo src/ml/ siguiendo las mejores prácticas"
```

## 📊 Métricas de Éxito

Después de aplicar los architects, deberías lograr:

- ✅ `main.py` < 100 líneas (solo inicialización)
- ✅ Separación clara: ML / API / Dashboard
- ✅ Tests independientes por módulo
- ✅ Documentación automática con OpenAPI
- ✅ Componentes web reutilizables
- ✅ Modelos ML versionados
- ✅ Capa de caché implementada
- ✅ Validación con Pydantic

## 🆘 Troubleshooting

### Si Claude Code no entiende la arquitectura
```bash
"Lee el archivo .claude/prompts/architects/[architect_name].md 
y explícame la arquitectura target para [componente]"
```

### Si hay conflictos al refactorizar
```bash
"Analiza las dependencias entre main.py líneas X-Y 
y sugiere el orden óptimo de extracción"
```

### Si los tests fallan después de refactorizar
```bash
"Compara la funcionalidad original en main.py con la nueva implementación 
y encuentra las diferencias"
```

## 📚 Recursos Adicionales

- **Documentación de negocio**: `/docs/` (mantener sin cambios)
- **Ejemplos de referencia**: Los repos de davila7 que compartiste
- **Arquitectura target**: Ver sección "Target Architecture" en cada architect

---

## 🎬 Siguiente Paso

1. Revisa los tres architects en `.claude/prompts/architects/`
2. Decide qué componente refactorizar primero
3. Crea una feature branch
4. Usa el architect correspondiente con Claude Code
5. Verifica con tests
6. Merge a develop

¡El objetivo es tener un código modular, testeable y mantenible sin perder funcionalidad!