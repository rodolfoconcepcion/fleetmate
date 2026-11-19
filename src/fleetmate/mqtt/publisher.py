import json
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from fleetmate.config.settings import settings
from fleetmate.telemetry.models import VehicleTelemetryPoint

logger = logging.getLogger(__name__)


class MQTTPublishClient(Protocol):
    async def publish(
        self,
        topic: str,
        payload: str | bytes | None = None,
        qos: int = 0,
        retain: bool = False,
    ) -> Any:
        """Publish an MQTT message to the broker."""


def _fmt_bool(val: bool) -> str:
    return "true" if val else "false"


def _fmt_num(val: int | float | Decimal) -> str:
    if isinstance(val, Decimal):
        return format(val.normalize(), "f") if val == val.to_integral() else str(val)
    return str(val)


def build_ha_discovery_payload(
    car_id: int,
    prefix: str,
    vehicle_name: str,
    vehicle_model: str,
    public_url: str,
) -> dict[str, Any]:
    """Builds a Home Assistant MQTT Device Discovery payload under the FleetMate namespace."""
    base = f"{prefix}/cars/{car_id}"
    uid_prefix = f"fleetmate_{car_id}"
    obj_prefix = re.sub(r"[^a-z0-9]+", "_", vehicle_name.lower()).strip("_") or f"car_{car_id}"

    def sensor(
        key: str,
        name: str,
        state_subtopic: str | None = None,
        *,
        icon: str | None = None,
        device_class: str | None = None,
        unit: str | None = None,
        state_class: str | None = None,
        precision: int | None = None,
        value_template: str | None = None,
        entity_category: str | None = None,
    ) -> dict[str, Any]:
        comp: dict[str, Any] = {
            "platform": "sensor",
            "name": name,
            "unique_id": f"{uid_prefix}_{key}",
            "object_id": f"{obj_prefix}_{key}",
            "state_topic": f"{base}/{state_subtopic or key}",
        }
        if icon:
            comp["icon"] = icon
        if device_class:
            comp["device_class"] = device_class
        if unit:
            comp["unit_of_measurement"] = unit
        if state_class:
            comp["state_class"] = state_class
        if precision is not None:
            comp["suggested_display_precision"] = precision
        if value_template:
            comp["value_template"] = value_template
        if entity_category:
            comp["entity_category"] = entity_category
        return comp

    def binary_sensor(
        key: str,
        name: str,
        state_subtopic: str | None = None,
        *,
        icon: str | None = None,
        device_class: str | None = None,
        payload_on: str = "true",
        payload_off: str = "false",
        value_template: str | None = None,
        entity_category: str | None = None,
    ) -> dict[str, Any]:
        comp: dict[str, Any] = {
            "platform": "binary_sensor",
            "name": name,
            "unique_id": f"{uid_prefix}_{key}",
            "object_id": f"{obj_prefix}_{key}",
            "state_topic": f"{base}/{state_subtopic or key}",
            "payload_on": payload_on,
            "payload_off": payload_off,
        }
        if icon:
            comp["icon"] = icon
        if device_class:
            comp["device_class"] = device_class
        if value_template:
            comp["value_template"] = value_template
        if entity_category:
            comp["entity_category"] = entity_category
        return comp

    def lock(
        key: str,
        name: str,
        state_subtopic: str,
        command_subtopic: str,
        *,
        icon: str = "mdi:car-door-lock",
    ) -> dict[str, Any]:
        return {
            "platform": "lock",
            "name": name,
            "unique_id": f"{uid_prefix}_{key}",
            "object_id": f"{obj_prefix}_{key}",
            "state_topic": f"{base}/{state_subtopic}",
            "command_topic": f"{base}/cmd/{command_subtopic}",
            "payload_lock": "LOCK",
            "payload_unlock": "UNLOCK",
            "state_locked": "true",
            "state_unlocked": "false",
            "icon": icon,
        }

    def switch(
        key: str,
        name: str,
        state_subtopic: str,
        command_subtopic: str,
        *,
        icon: str,
        value_template: str | None = None,
        optimistic: bool = False,
    ) -> dict[str, Any]:
        comp: dict[str, Any] = {
            "platform": "switch",
            "name": name,
            "unique_id": f"{uid_prefix}_{key}",
            "object_id": f"{obj_prefix}_{key}",
            "state_topic": f"{base}/{state_subtopic}",
            "command_topic": f"{base}/cmd/{command_subtopic}",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "true",
            "state_off": "false",
            "icon": icon,
        }
        if value_template:
            comp["value_template"] = value_template
        if optimistic:
            comp["optimistic"] = True
        return comp

    def number(
        key: str,
        name: str,
        state_subtopic: str,
        command_subtopic: str,
        *,
        min_val: int,
        max_val: int,
        step: int = 1,
        unit: str | None = None,
        mode: str = "slider",
        icon: str,
        optimistic: bool = False,
    ) -> dict[str, Any]:
        comp: dict[str, Any] = {
            "platform": "number",
            "name": name,
            "unique_id": f"{uid_prefix}_{key}",
            "object_id": f"{obj_prefix}_{key}",
            "state_topic": f"{base}/{state_subtopic}",
            "command_topic": f"{base}/cmd/{command_subtopic}",
            "min": min_val,
            "max": max_val,
            "step": step,
            "mode": mode,
            "icon": icon,
        }
        if unit:
            comp["unit_of_measurement"] = unit
        if optimistic:
            comp["optimistic"] = True
        return comp

    def button(
        key: str,
        name: str,
        command_subtopic: str,
        *,
        icon: str,
        entity_category: str | None = None,
    ) -> dict[str, Any]:
        comp: dict[str, Any] = {
            "platform": "button",
            "name": name,
            "unique_id": f"{uid_prefix}_{key}",
            "object_id": f"{obj_prefix}_{key}",
            "command_topic": f"{base}/cmd/{command_subtopic}",
            "payload_press": "PRESS",
            "icon": icon,
        }
        if entity_category:
            comp["entity_category"] = entity_category
        return comp

    components: dict[str, Any] = {
        "display_name": sensor("display_name", "Display Name", icon="mdi:car"),
        "state": sensor(
            "state",
            "State",
            icon="mdi:car-connected",
            value_template="{{ value | title }}",
        ),
        "since": sensor("since", "Since", device_class="timestamp", icon="mdi:clock-outline"),
        "healthy": binary_sensor(
            "healthy", "Health", device_class="connectivity", entity_category="diagnostic"
        ),
        "battery_level": sensor(
            "battery_level",
            "Battery",
            device_class="battery",
            unit="%",
            state_class="measurement",
        ),
        "usable_battery_level": sensor(
            "usable_battery_level",
            "Usable Battery",
            device_class="battery",
            unit="%",
            state_class="measurement",
        ),
        "rated_battery_range": sensor(
            "rated_battery_range",
            "Range (Rated)",
            state_subtopic="rated_battery_range_km",
            icon="mdi:map-marker-distance",
            device_class="distance",
            unit="km",
            state_class="measurement",
            precision=0,
        ),
        "ideal_battery_range": sensor(
            "ideal_battery_range",
            "Range (Ideal)",
            state_subtopic="ideal_battery_range_km",
            icon="mdi:map-marker-distance",
            device_class="distance",
            unit="km",
            state_class="measurement",
            precision=0,
        ),
        "est_battery_range": sensor(
            "est_battery_range",
            "Range (Estimated)",
            state_subtopic="est_battery_range_km",
            icon="mdi:map-marker-distance",
            device_class="distance",
            unit="km",
            state_class="measurement",
            precision=0,
        ),
        "odometer": sensor(
            "odometer",
            "Odometer",
            icon="mdi:counter",
            device_class="distance",
            unit="km",
            state_class="total_increasing",
            precision=0,
        ),
        "geofence": sensor("geofence", "Geofence", icon="mdi:earth"),
        "latitude": sensor("latitude", "Latitude", icon="mdi:latitude", precision=6),
        "longitude": sensor("longitude", "Longitude", icon="mdi:longitude", precision=6),
        "speed": sensor(
            "speed",
            "Speed",
            icon="mdi:speedometer",
            device_class="speed",
            unit="km/h",
            state_class="measurement",
            precision=0,
        ),
        "power": sensor(
            "power",
            "Power",
            device_class="power",
            unit="kW",
            state_class="measurement",
            precision=0,
        ),
        "shift_state": sensor("shift_state", "Shift State", icon="mdi:car-shift-pattern"),
        "heading": sensor("heading", "Heading", icon="mdi:compass", unit="°"),
        "elevation": sensor(
            "elevation", "Elevation", icon="mdi:elevation-rise", device_class="distance", unit="m"
        ),
        "inside_temp": sensor(
            "inside_temp",
            "Temperature (Inside)",
            icon="mdi:thermometer-lines",
            device_class="temperature",
            unit="°C",
            state_class="measurement",
            precision=1,
        ),
        "outside_temp": sensor(
            "outside_temp",
            "Temperature (Outside)",
            icon="mdi:thermometer",
            device_class="temperature",
            unit="°C",
            state_class="measurement",
            precision=1,
        ),
        "is_climate_on": binary_sensor(
            "is_climate_on", "Climate", icon="mdi:air-conditioner", device_class="running"
        ),
        "is_preconditioning": binary_sensor(
            "is_preconditioning", "Preconditioning", icon="mdi:air-conditioner"
        ),
        "climate_keeper_mode": sensor(
            "climate_keeper_mode",
            "Climate Keeper",
            icon="mdi:air-conditioner",
            value_template="{{ value | title }}",
        ),
        "locked": binary_sensor(
            "locked",
            "Lock",
            device_class="lock",
            payload_on="false",
            payload_off="true",
        ),
        "doors_open": binary_sensor("doors_open", "Doors", icon="mdi:car-door", device_class="door"),
        "driver_front_door_open": binary_sensor(
            "driver_front_door_open", "Door (Driver Front)", icon="mdi:car-door", device_class="door"
        ),
        "passenger_front_door_open": binary_sensor(
            "passenger_front_door_open",
            "Door (Passenger Front)",
            icon="mdi:car-door",
            device_class="door",
        ),
        "driver_rear_door_open": binary_sensor(
            "driver_rear_door_open", "Door (Driver Rear)", icon="mdi:car-door", device_class="door"
        ),
        "passenger_rear_door_open": binary_sensor(
            "passenger_rear_door_open",
            "Door (Passenger Rear)",
            icon="mdi:car-door",
            device_class="door",
        ),
        "windows_open": binary_sensor(
            "windows_open", "Windows", icon="mdi:car-door", device_class="window"
        ),
        "driver_front_window_open": binary_sensor(
            "driver_front_window_open",
            "Window (Driver Front)",
            icon="mdi:car-door",
            device_class="window",
        ),
        "passenger_front_window_open": binary_sensor(
            "passenger_front_window_open",
            "Window (Passenger Front)",
            icon="mdi:car-door",
            device_class="window",
        ),
        "driver_rear_window_open": binary_sensor(
            "driver_rear_window_open",
            "Window (Driver Rear)",
            icon="mdi:car-door",
            device_class="window",
        ),
        "passenger_rear_window_open": binary_sensor(
            "passenger_rear_window_open",
            "Window (Passenger Rear)",
            icon="mdi:car-door",
            device_class="window",
        ),
        "trunk_open": binary_sensor("trunk_open", "Trunk", icon="mdi:car-back", device_class="opening"),
        "frunk_open": binary_sensor("frunk_open", "Frunk", icon="mdi:car", device_class="opening"),
        "sentry_mode": binary_sensor("sentry_mode", "Sentry Mode", icon="mdi:cctv"),
        "is_user_present": binary_sensor(
            "is_user_present", "User Present", device_class="presence"
        ),
        "park_brake": binary_sensor(
            "park_brake",
            "Parking Brake",
            state_subtopic="shift_state",
            icon="mdi:car-brake-parking",
            payload_on="ON",
            payload_off="OFF",
            value_template="{% if value in ['', 'P'] %}ON{% elif value in ['D', 'N', 'R'] %}OFF{% else %}OFF{% endif %}",
        ),
        "charging": binary_sensor(
            "charging",
            "Charging",
            state_subtopic="charging_state",
            device_class="battery_charging",
            payload_on="ON",
            payload_off="OFF",
            value_template="{% if value in ['Charging', 'Starting', 'DetailedChargeStateCharging', 'DetailedChargeStateStarting'] %}ON{% else %}OFF{% endif %}",
        ),
        "charging_state": sensor(
            "charging_state",
            "Charging State",
            icon="mdi:ev-station",
            value_template="{{ value | regex_replace('(?<=[a-z])(?=[A-Z])', ' ') }}",
        ),
        "charger_power": sensor(
            "charger_power",
            "Charger Power",
            device_class="power",
            unit="kW",
            state_class="measurement",
            precision=0,
        ),
        "charger_voltage": sensor(
            "charger_voltage",
            "Charger Voltage",
            device_class="voltage",
            unit="V",
            state_class="measurement",
            precision=0,
        ),
        "charger_actual_current": sensor(
            "charger_actual_current",
            "Charger Actual Current",
            device_class="current",
            unit="A",
            state_class="measurement",
            precision=0,
        ),
        "charge_energy_added": sensor(
            "charge_energy_added",
            "Charge Energy Added",
            device_class="energy",
            unit="kWh",
            state_class="total_increasing",
            precision=2,
        ),
        "charge_limit_soc": sensor(
            "charge_limit_soc",
            "Charge Limit",
            icon="mdi:battery-charging-80",
            unit="%",
            state_class="measurement",
        ),
        "charge_current_request": sensor(
            "charge_current_request",
            "Charge Current Request",
            device_class="current",
            unit="A",
        ),
        "charge_port_door_open": binary_sensor(
            "charge_port_door_open",
            "Charge Port",
            icon="mdi:ev-plug-tesla",
            device_class="opening",
        ),
        "plugged_in": binary_sensor(
            "plugged_in", "Plugged In", icon="mdi:power-plug", device_class="plug"
        ),
        "time_to_full_charge": sensor(
            "time_to_full_charge",
            "Time To Full Charge",
            device_class="duration",
            unit="h",
            precision=2,
        ),
        "tpms_pressure_fl": sensor(
            "tpms_pressure_fl",
            "Tire Pressure (Front Left)",
            icon="mdi:gauge",
            device_class="pressure",
            unit="bar",
            state_class="measurement",
            precision=1,
        ),
        "tpms_pressure_fr": sensor(
            "tpms_pressure_fr",
            "Tire Pressure (Front Right)",
            icon="mdi:gauge",
            device_class="pressure",
            unit="bar",
            state_class="measurement",
            precision=1,
        ),
        "tpms_pressure_rl": sensor(
            "tpms_pressure_rl",
            "Tire Pressure (Rear Left)",
            icon="mdi:gauge",
            device_class="pressure",
            unit="bar",
            state_class="measurement",
            precision=1,
        ),
        "tpms_pressure_rr": sensor(
            "tpms_pressure_rr",
            "Tire Pressure (Rear Right)",
            icon="mdi:gauge",
            device_class="pressure",
            unit="bar",
            state_class="measurement",
            precision=1,
        ),
        "tpms_soft_warning_fl": binary_sensor(
            "tpms_soft_warning_fl",
            "Tire Pressure Warning (Front Left)",
            device_class="problem",
        ),
        "tpms_soft_warning_fr": binary_sensor(
            "tpms_soft_warning_fr",
            "Tire Pressure Warning (Front Right)",
            device_class="problem",
        ),
        "tpms_soft_warning_rl": binary_sensor(
            "tpms_soft_warning_rl",
            "Tire Pressure Warning (Rear Left)",
            device_class="problem",
        ),
        "tpms_soft_warning_rr": binary_sensor(
            "tpms_soft_warning_rr",
            "Tire Pressure Warning (Rear Right)",
            device_class="problem",
        ),
        "version": sensor(
            "version", "Version", icon="mdi:alphabetical", entity_category="diagnostic"
        ),
        "update": {
            "platform": "update",
            "name": "Update",
            "unique_id": f"{uid_prefix}_update",
            "object_id": f"{obj_prefix}_update",
            "state_topic": f"{base}/version",
            "latest_version_topic": f"{base}/update_version",
            "entity_category": "diagnostic",
            "icon": "mdi:car-cog",
        },
        "location": {
            "platform": "device_tracker",
            "name": None,
            "icon": "mdi:crosshairs-gps",
            "unique_id": f"{uid_prefix}_location",
            "object_id": f"{obj_prefix}_location",
            "json_attributes_topic": f"{base}/location",
        },
        "raw_location": sensor(
            "raw_location",
            "Location",
            state_subtopic="location",
            icon="mdi:crosshairs-gps",
            entity_category="diagnostic",
        ),
        "door_lock": lock("door_lock", "Door Lock", "locked", "door_lock"),
        "sentry_control": switch(
            "sentry_control",
            "Sentry Control",
            "sentry_mode",
            "sentry",
            icon="mdi:shield-car",
        ),
        "charging_control": switch(
            "charging_control",
            "Charging Control",
            "charging_state",
            "charging",
            icon="mdi:ev-station",
            value_template="{{ 'true' if value == 'Charging' else 'false' }}",
        ),
        "climate_control": switch(
            "climate_control",
            "Climate Control",
            "is_climate_on",
            "climate",
            icon="mdi:fan",
        ),
        "charge_port_control": switch(
            "charge_port_control",
            "Charge Port Control",
            "charge_port_door_open",
            "charge_port",
            icon="mdi:ev-plug-tesla",
        ),
        "steering_wheel_heater": switch(
            "steering_wheel_heater",
            "Steering Wheel Heater",
            "wheel_heater_state",
            "wheel_heater",
            icon="mdi:steering",
            optimistic=True,
        ),
        "charge_limit_target": number(
            "charge_limit_target",
            "Charge Limit Target",
            "charge_limit_soc",
            "charge_limit",
            min_val=50,
            max_val=100,
            step=1,
            unit="%",
            icon="mdi:battery-charging-80",
        ),
        "charge_amps_target": number(
            "charge_amps_target",
            "Charge Amps Target",
            "charge_current_request",
            "charge_amps",
            min_val=5,
            max_val=48,
            step=1,
            unit="A",
            icon="mdi:current-ac",
        ),
        "cabin_temp_target": number(
            "cabin_temp_target",
            "Cabin Temp Target",
            "cabin_temp_target_f",
            "cabin_temp_f",
            min_val=60,
            max_val=85,
            step=1,
            unit="°F",
            mode="box",
            icon="mdi:thermometer",
            optimistic=True,
        ),
        "seat_heater_driver": number(
            "seat_heater_driver",
            "Seat Heater Driver",
            "seat_heater_driver",
            "seat_heater_driver",
            min_val=0,
            max_val=3,
            step=1,
            icon="mdi:car-seat-heater",
            optimistic=True,
        ),
        "seat_heater_passenger": number(
            "seat_heater_passenger",
            "Seat Heater Passenger",
            "seat_heater_passenger",
            "seat_heater_passenger",
            min_val=0,
            max_val=3,
            step=1,
            icon="mdi:car-seat-heater",
            optimistic=True,
        ),
        "vent_windows": button(
            "vent_windows", "Vent Windows", "windows_vent", icon="mdi:window-open"
        ),
        "close_windows": button(
            "close_windows", "Close Windows", "windows_close", icon="mdi:window-closed"
        ),
        "open_frunk": button(
            "open_frunk", "Open Frunk", "open_frunk", icon="mdi:car-hood"
        ),
        "open_trunk": button(
            "open_trunk", "Open Trunk", "open_trunk", icon="mdi:car-back"
        ),
        "flash_lights": button(
            "flash_lights", "Flash Lights", "flash_lights", icon="mdi:car-light-high"
        ),
        "honk_horn": button(
            "honk_horn", "Honk Horn", "honk_horn", icon="mdi:bugle"
        ),
        "wake_up": button(
            "wake_up", "Wake Up", "wake", icon="mdi:power-sleep"
        ),
        "install_software_update": button(
            "install_software_update",
            "Install Software Update",
            "schedule_software_update",
            icon="mdi:update",
            entity_category="config",
        ),
    }

    return {
        "device": {
            "name": vehicle_name,
            "model": vehicle_model,
            "identifiers": [f"fleetmate_car_{car_id}"],
            "manufacturer": "Tesla",
            "configuration_url": public_url,
        },
        "origin": {
            "name": "FleetMate",
            "sw_version": "0.5.0",
            "support_url": "https://github.com/rodolfoconcepcion/fleetmate",
        },
        "components": components,
    }


