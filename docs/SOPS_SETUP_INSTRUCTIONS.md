# 🔐 SOPS Setup - Pasos Finales

**Fecha**: 14 de Octubre, 2025
**Status**: ⚠️ **ACCIÓN REQUERIDA**

---

## ✅ Completado Automáticamente

Los siguientes pasos ya están implementados:

1. ✅ SOPS y age instalados (v3.11.0 / v1.1.1)
2. ✅ Claves age generadas en `.sops/age-key.txt`
3. ✅ Secrets extraídos de Docker Secrets
4. ✅ `secrets.enc.yaml` creado y encriptado
5. ✅ `.gitea/workflows/ci-cd-dual.yml` actualizado con desencriptación SOPS
6. ✅ `docker-compose.dev.yml` actualizado (Docker Secrets eliminados)
7. ✅ `docker-compose.prod.yml` actualizado (Docker Secrets eliminados)
8. ✅ `.gitignore` actualizado
9. ✅ Script `decrypt-secrets.sh` creado
10. ✅ Documentación completa en `docs/SOPS_SECRETS_MANAGEMENT.md`

---

## ⚠️ ACCIÓN REQUERIDA: Añadir Secret en Forgejo

### Paso 1: Obtener la Clave Privada age

```bash
cat .sops/age-key.txt | grep "AGE-SECRET-KEY"
```

**Output esperado**:
```
AGE-SECRET-KEY-<your_private_key_here>
```

### Paso 2: Añadir Secret en Forgejo UI

1. Abrir Forgejo en navegador:
   - URL: `http://localhost:3000/<your_user>/<your_repo>`
   - O tu dominio Tailscale: `https://<git-domain>.ts.net/<your_user>/<your_repo>`

2. Ir a **Settings** (arriba derecha)

3. En el menú lateral izquierdo, click en **Secrets**

4. Click botón **Add Secret**

5. Rellenar formulario:
   - **Name**: `SOPS_AGE_KEY`
   - **Value**: `AGE-SECRET-KEY-<your_private_key_here>` (tu clave del paso 1)

6. Click **Add Secret**

7. ✅ Verificar que aparece en la lista con nombre `SOPS_AGE_KEY`

---

## 📋 Opcional: Limpiar Docker Secrets

Una vez verificado que SOPS funciona en CI/CD, puedes eliminar los archivos de Docker Secrets:

```bash
# Eliminar archivos .txt de secrets (mantener README.md)
rm -f docker/secrets/*.txt

# Verificar que solo queda README.md
ls -la docker/secrets/
```

**⚠️ IMPORTANTE**: Solo ejecutar después de verificar que:
1. Secret `SOPS_AGE_KEY` está añadido en Forgejo
2. Pipeline CI/CD funciona correctamente con SOPS
3. Servicios locales se levantan con `.env` desencriptado

---

## 🧪 Testing

### Test 1: Desencriptación Local

```bash
# Limpiar .env anterior
rm -f .env

# Desencriptar con script
./decrypt-secrets.sh

# Verificar .env generado
head -5 .env
```

**Expected output**:
```
# Chocolate Factory Secrets - Plain YAML (to be encrypted with SOPS)
# DO NOT COMMIT THIS FILE UNENCRYPTED
aemet_api_key: <your_aemet_key_here>
anthropic_api_key: <your_anthropic_key_here>
influxdb_admin_password: <your_password_here>
```

### Test 2: Docker Compose con .env

```bash
# Development
docker compose -f docker-compose.dev.yml config | grep "aemet_api_key"

# Production
docker compose -f docker-compose.prod.yml config | grep "anthropic_api_key"
```

**Expected**: Variables correctamente interpoladas

### Test 3: CI/CD Pipeline

```bash
# Commitear cambios
git add secrets.enc.yaml .gitea/workflows/ci-cd-dual.yml docker-compose.dev.yml docker-compose.prod.yml
git commit -m "feat: implement SOPS secrets management"
git push origin develop
```

**Expected**:
1. Pipeline se ejecuta
2. Step "Decrypt secrets with SOPS" muestra: ✅ Secrets decrypted to .env
3. Deploy succeed

---

## 📚 Documentación

- **Guía completa**: `docs/SOPS_SECRETS_MANAGEMENT.md`
- **Sprint 12**: `.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`
- **CI/CD Pipeline**: `docs/CI_CD_PIPELINE.md`

---

## 🔧 Troubleshooting

### Error: "no age key found" en CI/CD

**Causa**: Secret `SOPS_AGE_KEY` no añadido en Forgejo

**Solución**: Seguir [Paso 2: Añadir Secret en Forgejo UI](#paso-2-añadir-secret-en-forgejo-ui)

### Error: Variables vacías en containers

**Causa**: `.env` no generado o formato incorrecto

**Solución**:
```bash
./decrypt-secrets.sh
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

---

**Siguiente paso**: Añadir `SOPS_AGE_KEY` en Forgejo UI siguiendo las instrucciones arriba 👆
