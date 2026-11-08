# Hoja de Ruta de Producto de FleetMate

[English](ROADMAP.md) | [Español](ROADMAP.es.md)

Este documento describe la hoja de ruta y la visión a futuro de **FleetMate**, siguiendo la [Guía de Buenas Prácticas para Mantenedores de Open Source](https://opensource.guide/es/best-practices/).

---

## 🎯 Visión del Proyecto y Límites de Alcance

FleetMate aspira a ser el motor de transmisión de telemetría y plataforma de registro en tiempo real de máxima velocidad y coste cero para vehículos Tesla, integrándose a la perfección con Home Assistant, Grafana y entornos homelab. Aunque FleetMate actualmente admite la escritura directa en bases de datos PostgreSQL de TeslaMate para retrocompatibilidad, **alcanzar la independencia total y descontinuar por completo la dependencia de TeslaMate es un objetivo estratégico prioritario**.

### ✅ Dentro del Alcance
* **Transmisión de Telemetría en Tiempo Real**: Ingestión a alta velocidad (1 Hz) desde el servidor mTLS `fleet-telemetry` oficial de Tesla.
* **Independencia Total y Descontinuación de TeslaMate**: Transición progresiva desde los esquemas heredados de TeslaMate hacia un modelo de datos propio de FleetMate, motor de almacenamiento nativo y paneles de control de primer nivel.
* **Compatibilidad y Migración en 1 Clic**: Herramientas de migración automatizadas para importar históricos de viajes, cargas y estadísticas de eficiencia desde TeslaMate hacia el almacenamiento nativo de FleetMate.
* **Almacenamiento Homelab Llave en Mano e Híbrido**: Motores de almacenamiento nativos en PostgreSQL/SQLite con autodescubrimiento MQTT para Home Assistant.
* **Resiliencia en el Extremo**: Búfer local sin pérdida de datos, reproducción de trazas de telemetría y tolerancia a caídas de red transitorias.
* **Privacidad Autoalojada**: 100% independiente y autoalojado, sin suscripciones externas ni dependencias de nube ajena.

### ❌ Fuera del Alcance y No-Objetivos (Aprender a Decir No)
Para proteger el tiempo del mantenedor y evitar la dispersión de objetivos (según la [Guía de Buenas Prácticas para Mantenedores de Open Source](https://opensource.guide/es/best-practices/)), los siguientes aspectos quedan explícitamente fuera del alcance:
1. **Control Remoto del Vehículo**: FleetMate es estrictamente un canal de entrada de telemetría. NO envía comandos a los vehículos (apertura de puertas, climatización, bocina o encendido remoto).
2. **Servicio SaaS en la Nube**: FleetMate nunca será un servicio comercial multiinquilino alojado en la nube. Está concebido exclusivamente para la privacidad homelab autoalojada.
3. **Ingeniería Inversa de Protocolos Propietarios**: FleetMate opera exclusivamente sobre los protocolos oficiales documentados de Tesla Fleet Telemetry y WebSockets mTLS estándares.

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
- [ ] **Descontinuación de TeslaMate (Fase A - Almacenamiento Independiente)**: Modelo de datos relacional nativo de FleetMate independiente de las tablas de TeslaMate, junto a una utilidad de migración en 1 clic para bases de datos existentes de TeslaMate.

### 🌟 Fase 4: Independencia Completa e Inteligencia de Flota (v1.0.0) — *Futura*
- [ ] **Descontinuación de TeslaMate (Fase B - Independencia Total)**: Paneles nativos dedicados para Grafana y Home Assistant, eliminando definitivamente la necesidad de contenedores de TeslaMate.
- [ ] **Enrutamiento Multiflotas**: Soporte para transmisión concurrente de múltiples vehículos de distintas cuentas.
- [ ] **Analítica de Degradación de Batería**: Modelado de retención de capacidad a largo plazo.
- [ ] **Suite Nativa de Paneles en Grafana**: Paneles prediseñados optimizados directamente para telemetría de transmisión en vivo a 1 Hz.

---

## 💬 Participa en la Hoja de Ruta

¿Tienes sugerencias o ideas? ¡Participa en [GitHub Discussions](https://github.com/rodolfoconcepcion/fleetmate/discussions) o abre una propuesta de nueva característica!
