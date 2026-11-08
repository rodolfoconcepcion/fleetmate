# Security Policy

[English](SECURITY.md) | [Español](SECURITY.es.md)

## Supported Versions

FleetMate follows semantic versioning and actively maintains security patches for the latest minor releases.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of FleetMate, Tesla vehicles, and personal homelab infrastructure very seriously.

If you discover a security vulnerability, **please do not open a public issue.** Instead, please report it via one of the following methods:

1. **GitHub Private Vulnerability Reporting (Recommended):**
   Navigate to the [Security Advisories](https://github.com/rodolfoconcepcion/fleetmate/security/advisories) tab and click **"Report a vulnerability"**.

2. **Direct Security Contact:**
   Email: `rodolfo.concepcion@gmail.com` with the subject `[SECURITY] FleetMate Vulnerability Report`.

### What to include in your report:
* A description of the issue and potential impact.
* Step-by-step instructions or a Proof of Concept (PoC) to reproduce the vulnerability safely.
* Any affected components (mTLS ingestion, state machine, database repository, or CLI).

### Our Commitment:
* We will acknowledge receipt of your vulnerability report within 24 hours.
* We will provide an estimated timeline for the fix and keep you informed of our progress.
* Once patched, we will publicly credit you in our release notes (unless you request anonymity).
