# FleetMate Product Roadmap

[English](ROADMAP.md) | [Español](ROADMAP.es.md)

This document outlines the high-level roadmap and future vision for **FleetMate**, following the [Open Source Guide on Best Practices for Maintainers](https://opensource.guide/best-practices/).

---

## 🎯 Project Vision & Scope Boundaries

FleetMate aims to be the gold-standard, zero-cost, real-time streaming bridge between Tesla Fleet Telemetry and homelab automation systems (TeslaMate, Home Assistant, Grafana, and MQTT).

### ✅ What is In-Scope
* **Real-Time Telemetry Streaming**: High-speed, 1 Hz telemetry ingestion from Tesla's official `fleet-telemetry` mTLS server.
* **Turnkey & Hybrid Homelab Storage**: Full compatibility with TeslaMate PostgreSQL schemas and Home Assistant MQTT auto-discovery.
* **Edge Resilience**: Zero-loss local buffering, telemetry trace replaying, and transient network outage tolerance.
* **Self-Hosted Privacy**: 100% self-hosted, independent, zero external subscription or cloud dependency.

### ❌ Non-Goals & Out-of-Scope (Learning to Say No)
To protect maintainer focus and prevent scope creep (as recommended by [Open Source Guides: Best Practices for Maintainers](https://opensource.guide/best-practices/)), the following are explicitly out of scope:
1. **Vehicle Control & Remote Commands**: FleetMate is strictly an ingress telemetry pipeline. It does NOT send commands to vehicles (e.g. door unlocking, climate control, honking, or remote start).
2. **Cloud SaaS / Hosted Service**: FleetMate will never be a commercial hosted multi-tenant cloud service. It is designed solely for self-hosted homelab privacy.
3. **Custom Dashboard Replacement**: FleetMate does not build a standalone custom web frontend to replace TeslaMate or Home Assistant dashboards; it feeds the existing, proven ecosystems.
4. **Proprietary Protocol Reverse-Engineering**: FleetMate relies strictly on Tesla's documented official Fleet Telemetry protocols and standard mTLS WebSockets.

---

## 📅 Roadmap & Milestones

### ✅ Phase 1: Ingestion & Storage Baseline (v0.1.0) — *Completed*
- [x] Asynchronous Python 3.12+ streaming worker core.
- [x] Tesla Fleet Telemetry mTLS termination & handshake engine.
- [x] Direct PostgreSQL state repository matching TeslaMate schema.
- [x] Home Assistant MQTT discovery with dynamic vehicle sensor entities.
- [x] Initial bilingual documentation (English & Spanish).

### 🚀 Phase 2: Autodiscovery & Hardening (v0.2.0) — *Current*
- [x] Automated discovery of existing TeslaMate, PostgreSQL, and MQTT brokers.
- [x] Expanded TPMS tire sensor telemetry coverage (FL, FR, RL, RR pressure & temperature).
- [x] CodeQL hardening and security pipeline integrations.
- [x] 100% GitHub Community Standards & Open Source Guide compliance.

### 🔮 Phase 3: Edge Resilience, Packaging & Automation (v0.3.0) — *Planned*
- [ ] **Home Assistant Add-on**: Native 1-click Home Assistant Add-on distribution.
- [ ] **Local Edge Buffering**: SQLite local spool during transient PostgreSQL network outages.
- [ ] **Telemetry Replay Utility**: Replay recorded JSONL telemetry traces for offline debugging and testing.
- [ ] **Automated Multilingual Documentation Engine (i18n)**: Generic GitHub Actions translation pipeline for multi-language documentation parity (`*.es.md`, `*.de.md`, `*.fr.md`, etc.), ensuring community contributions in any language are automatically synchronized across all supported translations without manual overhead.

### 🌟 Phase 4: Fleet Intelligence (v1.0.0) — *Future*
- [ ] **Multi-Vehicle Fleet Routing**: Support concurrent multi-vehicle streaming across independent accounts.
- [ ] **Battery Degradation Analytics**: Long-term capacity retention modeling.
- [ ] **Grafana Dashboard Templates**: Pre-built dashboards for real-time telemetry inspection.

---

## 💬 Influencing the Roadmap

Have ideas or requests? Please discuss them in [GitHub Discussions](https://github.com/rodolfoconcepcion/fleetmate/discussions) or submit a feature request!
