# Git Workflow - Dual Remotes (GitHub + Forgejo)

Este documento explica cómo trabajar con el sistema de git remotes dobles configurado para el proyecto Chocolate Factory.

## 🎯 Arquitectura de Remotes

El proyecto está configurado para hacer push simultáneamente a dos repositorios:

```
origin (push múltiple)
├─ GitHub: git@github.com:knono/chocolate-factory.git
└─ Forgejo: https://git.azules-elver.ts.net/nono/chocolate-factory.git
```

## 🔧 Configuración

### Verificar configuración actual

```bash
# Ver remotes
git remote -v

# Ver configuración detallada
git config --get-regexp "remote.origin.*"
```

**Salida esperada:**
```
remote.origin.url git@github.com:knono/chocolate-factory.git
remote.origin.fetch +refs/heads/*:refs/remotes/origin/*
remote.origin.pushurl git@github.com:knono/chocolate-factory.git
remote.origin.pushurl https://git.azules-elver.ts.net/nono/chocolate-factory.git
```

### Configurar desde cero (si es necesario)

```bash
# 1. Añadir GitHub como primer push URL
git remote set-url --add --push origin git@github.com:knono/chocolate-factory.git

# 2. Añadir Forgejo como segunda push URL
git remote set-url --add --push origin https://git.azules-elver.ts.net/nono/chocolate-factory.git

# 3. Verificar
git remote -v
```

## 📋 Flujo de Trabajo Standard

### 1. Desarrollo en Feature Branch

```bash
# Crear feature branch desde develop
git checkout develop
git pull origin develop
git checkout -b feature/nueva-funcionalidad

# Trabajar...
git add .
git commit -m "feat: nueva funcionalidad"

# Push solo a GitHub para backup
git push origin feature/nueva-funcionalidad
```

### 2. Merge a Develop

```bash
# Cambiar a develop
git checkout develop
git pull origin develop

# Mergear feature
git merge feature/nueva-funcionalidad --no-ff -m "feat: descripción de la feature"

# Push a GitHub + Forgejo (dispara pipeline DEV)
git push origin develop
```

**Resultado:**
- ✅ Código actualizado en GitHub
- ✅ Código actualizado en Forgejo
- ✅ **Pipeline DEV ejecutándose** (si hay cambios relevantes)

### 3. Release a Producción

```bash
# Cambiar a main
git checkout main
git pull origin main

# Mergear develop
git merge develop --no-ff -m "release: versión X.Y.Z a producción"

# Push a GitHub + Forgejo (dispara pipeline PROD)
git push origin main
```

**Resultado:**
- ✅ Código actualizado en GitHub
- ✅ Código actualizado en Forgejo
- ✅ **Pipeline PROD ejecutándose**

### 4. Volver a Develop

```bash
# Siempre volver a develop después del release
git checkout develop
```

## 🚀 Comandos Útiles

### Push a ambos repositorios

```bash
# Push de cualquier rama a ambos
git push origin <branch-name>

# Ejemplos:
git push origin develop   # Dispara pipeline DEV
git push origin main      # Dispara pipeline PROD
```

### Push solo a uno de los remotes

Si necesitas pushear solo a un repositorio:

```bash
# Solo a GitHub (usando SSH)
git push git@github.com:knono/chocolate-factory.git <branch>

# Solo a Forgejo (usando HTTPS)
git push https://git.azules-elver.ts.net/nono/chocolate-factory.git <branch>
```

### Ver estado de branches en ambos repos

```bash
# Fetch de ambos
git fetch origin

# Ver branches remotas
git branch -r

# Ver diferencias
git log origin/develop..develop  # Commits locales no pusheados
```

## 🔍 Verificar Pipelines

Después de hacer push, verifica las ejecuciones:

### GitHub
- URL: https://github.com/knono/chocolate-factory/actions
- Uso: Backup, colaboración externa

### Forgejo
- URL: https://git.azules-elver.ts.net/nono/chocolate-factory/actions
- Uso: CI/CD automation, deployment

## ⚠️ Troubleshooting

### Error: "failed to push some refs"

**Causa**: Un repositorio tiene cambios que el otro no tiene.

**Solución**:
```bash
# Pull primero
git pull origin <branch>

# Resolver conflictos si hay
git mergetool

# Intentar push de nuevo
git push origin <branch>
```

### Error: "Authentication failed" en Forgejo

**Causa**: Credenciales de Forgejo no guardadas.

**Solución**:
```bash
# Configurar git credential helper
git config --global credential.helper cache

# Hacer push (te pedirá credenciales una vez)
git push origin develop
```

### Push lento o timeout

**Causa**: Uno de los repositorios tiene problemas de red.

**Solución temporal (push individual)**:
```bash
# Push solo a GitHub
git push git@github.com:knono/chocolate-factory.git <branch>

# Push solo a Forgejo después
git push https://git.azules-elver.ts.net/nono/chocolate-factory.git <branch>
```

## 🎯 Mejores Prácticas

### 1. Commits Atómicos
```bash
# ✅ BIEN: Un commit = una funcionalidad
git commit -m "feat: add user authentication"

# ❌ MAL: Commits enormes con múltiples cambios
git commit -m "various fixes and features"
```

### 2. Mensajes de Commit Descriptivos

Formato recomendado:
```
<tipo>: <descripción corta>

<descripción detallada opcional>

<referencias a issues/tareas>
```

Tipos:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Documentación
- `style`: Formato, sin cambios de código
- `refactor`: Refactorización
- `test`: Tests
- `chore`: Tareas de mantenimiento

### 3. Branches Organizadas

```
main                    # Producción estable
  └─ develop           # Desarrollo activo
      ├─ feature/*     # Nuevas funcionalidades
      ├─ bugfix/*      # Correcciones
      └─ hotfix/*      # Fixes urgentes para producción
```

### 4. Pull Antes de Push

```bash
# Siempre pull antes de push
git pull origin develop
git push origin develop
```

## 📊 Flujo Completo de Sprint

```bash
# 1. Iniciar sprint
git checkout develop
git pull origin develop
git checkout -b feature/sprint_XX_descripcion

# 2. Desarrollo
# ... código ...
git add .
git commit -m "feat: implementación sprint XX"

# 3. Backup en GitHub
git push origin feature/sprint_XX_descripcion

# 4. Merge a develop (dispara pipeline DEV)
git checkout develop
git merge feature/sprint_XX_descripcion --no-ff
git push origin develop

# 5. Verificar deployment en desarrollo
curl http://localhost:8001/health

# 6. Release a producción (dispara pipeline PROD)
git checkout main
git merge develop --no-ff -m "release: Sprint XX"
git push origin main

# 7. Verificar deployment en producción
curl http://localhost:8000/health

# 8. Volver a develop
git checkout develop
```

## 🔗 Referencias

- **GitHub Repository**: https://github.com/knono/chocolate-factory
- **Forgejo Repository**: https://git.azules-elver.ts.net/nono/chocolate-factory
- **Forgejo Actions**: https://git.azules-elver.ts.net/nono/chocolate-factory/actions
- **CI/CD Pipeline Docs**: [CI_CD_PIPELINE.md](./CI_CD_PIPELINE.md)
- **Dual Environment Setup**: [DUAL_ENVIRONMENT_SETUP.md](./DUAL_ENVIRONMENT_SETUP.md)

---

**Última actualización**: 2025-10-13
**Sprint**: 12 - Forgejo CI/CD Dual Environment