class StateMQTTPublisher:
    """Publishes normalized vehicle state and Home Assistant MQTT discovery."""

    def __init__(
        self,
        car_id: int = settings.car_id,
        prefix: str = settings.mqtt_publish_prefix,
        ha_prefix: str = settings.ha_topic_prefix,
        ha_discovery_enabled: bool = settings.ha_discovery_enabled,
        enabled: bool = settings.mqtt_publish_enabled,
        vehicle_name: str = settings.vehicle_name,
        vehicle_model: str = settings.vehicle_model,
        public_url: str = settings.public_url,
    ) -> None:
        self.car_id = car_id
        self.prefix = prefix.strip("/")
        self.ha_prefix = ha_prefix.strip("/")
        self.ha_discovery_enabled = ha_discovery_enabled
        self.enabled = enabled
        self.vehicle_name = vehicle_name
        self.vehicle_model = vehicle_model
        self.public_url = public_url
        self._client: MQTTPublishClient | None = None
        self._last_state: str | None = None
        self._last_state_since: datetime | None = None

    def set_client(self, client: MQTTPublishClient | None) -> None:
        self._client = client

    def _base_topic(self) -> str:
        return f"{self.prefix}/cars/{self.car_id}"

    async def publish_discovery(self, client: MQTTPublishClient | None = None) -> None:
        target = client or self._client
        if not self.enabled or target is None:
            return

        base = self._base_topic()
        if self.ha_discovery_enabled:
            payload = build_ha_discovery_payload(
                car_id=self.car_id,
                prefix=self.prefix,
                vehicle_name=self.vehicle_name,
                vehicle_model=self.vehicle_model,
                public_url=self.public_url,
            )
            discovery_topic = f"{self.ha_prefix}/device/fleetmate_{self.car_id}/config"
            await target.publish(discovery_topic, json.dumps(payload), qos=1, retain=True)
            logger.info("Published Home Assistant MQTT Discovery to %s", discovery_topic)

        await target.publish(f"{base}/display_name", self.vehicle_name, qos=1, retain=True)
        await target.publish(f"{base}/model", self.vehicle_model, qos=1, retain=True)
        await target.publish(f"{base}/healthy", "true", qos=1, retain=True)

    def build_state_messages(
        self,
        point: VehicleTelemetryPoint,
        vehicle_state: str,
        *,
        geofence_name: str | None = None,
        charger_power_kw: int | None = None,
        charge_energy_added: Decimal | None = None,
    ) -> dict[str, str]:
        """Builds a mapping of `{topic: payload}` for non-null telemetry fields."""
        base = self._base_topic()
        out: dict[str, str] = {}

        if vehicle_state != self._last_state:
            self._last_state = vehicle_state
            self._last_state_since = point.timestamp.astimezone(UTC)
            out[f"{base}/since"] = self._last_state_since.isoformat().replace("+00:00", "Z")
        out[f"{base}/state"] = vehicle_state
        out[f"{base}/healthy"] = "true"

        if point.latitude is not None and point.longitude is not None:
            lat_f = float(point.latitude)
            lon_f = float(point.longitude)
            out[f"{base}/latitude"] = str(point.latitude)
            out[f"{base}/longitude"] = str(point.longitude)
            out[f"{base}/location"] = json.dumps({"latitude": lat_f, "longitude": lon_f})

        if geofence_name is not None:
            out[f"{base}/geofence"] = geofence_name

        numeric_map: list[tuple[str, int | float | Decimal | None]] = [
            ("battery_level", point.battery_level),
            ("usable_battery_level", point.usable_battery_level),
            ("rated_battery_range_km", point.rated_battery_range_km),
            ("ideal_battery_range_km", point.ideal_battery_range_km),
            ("est_battery_range_km", point.est_battery_range_km),
            ("odometer", point.odometer),
            ("speed", point.speed),
            ("power", point.power),
            ("outside_temp", point.outside_temp),
            ("inside_temp", point.inside_temp),
            ("elevation", point.elevation),
            ("heading", point.heading),
            ("charger_voltage", point.charger_voltage),
            ("charger_actual_current", point.charger_actual_current),
            (
                "charger_power",
                charger_power_kw if charger_power_kw is not None else point.charger_power,
            ),
            (
                "charge_energy_added",
                charge_energy_added
                if charge_energy_added is not None
                else point.charge_energy_added,
            ),
            ("charge_limit_soc", point.charge_limit_soc),
            ("charge_current_request", point.charge_current_request),
            ("time_to_full_charge", point.time_to_full_charge),
            ("tpms_pressure_fl", point.tpms_pressure_fl),
            ("tpms_pressure_fr", point.tpms_pressure_fr),
            ("tpms_pressure_rl", point.tpms_pressure_rl),
            ("tpms_pressure_rr", point.tpms_pressure_rr),
        ]
        for key, num_val in numeric_map:
            if num_val is not None:
                out[f"{base}/{key}"] = _fmt_num(num_val)

        str_map: list[tuple[str, str | None]] = [
            ("shift_state", point.gear),
            ("charging_state", point.charge_state),
            ("climate_keeper_mode", point.climate_keeper_mode),
            ("version", point.version),
        ]
        for key, str_val in str_map:
            if str_val is not None:
                out[f"{base}/{key}"] = str_val

        bool_map: list[tuple[str, bool | None]] = [
            ("is_climate_on", point.is_climate_on),
            ("is_preconditioning", point.is_preconditioning),
            ("locked", point.locked),
            ("doors_open", point.doors_open),
            ("driver_front_door_open", point.driver_front_door_open),
            ("passenger_front_door_open", point.passenger_front_door_open),
            ("driver_rear_door_open", point.driver_rear_door_open),
            ("passenger_rear_door_open", point.passenger_rear_door_open),
            ("windows_open", point.windows_open),
            ("driver_front_window_open", point.driver_front_window_open),
            ("passenger_front_window_open", point.passenger_front_window_open),
            ("driver_rear_window_open", point.driver_rear_window_open),
            ("passenger_rear_window_open", point.passenger_rear_window_open),
            ("trunk_open", point.trunk_open),
            ("frunk_open", point.frunk_open),
            ("sentry_mode", point.sentry_mode),
            ("charge_port_door_open", point.charge_port_door_open),
            ("plugged_in", point.plugged_in),
            ("is_user_present", point.is_user_present),
            ("tpms_soft_warning_fl", point.tpms_soft_warning_fl),
            ("tpms_soft_warning_fr", point.tpms_soft_warning_fr),
            ("tpms_soft_warning_rl", point.tpms_soft_warning_rl),
            ("tpms_soft_warning_rr", point.tpms_soft_warning_rr),
        ]
        for key, bool_val in bool_map:
            if bool_val is not None:
                out[f"{base}/{key}"] = _fmt_bool(bool_val)

        return out

    async def publish_point(
        self,
        point: VehicleTelemetryPoint,
        vehicle_state: str,
        *,
        geofence_name: str | None = None,
        charger_power_kw: int | None = None,
        charge_energy_added: Decimal | None = None,
    ) -> None:
        if not self.enabled or self._client is None:
            return
        messages = self.build_state_messages(
            point,
            vehicle_state,
            geofence_name=geofence_name,
            charger_power_kw=charger_power_kw,
            charge_energy_added=charge_energy_added,
        )
        for topic, payload in messages.items():
            try:
                await self._client.publish(topic, payload, qos=0, retain=True)
            except Exception as err:
                logger.warning("Failed to publish MQTT topic %s: %s", topic, err)

    async def publish_raw(self, subtopic: str, payload: str, *, retain: bool = True) -> None:
        """Publish an arbitrary subtopic under fleetmate/cars/{car_id}/."""
        if not self.enabled or self._client is None:
            return
        topic = f"{self.prefix}/cars/{self.car_id}/{subtopic.lstrip('/')}"
        try:
            await self._client.publish(topic, payload, qos=0, retain=retain)
        except Exception as err:
            logger.warning("Failed to publish MQTT topic %s: %s", topic, err)

    async def publish_state_only(
        self, vehicle_state: str, timestamp: datetime | None = None
    ) -> None:
        """Publish a vehicle state transition (and updated since timestamp) to MQTT."""
        if not self.enabled or self._client is None:
            return
        ts = (timestamp or datetime.now(UTC)).astimezone(UTC)
        if vehicle_state != self._last_state:
            self._last_state = vehicle_state
            self._last_state_since = ts
            await self.publish_raw("since", ts.isoformat().replace("+00:00", "Z"), retain=True)
        await self.publish_raw("state", vehicle_state, retain=True)
