import asyncio
import contextlib
import logging
from typing import Any

import aiomqtt
import orjson

from fleetmate.commands.client import TeslaCommandExecutor
from fleetmate.config.settings import settings
from fleetmate.metrics.prometheus import (
    CURRENT_BATTERY_LEVEL,
    CURRENT_VEHICLE_SPEED,
    MESSAGES_RECEIVED,
)
from fleetmate.mqtt.publisher import StateMQTTPublisher
from fleetmate.state.engine import StateMachineEngine
from fleetmate.telemetry.models import VehicleTelemetryPoint

logger = logging.getLogger(__name__)

MILES_TO_KM = 1.609344
DISTANCE_FIELDS = frozenset(
    {"Odometer", "RatedRange", "IdealBatteryRange", "EstBatteryRange", "VehicleSpeed"}
)
IGNORED_RECORD_TYPES = frozenset({"alerts", "errors"})
IGNORED_FIELDS = frozenset({"Vin", "CreatedAt", "IsResend"})


class FleetMQTTConsumer:
    """
    Subscribes to incoming MQTT messages from tesla/fleet-telemetry.
    Supports both combined record payloads and per-field MQTT topics,
    normalizes units, maps VINs, and feeds the StateMachineEngine.
    """

    def __init__(
        self,
        engine: StateMachineEngine,
        publisher: StateMQTTPublisher | None = None,
        debounce_seconds: float = 0.15,
        command_executor: TeslaCommandExecutor | None = None,
        sleep_debounce_seconds: float = 15.0,
    ) -> None:
        self.engine = engine
        self.publisher = publisher or engine.publisher
        self.debounce_seconds = debounce_seconds
        self.sleep_debounce_seconds = sleep_debounce_seconds
        self.command_executor = command_executor
        self._cmd_prefix = f"{settings.mqtt_publish_prefix}/cars/{settings.car_id}/cmd/"
        self._running = False
        self._latest_fields: dict[str, dict[str, Any]] = {}
        self._flush_tasks: dict[str, asyncio.Task[None]] = {}
        self._sleep_tasks: dict[str, asyncio.Task[None]] = {}
        self._connected_interfaces: dict[str, set[str]] = {}
        self._command_tasks: set[asyncio.Task[None]] = set()

    async def _cancel_flush_tasks(self) -> None:
        tasks = list(self._flush_tasks.values()) + list(self._sleep_tasks.values())
        self._flush_tasks.clear()
        self._sleep_tasks.clear()
        for task in tasks:
            if not task.done():
                task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def _cancel_sleep_task(self, vin: str) -> None:
        task = self._sleep_tasks.pop(vin, None)
        if task is not None and not task.done():
            task.cancel()

    async def _delayed_sleep(self, vin: str) -> None:
        try:
            await asyncio.sleep(self.sleep_debounce_seconds)
            self._sleep_tasks.pop(vin, None)
            if not self._connected_interfaces.get(vin):
                await self.engine.mark_asleep()
        except asyncio.CancelledError:
            return
        except Exception as err:
            logger.error("Error transitioning %s to asleep: %s", vin, err)

    async def _schedule_sleep(self, vin: str) -> None:
        self._cancel_sleep_task(vin)
        if self.sleep_debounce_seconds <= 0:
            if not self._connected_interfaces.get(vin):
                await self.engine.mark_asleep()
            return
        self._sleep_tasks[vin] = asyncio.create_task(self._delayed_sleep(vin))

    async def _handle_connectivity(self, vin: str, payload: dict[str, Any]) -> None:
        iface = str(payload.get("NetworkInterface") or "default").lower()
        status = str(payload.get("Status") or "").upper()
        ifaces = self._connected_interfaces.setdefault(vin, set())
        if status == "CONNECTED":
            ifaces.add(iface)
            self._cancel_sleep_task(vin)
            await self.engine.mark_online()
        elif status == "DISCONNECTED":
            ifaces.discard(iface)
            if not ifaces:
                await self._schedule_sleep(vin)

    async def start(self) -> None:
        self._running = True
        logger.info(
            "Connecting to MQTT Broker at %s:%s (Topic: %s)...",
            settings.mqtt_broker,
            settings.mqtt_port,
            settings.mqtt_topic,
        )

        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=settings.mqtt_broker,
                    port=settings.mqtt_port,
                    username=settings.mqtt_username,
                    password=settings.mqtt_password,
                    identifier=settings.mqtt_client_id,
                ) as client:
                    logger.info(
                        "Connected to MQTT Broker. Subscribing to %s...", settings.mqtt_topic
                    )
                    if self.publisher is not None:
                        self.publisher.set_client(client)
                        await self.publisher.publish_discovery(client)
                    await client.subscribe(settings.mqtt_topic)
                    if self.command_executor is not None:
                        await client.subscribe(f"{self._cmd_prefix}#")
                        logger.info("Subscribed to HA MQTT commands on %s#", self._cmd_prefix)

                    async for message in client.messages:
                        if not self._running:
                            break
                        try:
                            await self._handle_message(message)
                        except Exception as e:
                            logger.error("Error processing telemetry message: %s", e)
                            MESSAGES_RECEIVED.labels(status="error").inc()
            except aiomqtt.MqttError as err:
                if self.publisher is not None:
                    self.publisher.set_client(None)
                logger.warning("MQTT connection lost: %s. Reconnecting in 5 seconds...", err)
                await asyncio.sleep(5)
            except Exception as e:
                if self.publisher is not None:
                    self.publisher.set_client(None)
                logger.error("Unexpected error in MQTT Consumer loop: %s", e)
                await asyncio.sleep(5)
            finally:
                await self._cancel_flush_tasks()
                if self.publisher is not None:
                    self.publisher.set_client(None)

    def stop(self) -> None:
        self._running = False

    @staticmethod
    def _parse_payload(payload_bytes: bytes) -> Any:
        try:
            return orjson.loads(payload_bytes)
        except Exception:
            text = payload_bytes.decode("utf-8", errors="ignore").strip()
            return text if text else None

    @staticmethod
    def _extract_vin(parts: list[str]) -> str:
        for part in parts:
            if len(part) == 17 and part.isalnum():
                return part
        return settings.vin

    async def _process_raw_payload(self, vin: str, raw_data: dict[str, Any]) -> None:
        point = VehicleTelemetryPoint.from_fleet_telemetry_json(vin=vin, raw_data=raw_data)
        if point.speed is not None:
            CURRENT_VEHICLE_SPEED.set(point.speed)
        if point.battery_level is not None:
            CURRENT_BATTERY_LEVEL.set(point.battery_level)
        await self.engine.process_point(point)

    async def _flush_vin(self, vin: str) -> None:
        self._flush_tasks.pop(vin, None)
        buf = self._latest_fields.get(vin)
        if not buf:
            return
        payload = dict(buf)
        buf.pop("Location", None)
        await self._process_raw_payload(vin, payload)

    async def _delayed_flush(self, vin: str) -> None:
        try:
            await asyncio.sleep(self.debounce_seconds)
            await self._flush_vin(vin)
        except asyncio.CancelledError:
            return
        except Exception as err:
            logger.error("Error flushing telemetry for %s: %s", vin, err)
            MESSAGES_RECEIVED.labels(status="error").inc()

    async def _schedule_flush(self, vin: str) -> None:
        existing = self._flush_tasks.pop(vin, None)
        if existing is not None and not existing.done():
            existing.cancel()
        if self.debounce_seconds <= 0:
            await self._flush_vin(vin)
            return
        self._flush_tasks[vin] = asyncio.create_task(self._delayed_flush(vin))

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        topic = str(message.topic)
        payload_bytes = message.payload
        if not isinstance(payload_bytes, bytes):
            return

        if topic.startswith(self._cmd_prefix):
            subtopic = topic[len(self._cmd_prefix) :].strip("/")
            raw_text = payload_bytes.decode("utf-8", errors="replace").strip()
            task = asyncio.create_task(self._dispatch_command(subtopic, raw_text))
            self._command_tasks.add(task)
            task.add_done_callback(self._command_tasks.discard)
            return

        MESSAGES_RECEIVED.labels(status="success").inc()

        parsed = self._parse_payload(payload_bytes)
        parts = [p for p in topic.split("/") if p]
        vin = self._extract_vin(parts)

        # Handle per-field MQTT topics emitted by tesla/fleet-telemetry: .../v/<FieldName>
        if len(parts) >= 3 and parts[-2].lower() == "v":
            field_name = parts[-1]
            if field_name in IGNORED_FIELDS or parsed is None:
                return
            if isinstance(parsed, str) and parsed == "<invalid>":
                return
            if (
                field_name in DISTANCE_FIELDS
                and isinstance(parsed, (int, float))
                and not isinstance(parsed, bool)
            ):
                parsed = float(parsed) * MILES_TO_KM
            self._cancel_sleep_task(vin)
            self._latest_fields.setdefault(vin, {})[field_name] = parsed
            await self._schedule_flush(vin)
            return

        if parts and parts[-1].lower() == "connectivity" and isinstance(parsed, dict):
            await self._handle_connectivity(vin, parsed)
            return

        if parts and parts[-1].lower() in IGNORED_RECORD_TYPES:
            return

        if isinstance(parsed, dict):
            await self._process_raw_payload(vin, parsed)

    async def _dispatch_command(self, subtopic: str, raw_payload: str) -> None:
        """Translate an incoming HA MQTT control payload into a Tesla Fleet API command."""
        if self.command_executor is None:
            logger.warning("Received MQTT command %s but command_executor is disabled", subtopic)
            return

        upper = raw_payload.upper()
        toggle_map: dict[str, tuple[str, str, str | None]] = {
            "door_lock": ("lock", "unlock", "locked"),
            "sentry": ("sentry_on", "sentry_off", "sentry_mode"),
            "charging": ("charge_start", "charge_stop", None),
            "climate": ("climate_on", "climate_off", "is_climate_on"),
            "charge_port": ("charge_port_open", "charge_port_close", "charge_port_door_open"),
            "wheel_heater": ("wheel_heater_on", "wheel_heater_off", "wheel_heater_state"),
        }
        button_map: dict[str, str] = {
            "windows_vent": "windows_vent",
            "windows_close": "windows_close",
            "open_frunk": "open_frunk",
            "open_trunk": "open_trunk",
            "flash_lights": "flash_lights",
            "honk_horn": "honk_horn",
            "wake": "wake",
            "schedule_software_update": "schedule_software_update",
        }
        numeric_map: dict[str, tuple[str, str | None]] = {
            "charge_limit": ("charge_limit", "charge_limit_soc"),
            "charge_amps": ("charge_amps", "charge_current_request"),
            "cabin_temp_f": ("climate_temp_f", "cabin_temp_target_f"),
            "seat_heater_driver": ("seat_heater_driver", "seat_heater_driver"),
            "seat_heater_passenger": ("seat_heater_passenger", "seat_heater_passenger"),
        }

        action: str | None = None
        value: Any = None
        state_update: tuple[str, str] | None = None

        if subtopic in toggle_map:
            on_act, off_act, state_key = toggle_map[subtopic]
            is_on = upper in {"ON", "LOCK", "TRUE", "1"}
            action = on_act if is_on else off_act
            if state_key:
                state_update = (state_key, "true" if is_on else "false")
        elif subtopic in button_map:
            action = button_map[subtopic]
        elif subtopic in numeric_map:
            action, state_key = numeric_map[subtopic]
            try:
                num = float(raw_payload)
            except ValueError:
                logger.warning("Invalid numeric MQTT payload for %s: %r", subtopic, raw_payload)
                return
            value = num if subtopic == "cabin_temp_f" else int(round(num))
            if state_key:
                state_update = (state_key, str(int(value) if float(value).is_integer() else value))
        else:
            logger.warning("Unknown MQTT command subtopic: %s", subtopic)
            return

        res = await self.command_executor.execute(
            action, value=value, coords=self.engine.last_coords
        )
        if res.ok:
            logger.info("HA MQTT command %s -> %s succeeded: %s", subtopic, action, res.message)
            if state_update and self.publisher is not None:
                await self.publisher.publish_raw(state_update[0], state_update[1], retain=True)
            if subtopic == "charging" and self.publisher is not None:
                await self.publisher.publish_raw(
                    "charging_state", "Charging" if upper in {"ON", "TRUE", "1"} else "Stopped"
                )
        else:
            logger.warning(
                "HA MQTT command %s -> %s failed (status=%s): %s",
                subtopic,
                action,
                res.http_status,
                res.message,
            )
