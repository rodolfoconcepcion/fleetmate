#!/usr/bin/env bash
# ==============================================================================
# 🚘 FleetMate: 1-Line Universal Cloud & Local Quick Installer
# Zero-clone, zero-assumption instant launcher with Automatic Discovery
# of existing TeslaMate, PostgreSQL, and MQTT brokers.
# ==============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

clear || true
echo -e "${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${CYAN}🚘 FLEETMATE: Zero-Cost Tesla Fleet Telemetry mTLS Streaming Stack${NC}"
echo -e "${CYAN}==============================================================================${NC}"
echo -e "Turnkey deployment for Tesla Model 3 (Highland), Model Y, Cybertruck, and Model S/X."
echo -e "Streams 1 Hz live telemetry directly into TeslaMate & Home Assistant at \$0.00 REST cost.\n"

# 1. Dependency checks (Docker & OpenSSL)
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker is not installed.${NC} Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command -v openssl &> /dev/null; then
    echo -e "${RED}[ERROR] OpenSSL is not installed.${NC} Please install openssl (e.g. sudo apt install openssl)."
    exit 1
fi

INSTALL_DIR="${FLEETMATE_DIR:-$HOME/fleetmate}"
echo -e "${GREEN}✔ Prerequisites verified. Target install directory: ${BOLD}${INSTALL_DIR}${NC}\n"

# 2. AUTO-DISCOVERY ENGINE: Detect Existing Services
echo -e "${YELLOW}🔍 Scanning system for existing services (TeslaMate, PostgreSQL, MQTT)...${NC}"

EXISTING_TESLAMATE_DB=""
EXISTING_MQTT_BROKER=""
USE_HYBRID_MODE=0

# Detect if any TeslaMate container or PostgreSQL is running
RUNNING_CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null || true)

if echo "$RUNNING_CONTAINERS" | grep -E -q 'teslamate.*db|teslamate.*postgres|teslamate-database'; then
    MATCHING_DB=$(echo "$RUNNING_CONTAINERS" | grep -E 'teslamate.*db|teslamate.*postgres|teslamate-database' | head -n1)
    echo -e "${GREEN}✔ Detected existing TeslaMate PostgreSQL container: ${BOLD}${MATCHING_DB}${NC}"
    EXISTING_TESLAMATE_DB="$MATCHING_DB"
    USE_HYBRID_MODE=1
fi

# Detect existing Mosquitto / MQTT Broker
if echo "$RUNNING_CONTAINERS" | grep -E -q 'mosquitto|mqtt|emqx'; then
    MATCHING_MQTT=$(echo "$RUNNING_CONTAINERS" | grep -E 'mosquitto|mqtt|emqx' | head -n1)
    echo -e "${GREEN}✔ Detected existing MQTT Broker container: ${BOLD}${MATCHING_MQTT}${NC}"
    EXISTING_MQTT_BROKER="$MATCHING_MQTT"
fi

if [ "$USE_HYBRID_MODE" -eq 1 ]; then
    echo -e "\n${CYAN}💡 Auto-Discovery Insight:${NC} Existing TeslaMate setup detected!"
    echo -e "FleetMate will attach seamlessly to your existing database & Grafana dashboards."
    echo -e "It will ${BOLD}NOT duplicate${NC} PostgreSQL or Grafana containers.\n"
    read -r -p "Attach to existing TeslaMate installation? [Y/n]: " ATTACH_CONFIRM
    ATTACH_CONFIRM=${ATTACH_CONFIRM:-Y}
    if [[ "$ATTACH_CONFIRM" =~ ^[Nn] ]]; then
        USE_HYBRID_MODE=0
        echo -e "${YELLOW}Proceeding with standalone full-stack mode (own DB + Grafana).${NC}"
    fi
fi

# 3. Interactive Input
read -r -p "Enter your public domain or VPS IP (e.g. telemetry.example.com): " PUBLIC_HOST
read -r -p "Enter your 17-character Tesla VIN: " VIN
read -r -p "Enter your Tesla Fleet API Access Token: " TESLA_TOKEN

