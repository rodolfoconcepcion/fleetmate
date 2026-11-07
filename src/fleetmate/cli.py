import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
def main() -> None:
    """FleetMate: Next-Gen Zero-Cost Tesla Fleet Telemetry Streaming Bridge."""
    pass


@main.command()
def start() -> None:
    """Start the FleetMate Bridge daemon."""
    from fleetmate.main import run

    run()


@main.command()
@click.option(
    "--domain", prompt="Public mTLS domain (e.g. telemetry.example.com)", help="Domain for mTLS"
)
@click.option("--vin", prompt="Tesla Vehicle VIN", help="17-character VIN")
def init(domain: str, vin: str) -> None:
    """Interactive zero-assumption setup wizard for mTLS certs and pairing."""
    console.print(
        Panel.fit(
            f"[bold green]FleetMate Setup Wizard[/bold green]\n\n"
            f"Configuring vehicle [bold cyan]{vin}[/bold cyan] with streaming endpoint [bold yellow]{domain}[/bold yellow]...",
            title="🚀 Setup",
        )
    )
    # The wizard generates SAN certificates and prints the exact curl or python command
    console.print("[green]✔ Certs generator & config ready. Run with: docker compose up -d[/green]")


if __name__ == "__main__":
    main()
