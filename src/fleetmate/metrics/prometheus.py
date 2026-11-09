from prometheus_client import Counter, Gauge, Histogram

MESSAGES_RECEIVED = Counter(
    "fleetmate_messages_received_total",
    "Total incoming telemetry MQTT messages received from fleet-telemetry",
    ["status"],
)

POSITIONS_INSERTED = Counter(
    "fleetmate_positions_inserted_total",
    "Total positions written directly to TeslaMate PostgreSQL",
    ["status"],
)

DRIVES_DETECTED = Counter(
    "fleetmate_drives_detected_total",
    "Total driving sessions initiated and finalized by StateMachineEngine",
    ["event"],
)

CHARGES_DETECTED = Counter(
    "fleetmate_charges_detected_total",
    "Total charging sessions initiated and finalized by StateMachineEngine",
    ["event"],
)

CURRENT_VEHICLE_SPEED = Gauge(
    "fleetmate_vehicle_speed_kmh",
    "Current live speed of the vehicle in km/h",
)

CURRENT_BATTERY_LEVEL = Gauge(
    "fleetmate_vehicle_battery_level_percent",
    "Current state of charge percentage",
)

DB_LATENCY = Histogram(
    "fleetmate_db_insert_duration_seconds",
    "Database write latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

GEOCODING_REQUESTS = Counter(
    "fleetmate_geocoding_requests_total",
    "Total reverse geocoding requests executed against Nominatim",
    ["status"],
)

GEOFENCE_MATCHES = Counter(
    "fleetmate_geofence_matches_total",
    "Total drive and charging locations matched against configured geofences",
    ["context"],
)
