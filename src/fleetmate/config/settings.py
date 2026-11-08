from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLEETMATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server / Healthcheck
    app_name: str = "fleetmate"
    host: str = "0.0.0.0"
    port: int = 8089
    metrics_port: int = 9090
    log_level: str = "INFO"

    # MQTT Ingestion (Subscribes to fleet-telemetry output)
    mqtt_broker: str = Field(default="localhost", description="MQTT broker host")
    mqtt_port: int = Field(default=1883, description="MQTT broker port")
    mqtt_username: str | None = Field(default=None, description="MQTT username")
    mqtt_password: str | None = Field(default=None, description="MQTT password")
    mqtt_topic: str = Field(
        default="telemetry/tesla_telemetry/#",
        description="MQTT topic wildcard for incoming vehicle telemetry",
    )
    mqtt_client_id: str = "fleetmate-bridge"

    # Home Assistant MQTT Publishing (Optional Live Discovery)
    ha_discovery_enabled: bool = True
    ha_topic_prefix: str = "homeassistant"

    # TeslaMate Database Integration (Direct High-Speed asyncpg)
    postgres_host: str = Field(default="database", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="teslamate", description="PostgreSQL username")
    postgres_password: str = Field(default="teslamate_pwd_2026", description="PostgreSQL password")
    postgres_db: str = Field(default="teslamate", description="PostgreSQL database")
    postgres_pool_min_size: int = 2
    postgres_pool_max_size: int = 10

    # Ingestion & State Machine Engine Settings
    car_id: int = Field(default=1, description="TeslaMate internal car ID")
    vin: str = Field(default="", description="Vehicle VIN")
    min_drive_duration_seconds: int = 30
    drive_idle_timeout_seconds: int = 300
    batch_flush_interval_seconds: float = 1.0
    batch_max_size: int = 50

    # Reverse Geocoding (OpenStreetMap Nominatim)
    geocoding_enabled: bool = Field(
        default=True, description="Enable asynchronous Nominatim reverse geocoding"
    )
    nominatim_base_url: str = Field(
        default="https://nominatim.openstreetmap.org",
        description="OpenStreetMap Nominatim API base URL",
    )
    nominatim_user_agent: str = Field(
        default="FleetMate/0.1.0 (Open-Source Telemetry Bridge)",
        description="Custom User-Agent header required by Nominatim usage policy",
    )
    nominatim_rate_limit_seconds: float = Field(
        default=1.1,
        description="Minimum delay in seconds between Nominatim API requests",
    )


settings = Settings()
