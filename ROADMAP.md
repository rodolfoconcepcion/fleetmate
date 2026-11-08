# FleetMate Product Roadmap

This document outlines the high-level roadmap and future vision for **FleetMate**, following the [Open Source Guide on Best Practices for Maintainers](https://opensource.guide/best-practices-for-maintainers/).

---

## 🎯 Project Vision

FleetMate aims to be the gold-standard, zero-cost, real-time streaming bridge between Tesla Fleet Telemetry and homelab automation systems (TeslaMate, Home Assistant, Grafana, and MQTT).

---

## 📅 Roadmap & Milestones

### ✅ Phase 1: Ingestion & Storage Baseline (v0.1.0) — *Completed*
- [x] Asynchronous Python 3.12+ streaming worker core.
- [x] Tesla Fleet Telemetry mTLS termination & handshake engine.
- [x] Direct PostgreSQL state repository matching TeslaMate schema.
- [x] Home Assistant MQTT discovery with dynamic vehicle sensor entities.
- [x] Bilingual documentation (English & Spanish).

### 🚀 Phase 2: Autodiscovery & Hardening (v0.2.0) — *Current*
- [x] Automated discovery of existing TeslaMate, PostgreSQL, and MQTT brokers.
- [x] Expanded TPMS tire sensor telemetry coverage (FL, FR, RL, RR pressure & temperature).
- [x] CodeQL hardening and security pipeline integrations.
- [x] 100% GitHub Community Standards & Open Source Guide compliance.

### 🔮 Phase 3: Edge Resilience & HA Packaging (v0.3.0) — *Planned*
- [ ] **Home Assistant Add-on**: Native 1-click Home Assistant Add-on distribution.
- [ ] **Local Edge Buffering**: SQLite local spool during transient PostgreSQL network outages.
- [ ] **Telemetry Replay Utility**: Replay recorded JSONL telemetry traces for offline debugging and testing.

### 🌟 Phase 4: Fleet Intelligence (v1.0.0) — *Future*
- [ ] **Multi-Vehicle Fleet Routing**: Support concurrent multi-vehicle streaming across independent accounts.
- [ ] **Battery Degradation Analytics**: Long-term capacity retention modeling.
- [ ] **Grafana Dashboard Templates**: Pre-built dashboards for real-time telemetry inspection.

---

## 💬 Influencing the Roadmap

Have ideas or requests? Please discuss them in [GitHub Discussions](https://github.com/rodolfoconcepcion/fleetmate/discussions) or submit a feature request!
