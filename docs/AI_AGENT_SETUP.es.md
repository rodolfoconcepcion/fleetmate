# Integración con Agentes de Inteligencia Artificial (Antigravity & Claude Code)

[English](AI_AGENT_SETUP.md) | [Español](AI_AGENT_SETUP.es.md)

FleetMate está diseñado de forma nativa para la era de la programación agéntica. Si utilizas herramientas como **Google Antigravity (AGY)**, **Claude Code**, **Cursor** o **Windsurf**, no necesitas configurar contenedores Docker a mano, generar certificados OpenSSL ni lidiar con comandos complejos.

Un agente de IA puede desplegar y configurar todo el stack de principio a fin de manera 100% autónoma.

---

## 🤖 Despliegue Autónomo con 1 Solo Mensaje (Prompt)

Simplemente abre el proyecto en tu asistente de IA y escribe:

> *"Configura FleetMate para mi Tesla (VIN: `5YJ...`, Token: `...`, Dominio: `telemetry.midominio.com`). Ejecuta el skill de despliegue y verifica el estado del stack."*

---

## 📦 Skills y Directivas de IA Incluidas

FleetMate incluye directivas agénticas pre-empaquetadas que le indican a cualquier IA cómo ejecutar cada paso de forma segura y sin interrupciones:

* **`.agents/skills/fleetmate-deployer/SKILL.es.md`:** 
  El manual de instrucciones agéntico para Google Antigravity y entornos de ejecución autónoma.
* **Integración nativa con `CLAUDE.md` / `AGENTS.md`:** 
  Incluye resolución automática de errores, aprovisionamiento de certificados sin pedir permisos manuales y validación segura del esquema PostgreSQL.

---

## 🛠️ Lo que el Agente de IA Realiza Automáticamente:

1. **Detección Automática del Entorno:** Identifica si estás ejecutando en un **Homelab Local** (detrás de un túnel Cloudflare o router casero) o en un **Cloud VPS** público con IP dedicada.
2. **Generación de Certificados mTLS:** Genera programáticamente el Root CA, la llave privada del servidor y los nombres alternativos de sujeto (SANs) necesarios para la conexión cifrada del carro.
3. **Emparejamiento del Vehículo:** Envía la llamada administrativa directamente al API de Tesla (`fleet_telemetry_config`) para ordenar al vehículo iniciar la transmisión.
4. **Despliegue y Verificación SRE:** Ejecuta `docker compose up -d`, consulta el endpoint de métricas de Prometheus (`:9090/metrics`) y confirma que la base de datos y los tópicos de MQTT estén saludables y recibiendo datos.
