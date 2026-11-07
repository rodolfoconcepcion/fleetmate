# AI Agent Integration: Antigravity & Claude Code

FleetMate is built natively for the Agentic Coding era. If you are using **Google Antigravity (AGY)**, **Claude Code**, **Cursor**, or **Windsurf**, you do not need to manually configure Docker, write certificates, or copy curl commands.

An AI agent can deploy and configure the entire stack end-to-end autonomously.

---

## 🤖 1-Prompt Autonomous Setup

Simply clone the repository and prompt your AI assistant:

> *"Set up FleetMate for my Tesla (VIN: `5YJ...`, Token: `...`, Domain: `telemetry.example.com`). Run the skill and verify the stack."*

---

## 📦 Bundled AI Skills & Directives

FleetMate includes built-in AI skills that instruct AI agents on how to safely and reliably execute every step without human intervention:

* **`.agents/skills/fleetmate-deployer/SKILL.md`:** 
  The autonomous deployment playbook for Google Antigravity and Agentic CLI systems.
* **`CLAUDE.md` / `AGENTS.md` integration:** 
  Includes automated self-healing, zero-permission certificate provisioning, and safe PostgreSQL schema validation.

---

## 🛠️ What the AI Agent Does Automatically:

1. **Environment Detection:** Detects whether you are running on a **Local Homelab** (behind Cloudflare tunnel or router) or on a **Cloud VPS** (public IP).
2. **mTLS Certificate Generation:** Programmatically creates the Root CA, Server Private Key, and Subject Alternative Names (SANs) for your vehicle.
3. **Vehicle Pairing:** Sends the administrative configuration call directly to Tesla's Fleet API (`fleet_telemetry_config`).
4. **Stack Launch & SRE Verification:** Runs `docker compose up -d`, queries the Prometheus metrics endpoint (`:9090/metrics`), and verifies that database connections and MQTT topics are healthy.
