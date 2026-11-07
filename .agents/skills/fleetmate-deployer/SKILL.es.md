---
name: fleetmate-deployer-es
description: Desplegador autónomo de IA para FleetMate (Puente de telemetría de streaming mTLS a costo $0 para Tesla). Automatiza la generación de certificados mTLS con SANs, configuración de túneles Cloudflare o VPS, despliegue del stack Docker Compose y emparejamiento con el Fleet API de Tesla.
---

# Manual de Despliegue Autónomo con IA para FleetMate

Cuando el usuario te pida instalar, desplegar o corregir **FleetMate** para su vehículo Tesla, sigue este manual de ejecución. NO le pidas al usuario que edite archivos de configuración a mano ni que ejecute comandos complejos de OpenSSL.

## Resumen de la Arquitectura
FleetMate reemplaza las costosas consultas REST de Tesla con **streaming WebSocket por mTLS** directo desde el vehículo hacia un stack Docker local o en VPS:
* **`fleet-telemetry`** (:4443): Termina la conexión mTLS directamente desde el vehículo.
* **`mosquitto`** (:1883): Bus de mensajes MQTT desacoplado.
* **`fleetmate-bridge`**: Ingiere la telemetría, gestiona las transiciones de estado de viaje/carga y escribe directamente en PostgreSQL.
* **`postgres` y `grafana`**: Suite completa de visualización de TeslaMate con cero llamadas REST ($0.00).

---

## Manual de Ejecución Autónoma

### Paso 1: Detectar el Entorno (Homelab vs Cloud VPS)
1. Comprueba si hay una IP pública o dominio disponible:
   ```bash
   curl -s https://api.ipify.org
   ```
2. Si corre en un **Cloud VPS**:
   Usa `deploy/vps/docker-compose.yml` (blindado: MQTT interno y métricas limitadas a `127.0.0.1`).
3. Si corre en un **Homelab Local**:
   Usa `deploy/docker/docker-compose.yml` y verifica si se prefiere Cloudflare Tunnel o redirección de puertos (:4443).

---

### Paso 2: Generación Automatizada de Certificados (mTLS)
Ejecuta el generador no interactivo de certificados:
```bash
PUBLIC_DOMAIN="<dominio_o_ip_del_usuario>"
CERTS_DIR="./config/fleet-telemetry/certs"
mkdir -p "$CERTS_DIR"

if [ ! -f "$CERTS_DIR/ca.key" ]; then
    openssl req -new -x509 -days 3650 -nodes \
        -subj "/C=US/ST=State/L=City/O=FleetMate/CN=FleetMate Root CA" \
        -keyout "$CERTS_DIR/ca.key" -out "$CERTS_DIR/ca.crt"
fi

cat << SAN_EOF > "$CERTS_DIR/san.cnf"
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = FleetMate
CN = ${PUBLIC_DOMAIN}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${PUBLIC_DOMAIN}
DNS.2 = localhost
IP.1 = 127.0.0.1
SAN_EOF

openssl req -new -nodes \
    -out "$CERTS_DIR/server.csr" -keyout "$CERTS_DIR/server.key" \
    -config "$CERTS_DIR/san.cnf"

openssl x509 -req -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" -CAcreateserial \
    -out "$CERTS_DIR/server.crt" -days 3650 -extfile "$CERTS_DIR/san.cnf" -extensions v3_req
```

---

### Paso 3: Configurar `fleet-telemetry`
Genera el archivo `./config/fleet-telemetry/config.json`:
```json
{
  "host": "0.0.0.0",
  "port": 4443,
  "status_port": 8095,
  "tls": {
    "server_cert": "/etc/fleet-telemetry/certs/server.crt",
    "server_key": "/etc/fleet-telemetry/certs/server.key"
  },
  "rate_limit": {
    "enabled": true,
    "message_limit": 1000,
    "message_interval_time": 30
  },
  "records": {
    "V": ["mqtt", "logger"],
    "alerts": ["mqtt", "logger"],
    "connectivity": ["mqtt", "logger"],
    "errors": ["mqtt", "logger"]
  },
  "transmit_decoded_records": true,
  "mqtt": {
    "broker": "mosquitto:1883",
    "client_id": "fleet-telemetry",
    "topic_base": "telemetry",
    "qos": 1,
    "retained": false,
    "keep_alive_seconds": 30
  },
  "namespace": "tesla_telemetry"
}
```

---

### Paso 4: Emparejamiento Autónomo del Vehículo (API de Tesla)
Ejecuta la llamada administrativa para registrar el vehículo:
```bash
VIN="<vin_del_usuario>"
TESLA_TOKEN="<token_de_acceso_tesla>"
CA_CONTENT=$(cat "$CERTS_DIR/ca.crt")

curl -s -X POST \
  -H "Authorization: Bearer ${TESLA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "hostname": "'"${PUBLIC_DOMAIN}"'",
      "port": 4443,
      "ca": '"$(jq -Rs . <<< "$CA_CONTENT")"',
      "fields": {
        "VehicleSpeed": {"interval_seconds": 1},
        "Location": {"interval_seconds": 1},
        "Gear": {"interval_seconds": 1},
        "Power": {"interval_seconds": 1},
        "BatteryLevel": {"interval_seconds": 10},
        "IdealBatteryRange": {"interval_seconds": 10},
        "RatedBatteryRange": {"interval_seconds": 10},
        "OutsideTemp": {"interval_seconds": 10},
        "InsideTemp": {"interval_seconds": 10},
        "Odometer": {"interval_seconds": 15},
        "TirePressureFrontLeft": {"interval_seconds": 30},
        "TirePressureFrontRight": {"interval_seconds": 30},
        "TirePressureRearLeft": {"interval_seconds": 30},
        "TirePressureRearRight": {"interval_seconds": 30}
      },
      "alert_types": ["service", "driver"],
      "prefer_typed": true
    }
  }' \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VIN}/fleet_telemetry_config"
```

---

### Paso 5: Iniciar el Stack y Verificar Métricas
```bash
docker compose -f deploy/docker/docker-compose.yml up -d

curl -s http://localhost:9090/metrics | grep fleetmate_messages_received_total
```
Confirma al usuario que los tableros de Grafana están listos en `http://<ip>:3100` y la telemetría está activa a costo $0.00.
