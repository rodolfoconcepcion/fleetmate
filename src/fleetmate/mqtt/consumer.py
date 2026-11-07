import asyncio
import logging

import aiomqtt
import orjson

from fleetmate.config.settings import settings
from fleetmate.metrics.prometheus import (
    CURRENT_BATTERY_LEVEL,
    CURRENT_VEHICLE_SPEED,
    MESSAGES_RECEIVED,
)
from fleetmate.state.engine import StateMachineEngine
from fleetmate.telemetry.models import VehicleTelemetryPoint

logger = logging.getLogger(__name__)


class FleetMQTTConsumer:
    """
    Subscribes to incoming MQTT messages from tesla/fleet-telemetry.
    Decodes protobuf-JSON payloads, maps VINs, and feeds the StateMachineEngine.
    """

    def __init__(self, engine: StateMachineEngine) -> None:
        self.engine = engine
        self._running = False

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
                    await client.subscribe(settings.mqtt_topic)

                    async for message in client.messages:
                        if not self._running:
                            break
                        try:
                            await self._handle_message(message)
                        except Exception as e:
                            logger.error("Error processing telemetry message: %s", e)
                            MESSAGES_RECEIVED.labels(status="error").inc()
            except aiomqtt.MqttError as err:
                logger.warning("MQTT connection lost: %s. Reconnecting in 5 seconds...", err)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("Unexpected error in MQTT Consumer loop: %s", e)
                await asyncio.sleep(5)

    def stop(self) -> None:
        self._running = False

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        topic = str(message.topic)
        payload_bytes = message.payload
        if not isinstance(payload_bytes, bytes):
            return

        MESSAGES_RECEIVED.labels(status="success").inc()

        try:
            data = orjson.loads(payload_bytes)
        except Exception:
            return

        # Extract VIN from topic (e.g., telemetry/tesla_telemetry/5YJ3E1EBXRF822141/V)
        parts = topic.split("/")
        vin = settings.vin
        for part in parts:
            if len(part) == 17 and part.isalnum():
                vin = part
                break

        # Convert to standardized point
        point = VehicleTelemetryPoint.from_fleet_telemetry_json(vin=vin, raw_data=data)

        # Update metrics
        if point.speed is not None:
            CURRENT_VEHICLE_SPEED.set(point.speed)
        if point.battery_level is not None:
            CURRENT_BATTERY_LEVEL.set(point.battery_level)

        # Feed the state machine
        await self.engine.process_point(point)
