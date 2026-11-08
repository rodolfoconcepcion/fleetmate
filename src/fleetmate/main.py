import asyncio
import contextlib
import logging
import signal
import sys

from prometheus_client import start_http_server

from fleetmate.config.settings import settings
from fleetmate.mqtt.consumer import FleetMQTTConsumer
from fleetmate.state.engine import StateMachineEngine
from fleetmate.storage.postgres import TeslaMateRepository

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
    repo = TeslaMateRepository()
    await repo.connect()

    # 3. Initialize State Machine Engine
    engine = StateMachineEngine(repo=repo, car_id=settings.car_id)

    # 4. Initialize MQTT Consumer
    consumer = FleetMQTTConsumer(engine=engine)

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

    # 6. Run consumer loop
    consumer_task = asyncio.create_task(consumer.start())

    await stop_event.wait()

    # Cleanup
    logger.info("Cleaning up resources...")
    consumer_task.cancel()
    await asyncio.gather(consumer_task, return_exceptions=True)
    await repo.close()
    logger.info("FleetMate Bridge shutdown complete.")


def run() -> None:
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


if __name__ == "__main__":
    run()
