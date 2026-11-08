# Contributing to FleetMate

[English](CONTRIBUTING.md) | [Español](CONTRIBUTING.es.md)

Thank you for your interest in contributing to **FleetMate**! 🚗⚡

FleetMate is a high-speed, zero-cost Tesla Fleet Telemetry mTLS streaming engine and bridge for TeslaMate and Home Assistant. We welcome contributions from developers, homelab enthusiasts, and Tesla owners worldwide.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Style & Quality](#code-style--quality)
- [Pull Request Process](#pull-request-process)
- [Conventional Commits](#conventional-commits)
- [Multilingual Documentation & AI Assistance](#multilingual-documentation--ai-assistance-coderabbit)
- [Security Vulnerabilities](#security-vulnerabilities)

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior privately via [GitHub Security Advisories](https://github.com/rodolfoconcepcion/fleetmate/security/advisories).

---

## How Can I Contribute?

- **Report Bugs**: Submit detailed issue reports using the [Bug Report template](https://github.com/rodolfoconcepcion/fleetmate/issues/new?template=bug_report.yml).
- **Suggest Features**: Propose enhancements via the [Feature Request template](https://github.com/rodolfoconcepcion/fleetmate/issues/new?template=feature_request.yml).
- **Improve Documentation**: Enhance READMEs, guides, architectural diagrams, or docstrings.
- **Submit Code**: Add telemetry fields, improve mTLS performance, expand test coverage, or optimize Home Assistant MQTT discovery.

---

## Development Setup

FleetMate is written in modern asynchronous Python 3.12+ and uses [`uv`](https://docs.astral.sh/uv/) for fast, deterministic dependency management.

### Prerequisites

- **Python**: 3.12 or newer
- **uv**: Fast Python package installer and resolver (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Docker & Docker Compose**: For local telemetry ingestion and broker testing

### Setup Instructions

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/fleetmate.git
   cd fleetmate
   ```

2. **Set Up the Virtual Environment with `uv`**:
   ```bash
   uv sync --all-extras
   ```

3. **Activate Environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Verify Installation**:
   ```bash
   fleetmate --help
   ```

---

## Project Architecture

```
fleetmate/
├── src/fleetmate/
│   ├── cli.py               # Click & Rich CLI interface
│   ├── config.py            # Pydantic Settings & environment variables
│   ├── main.py              # Application lifecycle & async worker loop
│   ├── autodiscovery.py     # TeslaMate & Home Assistant auto-detection
│   ├── consumer.py          # Asynchronous stream consumer
│   ├── models.py            # Pydantic telemetry & state payload schemas
│   ├── repository.py        # AsyncPG PostgreSQL persistence layer
│   └── mtls/                # Tesla mTLS certificate & handshake management
├── tests/                   # Pytest test suite with asyncio & coverage
├── deploy/                  # Docker Compose, systemd, & production manifests
└── docs/                    # Architecture diagrams & guides
```

---

## Testing Guidelines

FleetMate enforces strict test quality and high code coverage.

Run the test suite locally:

```bash
# Run all unit tests
pytest

# Run tests with verbose output and coverage report
pytest --cov=src/fleetmate --cov-report=term-missing tests/
```

Before submitting a PR, make sure all tests pass cleanly.

---

## Code Style & Quality

We maintain high code quality with **Ruff** for linting/formatting and **Mypy** for static type analysis:

```bash
# Format and lint code with Ruff
ruff check src tests
ruff format src tests

# Static type checking
mypy src
```

---

## Pull Request Process

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feat/my-new-feature
   ```

2. **Implement Changes & Tests**:
   - Write clean, documented, asynchronous Python code.
   - Include unit tests in `tests/` covering new logic or bug fixes.
   - Ensure `ruff check`, `mypy`, and `pytest` pass 100%.

3. **Commit with Conventional Commits**:
   Follow semantic commit conventions (see below).

4. **Push and Open a Pull Request**:
   - Push to your fork: `git push origin feat/my-new-feature`
   - Open a PR against the `main` branch.
   - Fill out the provided [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).

---

## Conventional Commits

We follow [Conventional Commits](https://www.conventionalcommits.org/) for automated semantic releases via Release Please:

| Prefix | Description |
| :--- | :--- |
| `feat:` | A new feature or capability (triggers minor version bump) |
| `fix:` | A bug fix or security patch (triggers patch version bump) |
| `docs:` | Documentation changes only |
| `style:` | Code style updates (formatting, white-space, etc.) |
| `refactor:` | Code restructuring without feature or bug changes |
| `perf:` | Performance enhancements |
| `test:` | Adding or improving tests |
| `chore:` | Tooling, dependencies, or CI/CD workflow updates |

> [!IMPORTANT]
> All commit messages, code comments, pull request titles, and documentation must be written in **English**.

---

## Multilingual Documentation & AI Assistance (CodeRabbit)

FleetMate maintains complete **multilingual documentation parity** (every English guide has a corresponding Spanish counterpart, e.g. `README.md` and `README.es.md`).

### If You Don't Speak Spanish:
You do **not** need to speak Spanish to contribute to FleetMate! We provide automated AI assistance to handle translations:
1. **Submit Your PR in English**: Make your changes or additions to English markdown files (`README.md`, `ROADMAP.md`, etc.).
2. **Use CodeRabbit AI**: CodeRabbit is integrated into this repository and automatically reviews every Pull Request. You can prompt CodeRabbit directly in any PR comment thread:
   ```text
   @coderabbitai please generate the Spanish translation for my changes in README.md
   ```
3. **Commit the Translation**: Review CodeRabbit's generated translation and commit it to your branch (or a maintainer will gladly assist before merging).
4. **Automated CI Parity Guardrail**: Our CI suite runs `tests/test_doc_parity.py` on every PR to verify that all core documents, version releases, and language switcher headers remain 100% in sync.

### Alternative Translation Options:
- **Manual Translation**: If you speak Spanish (or other supported languages), you are very welcome to provide the translations directly in `*.es.md`.
- **Maintainer Assistance**: If you prefer not to use AI, simply open your PR with your English changes and request maintainer assistance in your PR description. We will translate it for you before merging.

---

## Security Vulnerabilities

Please do **NOT** open public issues for security vulnerabilities. Review our [Security Policy](SECURITY.md) and report privately via [GitHub Security Advisories](https://github.com/rodolfoconcepcion/fleetmate/security/advisories).