# Detect if running on a Cloud VPS vs Homelab
IS_VPS=0
if curl -s -m 2 https://api.ipify.org | grep -q '^[0-9.]\+$'; then
    PUB_IP=$(curl -s https://api.ipify.org)
    if hostname -I 2>/dev/null | grep -q "$PUB_IP"; then
        IS_VPS=1
    fi
fi

mkdir -p "$INSTALL_DIR"/{config/fleet-telemetry/certs,config/mosquitto,data}
cd "$INSTALL_DIR"

# 4. Generate Root CA & mTLS Server Certificates
echo -e "\n${YELLOW}Generating Root CA & mTLS Server Certificates for ${PUBLIC_HOST}...${NC}"
CERTS_DIR="$INSTALL_DIR/config/fleet-telemetry/certs"

if [ ! -f "$CERTS_DIR/ca.key" ]; then
    openssl req -new -x509 -days 3650 -nodes \
        -subj "/C=US/ST=State/L=City/O=FleetMate/CN=FleetMate Root CA" \
        -keyout "$CERTS_DIR/ca.key" -out "$CERTS_DIR/ca.crt" >/dev/null 2>&1
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
CN = ${PUBLIC_HOST}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${PUBLIC_HOST}
DNS.2 = localhost
IP.1 = 127.0.0.1
SAN_EOF

openssl req -new -nodes \
    -out "$CERTS_DIR/server.csr" -keyout "$CERTS_DIR/server.key" \
    -config "$CERTS_DIR/san.cnf" >/dev/null 2>&1

openssl x509 -req -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" -CAcreateserial \
    -out "$CERTS_DIR/server.crt" -days 3650 -extfile "$CERTS_DIR/san.cnf" -extensions v3_req >/dev/null 2>&1

echo -e "${GREEN}✔ mTLS Certificates generated successfully.${NC}"

# 5. Determine MQTT target for fleet-telemetry
MQTT_TARGET_HOST="mosquitto:1883"
if [ "$USE_HYBRID_MODE" -eq 1 ] && [ -n "$EXISTING_MQTT_BROKER" ]; then
    # Try resolving host gateway or container IP
    MQTT_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$EXISTING_MQTT_BROKER" 2>/dev/null || echo "")
    if [ -n "$MQTT_IP" ]; then
        MQTT_TARGET_HOST="${MQTT_IP}:1883"
    fi
fi

# 6. Generate fleet-telemetry config
CONFIG_FILE="$INSTALL_DIR/config/fleet-telemetry/config.json"
cat << CONFIG_EOF > "$CONFIG_FILE"
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
    "broker": "${MQTT_TARGET_HOST}",
    "client_id": "fleet-telemetry",
    "topic_base": "telemetry",
    "qos": 1,
    "retained": false,
    "keep_alive_seconds": 30
  },
  "namespace": "tesla_telemetry"
}
CONFIG_EOF

echo -e "${GREEN}✔ fleet-telemetry configuration created.${NC}"

# 7. Select & Download the Appropriate Docker Compose Profile
COMPOSE_URL=""
if [ "$USE_HYBRID_MODE" -eq 1 ]; then
    echo -e "${CYAN}Configuring Hybrid Profile: injecting directly into existing TeslaMate DB.${NC}"
    COMPOSE_URL="https://raw.githubusercontent.com/rodolfoconcepcion/fleetmate/main/deploy/docker/docker-compose.hybrid.yml"
elif [ "$IS_VPS" -eq 1 ]; then
    echo -e "${CYAN}Public Cloud VPS detected: using hardened internal network profile.${NC}"
    COMPOSE_URL="https://raw.githubusercontent.com/rodolfoconcepcion/fleetmate/main/deploy/vps/docker-compose.yml"
else
    COMPOSE_URL="https://raw.githubusercontent.com/rodolfoconcepcion/fleetmate/main/deploy/docker/docker-compose.yml"
fi

curl -fsSL "$COMPOSE_URL" -o "$INSTALL_DIR/docker-compose.yml"

# If hybrid, write .env for database resolution
if [ "$USE_HYBRID_MODE" -eq 1 ]; then
    DB_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$EXISTING_TESLAMATE_DB" 2>/dev/null || echo "127.0.0.1")
    cat << ENV_EOF > "$INSTALL_DIR/.env"
FLEETMATE_POSTGRES_HOST=${DB_IP}
FLEETMATE_POSTGRES_PORT=5432
FLEETMATE_POSTGRES_USER=teslamate
FLEETMATE_POSTGRES_PASSWORD=teslamate_pwd_2026
FLEETMATE_POSTGRES_DB=teslamate
FLEETMATE_CAR_ID=1
ENV_EOF
fi

# 8. Pair Vehicle with Tesla Fleet API
echo -e "\n${YELLOW}Pairing vehicle (${VIN}) with ${PUBLIC_HOST}:4443...${NC}"
CA_ESCAPED=$(cat "$CERTS_DIR/ca.crt" | sed ':a;N;$!ba;s/\n/\\n/g')

PAYLOAD=$(cat << JSON_PAYLOAD
{
  "config": {
    "hostname": "${PUBLIC_HOST}",
    "port": 4443,
    "ca": "${CA_ESCAPED}",
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
}
JSON_PAYLOAD
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer ${TESLA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VIN}/fleet_telemetry_config" || true)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}✔ Vehicle successfully paired with Fleet Telemetry!${NC}"
else
    echo -e "${YELLOW}Notice: Tesla Fleet API responded with HTTP ${HTTP_CODE}: ${BODY}${NC}"
    echo -e "${YELLOW}(You can re-run pairing anytime once your Tesla Developer account is active).${NC}"
fi

# 9. Start the Docker Stack
echo -e "\n${YELLOW}Launching FleetMate Docker stack...${NC}"
docker compose -f "$INSTALL_DIR/docker-compose.yml" up -d

echo -e "\n${GREEN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}🎉 FleetMate is UP and RUNNING!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
if [ "$USE_HYBRID_MODE" -eq 1 ]; then
    echo -e "• Mode:                ${BOLD}${GREEN}HYBRID (Connected to existing TeslaMate DB)${NC}"
    echo -e "• Stream Bridge:       Active (1 Hz telemetry streaming into your existing Grafana)"
else
    echo -e "• Mode:                ${BOLD}${CYAN}STANDALONE (Turnkey full-stack)${NC}"
    echo -e "• Dashboard (Grafana): ${CYAN}http://${PUBLIC_HOST}:3100${NC} (or http://localhost:3100)"
fi
echo -e "• Prometheus Metrics:  ${CYAN}http://localhost:9090/metrics${NC}"
echo -e "• Config & Data:       ${CYAN}${INSTALL_DIR}${NC}\n"
