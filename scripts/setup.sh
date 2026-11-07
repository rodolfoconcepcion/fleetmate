#!/usr/bin/env bash
# ==============================================================================
# FleetMate Zero-Assumption Turnkey Setup Wizard
# Generates valid mTLS certificates with SANs for your vehicle, creates
# Tesla Fleet Telemetry configs, and pairs your car in 1 clean step.
# ==============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}==============================================================================${NC}"
echo -e "${CYAN}🚘 FleetMate: Zero-Cost Tesla Fleet Telemetry Turnkey Initializer${NC}"
echo -e "${CYAN}==============================================================================${NC}"

read -r -p "Enter your public domain or Cloudflare Tunnel host (e.g. telemetry.example.com): " PUBLIC_HOST
read -r -p "Enter your 17-character Tesla VIN: " VIN
read -r -p "Enter your Tesla Fleet API Access Token: " TESLA_TOKEN

CERTS_DIR="./config/fleet-telemetry/certs"
mkdir -p "$CERTS_DIR"

echo -e "\n${YELLOW}Step 1/3: Generating Root CA & mTLS Server Certificates...${NC}"
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
    -config "$CERTS_DIR/san.cnf"

openssl x509 -req -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" -CAcreateserial \
    -out "$CERTS_DIR/server.crt" -days 3650 -extfile "$CERTS_DIR/san.cnf" -extensions v3_req

echo -e "${GREEN}✔ mTLS Certificates generated successfully.${NC}"

echo -e "\n${YELLOW}Step 2/3: Generating Fleet Telemetry Configuration...${NC}"
CONFIG_DIR="./config/fleet-telemetry"
cat << CONFIG_EOF > "$CONFIG_DIR/config.json"
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
CONFIG_EOF

echo -e "${GREEN}✔ fleet-telemetry configuration ready.${NC}"

echo -e "\n${YELLOW}Step 3/3: Pairing Vehicle (${VIN}) with ${PUBLIC_HOST}...${NC}"
CA_CONTENT=$(cat "$CERTS_DIR/ca.crt")

PAYLOAD=$(cat << JSON_PAYLOAD
{
  "config": {
    "hostname": "${PUBLIC_HOST}",
    "port": 4443,
    "ca": $(jq -Rs . <<< "$CA_CONTENT"),
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

RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer ${TESLA_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VIN}/fleet_telemetry_config" || true)

echo -e "Tesla API Response: ${RESPONSE}"

echo -e "\n${GREEN}==============================================================================${NC}"
echo -e "${GREEN}🎉 Setup Complete! Launch your stack with:${NC}"
echo -e "${CYAN}docker compose -f deploy/docker/docker-compose.yml up -d${NC}"
echo -e "${GREEN}==============================================================================${NC}"
