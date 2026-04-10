# Proyecto Futuro

## Objetivo

Desplegar la aplicacion como pagina web publica en una instancia de Google Compute Engine para mostrar resultados del pipeline (ranking, reportes y dashboard).

## Arquitectura objetivo

- VM en Google Compute Engine (Ubuntu 22.04 LTS)
- Aplicacion Streamlit corriendo como servicio systemd
- Nginx como reverse proxy en puertos 80/443
- Certificado TLS con Let's Encrypt
- Ejecucion automatica diaria del pipeline via cron o systemd timer
- Almacenamiento local inicial en VM para `project/data/`

## Fases

### Fase 1 - Infraestructura base (1 semana)

1. Crear proyecto en Google Cloud y habilitar facturacion.
2. Crear VM (e2-standard-2 o e2-standard-4 segun carga).
3. Configurar firewall para permitir HTTP/HTTPS y SSH restringido.
4. Instalar Python 3.10+, git, Nginx y certbot.

### Fase 2 - Aplicacion y servicio (1 semana)

1. Clonar repositorio y crear entorno virtual en la VM.
2. Configurar `.env` con proveedor LLM y parametros de ejecucion.
3. Probar `python main.py` y validar outputs en `project/data/`.
4. Ejecutar Streamlit como servicio systemd.
5. Configurar Nginx como proxy para exponer el dashboard.

### Fase 3 - Produccion web segura (1 semana)

1. Configurar dominio y DNS hacia IP publica de la VM.
2. Habilitar HTTPS con Let's Encrypt.
3. Endurecer seguridad (UFW, fail2ban, SSH con llave, usuario no-root).
4. Configurar logs y rotacion de logs.

### Fase 4 - Operacion automatizada (1 semana)

1. Programar `update_all.sh` diario con cron/systemd timer.
2. Generar alerta en caso de fallo (correo o webhook).
3. Definir backups diarios de `project/data/reports/`.
4. Documentar runbook de recuperacion.

## Backlog tecnico recomendado

- Separar capa de datos (CSV) de capa de presentacion (dashboard).
- Agregar endpoint API simple para publicar Top N en JSON.
- Incluir healthcheck (`/health`) y pagina de estado.
- Contenerizar con Docker para despliegues mas repetibles.
- Migrar a Cloud Run en fase posterior si se busca menor operacion manual.

## Riesgos y mitigacion

- Costos de VM y egress: usar alertas de presupuesto en Google Cloud.
- Exposicion de secretos: no subir `.env`, usar Secret Manager en etapa avanzada.
- Caidas por dependencia de proveedores externos: mantener fallback rule-based activo.
- Degradacion por crecimiento de datos: rotacion de archivos y archivado historico.

## Criterios de exito

- Dashboard accesible por dominio HTTPS 24/7.
- Pipeline diario ejecutado automaticamente sin intervencion manual.
- Reportes disponibles y descargables con convencion de nombres estable.
- Recuperacion documentada y reproducible ante fallas.
