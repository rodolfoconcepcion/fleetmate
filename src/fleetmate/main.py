import asyncio
import contextlib
import logging
import signal
import sys

from prometheus_client import start_http_server

from fleetmate.commands.client import TeslaCommandExecutor
from fleetmate.config.settings import settings
from fleetmate.mqtt.consumer import FleetMQTTConsumer
from fleetmate.mqtt.publisher import StateMQTTPublisher
from fleetmate.state.engine import StateMachineEngine
from fleetmate.storage.postgres import FleetMateRepository

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fleetmate")


async def main_async() -> None:
    logger.info("Starting FleetMate Bridge Engine v0.1.0...")

    # 1. Start Prometheus SRE metrics exporter
    logger.info("Exposing Prometheus metrics on port %d...", settings.metrics_port)
    start_http_server(settings.metrics_port)

    # 2. Initialize PostgreSQL repository
    repo = FleetMateRepository()
    await repo.connect()

    # 3. Initialize State Machine Engine & MQTT Publisher
    from fleetmate.web.server import FleetMateWebServer

    command_executor = (
        TeslaCommandExecutor(
            vin=settings.vin,
            proxy_url=settings.fleet_proxy_url,
            token_file=settings.fleet_token_file,
            auth_url=settings.fleet_auth_url,
            client_id=settings.fleet_client_id,
            client_secret=settings.fleet_client_secret,
        )
        if settings.vin and settings.fleet_proxy_url
        else None
    )

    publisher = StateMQTTPublisher(car_id=settings.car_id)
    engine = StateMachineEngine(repo=repo, car_id=settings.car_id, publisher=publisher)

    # 4. Initialize MQTT Consumer & Web Portal
    consumer = FleetMQTTConsumer(
        engine=engine, publisher=publisher, command_executor=command_executor
    )
    web_server = (
        FleetMateWebServer(
            repo=repo, engine=engine, command_executor=command_executor, config=settings
        )
        if settings.web_enabled
        else None
    )

    # 5. Graceful shutdown handler
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Termination signal received. Initiating graceful shutdown...")
        consumer.stop()
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal_handler)

    # 6. Start Web Portal & MQTT consumer loop
    consumer_task = asyncio.create_task(consumer.start())
    try:
        if web_server is not None:
            await web_server.start()

        await stop_event.wait()
    finally:
        logger.info("Cleaning up resources...")
        consumer_task.cancel()
        await asyncio.gather(consumer_task, return_exceptions=True)
        if web_server is not None:
            try:
                await web_server.stop()
            except Exception as err:
                logger.warning("Web portal shutdown error: %s", err)
        await repo.close()
        logger.info("FleetMate Bridge shutdown complete.")


def run() -> None:
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


if __name__ == "__main__":
    run()
