---
name: fleetmate-deployer
description: Turnkey AI autonomous deployer for FleetMate (Zero-cost Tesla Fleet Telemetry streaming bridge). Automates mTLS SAN certificate generation, Cloudflare tunnel or VPS ingress setup, Docker Compose stack deployment, and Tesla Fleet API vehicle pairing.
---

# FleetMate Autonomous AI Setup Skill

When the user asks you to set up, deploy, or fix **FleetMate** for their Tesla vehicle, follow this automated playbook. Do NOT ask the user to manually edit configuration files or run complex OpenSSL commands.

## Architecture Overview
FleetMate replaces high-cost Tesla REST polling with official **mTLS WebSocket streaming** directly from the vehicle into a self-hosted or VPS Docker stack:
* **`fleet-telemetry`** (:4443): Terminated mTLS directly from vehicle.
* **`mosquitto`** (:1883): Decoupled MQTT message bus.
* **`fleetmate-bridge`**: Ingests telemetry, manages trip/charge state transitions, and writes directly into PostgreSQL.
* **`postgres` & `grafana`**: Complete TeslaMate dashboard suite with zero REST calls ($0.00).

---

## Autonomous Execution Playbook

### Step 1: Detect Environment (Homelab vs Cloud VPS)
1. Check if public IP or domain is available:
   ```bash
   curl -s https://api.ipify.org
   ```
2. If running on a **Cloud VPS**:
   Use `deploy/vps/docker-compose.yml` (hardened: internal MQTT and metrics bound to `127.0.0.1`).
3. If running on a **Local Homelab**:
   Use `deploy/docker/docker-compose.yml` and check if Cloudflare tunnel or router port forwarding (:4443) is preferred.

---

### Step 2: Automated Certificate Generation (mTLS)
Run the automated non-interactive certificate builder:
```bash
PUBLIC_DOMAIN="<user_domain_or_ip>"
CERTS_DIR="./config/fleet-telemetry/certs"
mkdir -p "$CERTS_DIR"

# Generate Root CA if missing
if [ ! -f "$CERTS_DIR/ca.key" ]; then
    openssl req -new -x509 -days 3650 -nodes \
        -subj "/C=US/ST=State/L=City/O=FleetMate/CN=FleetMate Root CA" \
        -keyout "$CERTS_DIR/ca.key" -out "$CERTS_DIR/ca.crt"
fi

# Build SAN config
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

### Step 3: Configure `fleet-telemetry`
Generate `./config/fleet-telemetry/config.json`:
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

### Step 4: Autonomous Vehicle Pairing (Tesla API)
Execute the single administrative pairing call to register the car:
```bash
VIN="<user_vin>"
TESLA_TOKEN="<tesla_access_token>"
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

### Step 5: Launch Stack & Healthcheck
```bash
# Start Docker stack
docker compose -f deploy/docker/docker-compose.yml up -d

# Verify metrics
curl -s http://localhost:9090/metrics | grep fleetmate_messages_received_total
```
Confirm to the user that live Grafana dashboards are ready at `http://<ip>:3100` and telemetry streaming is active at $0.00 cost.
