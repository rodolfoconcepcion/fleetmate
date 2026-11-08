# Hoja de Ruta de Producto de FleetMate

[English](ROADMAP.md) | [Español](ROADMAP.es.md)

Este documento describe la hoja de ruta y la visión a futuro de **FleetMate**, siguiendo la [Guía de Buenas Prácticas para Mantenedores de Open Source](https://opensource.guide/best-practices-for-maintainers/).

---

## 🎯 Visión del Proyecto

FleetMate aspira a ser el puente de transmisión en tiempo real de coste cero y máxima velocidad entre Tesla Fleet Telemetry y sistemas homelab (TeslaMate, Home Assistant, Grafana y MQTT).

---

## 📅 Hoja de Ruta e Hitos

### ✅ Fase 1: Base de Ingestión y Almacenamiento (v0.1.0) — *Completada*
- [x] Núcleo de trabajador asíncrono en Python 3.12+.
- [x] Terminación y motor de apretón de manos (*handshake*) mTLS de Tesla Fleet Telemetry.
- [x] Repositorio de base de datos PostgreSQL compatible con el esquema de TeslaMate.
- [x] Autodescubrimiento MQTT para Home Assistant con entidades dinámicas de sensores.
- [x] Documentación bilingüe inicial (inglés y español).

### 🚀 Fase 2: Autodescubrimiento y Blindaje (v0.2.0) — *Actual*
- [x] Detección automática de instancias existentes de TeslaMate, PostgreSQL y brokers MQTT.
- [x] Cobertura ampliada de telemetría de sensores de neumáticos TPMS (presión y temperatura FL, FR, RL, RR).
- [x] Blindaje de seguridad y análisis estático con CodeQL en CI.
- [x] Cumplimiento del 100% de los estándares de comunidad de GitHub y Open Source Guides.

### 🔮 Fase 3: Resiliencia en el Extremo, Paquetes y Automatización (v0.3.0) — *Planificada*
- [ ] **Add-on para Home Assistant**: Distribución nativa en 1 clic como Add-on de Home Assistant.
- [ ] **Búfer Local de Respaldo**: Cola local en SQLite durante caídas transitorias de red con PostgreSQL.
- [ ] **Utilidad de Reproducción de Telemetría**: Reproductor de trazas JSONL grabadas para pruebas y depuración offline.
- [ ] **Motor de Documentación Multilingüe Automatizado (i18n)**: Canalización genérica de traducción en GitHub Actions para paridad documental multilingüe (`*.es.md`, `*.de.md`, `*.fr.md`, etc.), asegurando que las contribuciones de la comunidad en cualquier idioma se sincronicen automáticamente en todas las traducciones sin sobrecarga manual.

### 🌟 Fase 4: Inteligencia de Flota (v1.0.0) — *Futura*
- [ ] **Enrutamiento Multiflotas**: Soporte para transmisión concurrente de múltiples vehículos de distintas cuentas.
- [ ] **Analítica de Degradación de Batería**: Modelado de retención de capacidad a largo plazo.
- [ ] **Plantillas de Dashboards para Grafana**: Paneles prediseñados para inspección de telemetría en tiempo real.

---

## 💬 Participa en la Hoja de Ruta

¿Tienes sugerencias o ideas? ¡Participa en [GitHub Discussions](https://github.com/rodolfoconcepcion/fleetmate/discussions) o abre una propuesta de nueva característica!
