# SOPS Secrets Management - Chocolate Factory

**Fecha**: 14 de Octubre, 2025
**Status**: ✅ **IMPLEMENTADO**
**Versión**: 1.0

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [¿Por qué SOPS?](#por-qué-sops)
3. [Arquitectura](#arquitectura)
4. [Instalación](#instalación)
5. [Flujo de Trabajo](#flujo-de-trabajo)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)
8. [Migración desde Docker Secrets](#migración-desde-docker-secrets)

---

## Resumen Ejecutivo

**SOPS** (Secrets OPerationS) es la solución adoptada para gestión de secretos en Chocolate Factory, reemplazando completamente Docker Secrets.

### Problema Resuelto

- ❌ **Docker Secrets**: NO funcionan en Docker Compose (problemas permisos UID/GID)
- ✅ **SOPS**: Secrets encriptados commiteables en Git de forma segura
- ✅ **CI/CD nativo**: Desencriptación automática en pipelines
- ✅ **Auditoría**: Git history muestra quién cambió qué
- ✅ **Sin runtime overhead**: Desencripta a `.env` en tiempo de despliegue

### Secrets Gestionados

Total: **14 secrets**

```yaml
- aemet_api_key              # AEMET OpenData API
- anthropic_api_key          # Claude Haiku API
- influxdb_admin_password    # InfluxDB admin password
- influxdb_token_dev         # InfluxDB token (dev)
- influxdb_token             # InfluxDB token (prod)
- openweathermap_api_key     # OpenWeatherMap API
- ree_api_token              # REE electricity prices API
- registry_password          # Docker Registry
- registry_user              # Docker Registry user
- runner_token_dev           # Gitea Actions runner (dev)
- runner_token_prod          # Gitea Actions runner (prod)
- tailscale_authkey_dev      # Tailscale auth (dev node)
- tailscale_authkey_git      # Tailscale auth (git node)
- tailscale_authkey          # Tailscale auth (prod node)
```

---

## ¿Por qué SOPS?

### Comparativa con Alternativas

| Feature | SOPS | Docker Secrets | Vault | AWS Secrets |
|---------|------|----------------|-------|-------------|
| Git-friendly | ✅ Sí | ❌ No | ❌ No | ❌ No |
| CI/CD nativo | ✅ Sí | ⚠️ Parcial | ⚠️ Complejo | ⚠️ Cloud-only |
| Auditoría | ✅ Git history | ❌ No | ✅ Logs | ✅ Logs |
| Self-hosted | ✅ Sí | ✅ Sí | ⚠️ Complejo | ❌ No |
| Coste | ✅ Gratis | ✅ Gratis | ⚠️ Setup | 💰 Pago |
| Compose support | ✅ Sí | ❌ No | ⚠️ Ext tools | ❌ No |

### Ventajas Específicas

1. **Commitable en Git**: Secrets encriptados pueden versionarse
2. **Una sola clave age**: Simplifica gestión vs 14 secrets individuales
3. **Rotación simple**: `sops rotate` cambia claves de encriptación
4. **Desencriptación en CI/CD**: Integración nativa en workflows
5. **Sin dependencias externas**: No requiere servicios adicionales

---

## Arquitectura

### Flujo de Encriptación/Desencriptación

```
┌─────────────────────────────────────────────────────────────┐
│                   DEVELOPER LOCAL                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. age-keygen → .sops/age-key.txt                         │
│     (Private key - NO COMMIT)                               │
│                                                             │
│  2. Create secrets.yaml                                     │
│     (Plain YAML - 14 secrets)                               │
│                                                             │
│  3. sops --encrypt secrets.yaml → secrets.enc.yaml         │
│     (Encrypted with age public key)                         │
│                                                             │
│  4. git add secrets.enc.yaml                                │
│     git commit -m "chore: update secrets"                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ git push
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FORGEJO REPOSITORY                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  secrets.enc.yaml (encrypted, safe to commit)               │
│  .sops/age-key.txt (NOT in repo, only in Secret)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Gitea Actions trigger
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   CI/CD PIPELINE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Checkout code                                           │
│  2. Decrypt with SOPS:                                      │
│     echo "${{ secrets.SOPS_AGE_KEY }}" > /tmp/age-key.txt  │
│     sops --decrypt secrets.enc.yaml > .env                 │
│  3. docker compose -f docker-compose.dev.yml up -d          │
│     (Uses .env variables)                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Archivo de Secrets Encriptado

**Archivo**: `secrets.enc.yaml` (commiteado en Git)

```yaml
#ENC[AES256_GCM,data:...,iv:...,tag:...,type:comment]
aemet_api_key: ENC[AES256_GCM,data:...,type:str]
anthropic_api_key: ENC[AES256_GCM,data:...,type:str]
# ... más secrets encriptados
sops:
    age:
        - recipient: age1<your_public_key_here>
          enc: |
            -----BEGIN AGE ENCRYPTED FILE-----
            ...
            -----END AGE ENCRYPTED FILE-----
```

---

## Instalación

### 1. Instalar SOPS y age

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y sops age

# Verify
sops --version  # 3.11.0+
age --version   # 1.1.1+
```

### 2. Generar Claves age (una sola vez)

```bash
mkdir -p .sops
age-keygen -o .sops/age-key.txt
cat .sops/age-key.txt
```

**Salida**:
```
# created: 2025-10-14T13:51:46+02:00
# public key: age1<your_public_key_here>
AGE-SECRET-KEY-<your_private_key_here>
```

⚠️ **IMPORTANTE**:
- `AGE-SECRET-KEY-...` → Añadir como secret `SOPS_AGE_KEY` en Forgejo
- `age1...` → Public key (usar para encriptar)
- `.sops/age-key.txt` → NUNCA commitear (está en `.gitignore`)

### 3. Crear y Encriptar Secrets

```bash
# Crear secrets.yaml plain
cat > .sops/secrets.yaml << EOF
aemet_api_key: "your_key_here"
anthropic_api_key: "your_key_here"
# ... más secrets
EOF

# Encriptar con age (usa tu public key generada)
export SOPS_AGE_RECIPIENTS=age1<your_public_key_here>
sops --encrypt --age $SOPS_AGE_RECIPIENTS .sops/secrets.yaml > secrets.enc.yaml

# Commitear archivo encriptado
git add secrets.enc.yaml
git commit -m "chore: add encrypted secrets"
```

---

## Flujo de Trabajo

### Desarrollo Local

#### 1. Desencriptar Secrets

```bash
# Usando script helper
./decrypt-secrets.sh

# O manualmente
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops --decrypt secrets.enc.yaml > .env
```

#### 2. Levantar Servicios

```bash
# Development
docker compose -f docker-compose.dev.yml up -d

# Production
docker compose -f docker-compose.prod.yml up -d
```

#### 3. Actualizar Secrets

```bash
# Editar secrets encriptados (abre editor)
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops secrets.enc.yaml

# O re-encriptar desde YAML plain
sops --encrypt --age $SOPS_AGE_RECIPIENTS .sops/secrets.yaml > secrets.enc.yaml

# Commitear cambios
git add secrets.enc.yaml
git commit -m "chore: update API keys"
git push origin develop
```

### Rotación de Claves

```bash
# Generar nueva clave age
age-keygen -o .sops/age-key-new.txt

# Rotar secrets con nueva clave
export NEW_PUBLIC_KEY=$(grep "public key:" .sops/age-key-new.txt | awk '{print $4}')
sops --rotate --age $NEW_PUBLIC_KEY secrets.enc.yaml

# Actualizar secret en Forgejo con nueva clave privada
# Settings → Secrets → SOPS_AGE_KEY → Update

# Commitear y desplegar
git add secrets.enc.yaml
git commit -m "chore: rotate encryption keys"
git push origin develop
```

---

## CI/CD Integration

### Forgejo Secret Configuration

1. Ir a repositorio en Forgejo: `http://localhost:3000/<your_user>/<your_repo>`
2. Settings → Secrets → Add Secret
3. Name: `SOPS_AGE_KEY`
4. Value: `AGE-SECRET-KEY-<your_private_key_here>` (de `.sops/age-key.txt`)
5. Save

### Pipeline Integration

**Archivo**: `.gitea/workflows/ci-cd-dual.yml`

```yaml
deploy-dev:
  runs-on: dev
  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Decrypt secrets with SOPS
      run: |
        # Install SOPS if not present
        if ! command -v sops &> /dev/null; then
          echo "📦 Installing SOPS..."
          sudo apt-get update && sudo apt-get install -y sops age
        fi

        # Decrypt secrets to .env file
        echo "🔓 Decrypting secrets..."
        echo "${{ secrets.SOPS_AGE_KEY }}" > /tmp/age-key.txt
        export SOPS_AGE_KEY_FILE=/tmp/age-key.txt
        sops --decrypt secrets.enc.yaml > .env
        rm /tmp/age-key.txt
        echo "✅ Secrets decrypted to .env"

    - name: Login to registry
      run: |
        REGISTRY_PASSWORD=$(grep "^registry_password:" .env | cut -d'"' -f2)
        REGISTRY_USER=$(grep "^registry_user:" .env | cut -d'"' -f2)
        echo "$REGISTRY_PASSWORD" | docker login localhost:5000 -u $REGISTRY_USER --password-stdin

    - name: Deploy to development
      run: |
        docker compose -f docker-compose.dev.yml down || true
        docker compose -f docker-compose.dev.yml up -d
```

---

## Troubleshooting

### Error: "no age key found"

**Causa**: SOPS no encuentra la clave privada

**Solución**:
```bash
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops --decrypt secrets.enc.yaml > .env
```

### Error: "failed to decrypt sops data key"

**Causa**: Clave age incorrecta o archivo corrupto

**Solución**:
```bash
# Verificar que la clave age coincide
cat .sops/age-key.txt | grep "public key"
grep "recipient:" secrets.enc.yaml
```

### Error: Variables no se cargan en Docker Compose

**Causa**: `.env` no existe o formato incorrecto

**Solución**:
```bash
# Verificar .env
cat .env | head -5

# Re-desencriptar
./decrypt-secrets.sh

# Verificar que docker-compose lee .env
docker compose -f docker-compose.dev.yml config | grep "aemet_api_key"
```

### CI/CD: SOPS no instalado en runner

**Causa**: Runners no tienen SOPS instalado

**Solución**: El pipeline instala automáticamente:
```yaml
if ! command -v sops &> /dev/null; then
  sudo apt-get update && sudo apt-get install -y sops age
fi
```

---

## Migración desde Docker Secrets

### Antes (Docker Secrets - NO FUNCIONA)

```yaml
# docker-compose.dev.yml
services:
  fastapi-app-dev:
    secrets:
      - aemet_api_key
      - anthropic_api_key
    environment:
      - AEMET_API_KEY_FILE=/run/secrets/aemet_api_key

secrets:
  aemet_api_key:
    file: ./docker/secrets/aemet_api_key.txt
```

**Problemas**:
- ❌ Secrets no accesibles por permisos UID/GID
- ❌ No funciona en Docker Compose
- ❌ 14 archivos individuales difíciles de gestionar

### Después (SOPS - FUNCIONA)

```yaml
# docker-compose.dev.yml
services:
  fastapi-app-dev:
    environment:
      - AEMET_API_KEY=${aemet_api_key}
      - ANTHROPIC_API_KEY=${anthropic_api_key}

# No secrets section needed
```

**Beneficios**:
- ✅ Variables de entorno desde `.env` desencriptado
- ✅ Una sola clave age en Forgejo Secret
- ✅ Secrets versionados de forma segura en Git

### Pasos de Migración

1. **Extraer secrets actuales**:
   ```bash
   # Script incluido
   .sops/create-secrets-yaml.sh
   ```

2. **Encriptar con SOPS**:
   ```bash
   export SOPS_AGE_RECIPIENTS=age1<your_public_key_here>
   sops --encrypt --age $SOPS_AGE_RECIPIENTS .sops/secrets.yaml > secrets.enc.yaml
   ```

3. **Actualizar docker-compose**:
   - Eliminar sección `secrets:`
   - Cambiar `*_FILE` por variables directas
   - Usar `${secret_name}` en environment

4. **Actualizar .gitignore**:
   ```gitignore
   # SOPS
   .sops/age-key.txt
   .sops/secrets.yaml
   .env
   ```

5. **Limpiar Docker Secrets (opcional)**:
   ```bash
   rm -rf docker/secrets/*.txt
   # Mantener solo README.md para documentación
   ```

---

## Referencias

- **SOPS GitHub**: https://github.com/getsops/sops
- **age Encryption**: https://github.com/FiloSottile/age
- **Sprint 12 Docs**: `.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`
- **CI/CD Pipeline**: `docs/CI_CD_PIPELINE.md`

---

**Última actualización**: 2025-10-14
**Versión**: 1.0
**Autor**: Sprint 12 - Forgejo CI/CD Implementation
