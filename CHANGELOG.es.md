# Registro de Cambios

[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)

---

## [0.2.0](https://github.com/rodolfoconcepcion/fleetmate/compare/fleetmate-v0.1.0...fleetmate-v0.2.0) (2026-11-08)

### Características (Features)

* **autodiscovery:** detección automática de instancias existentes de TeslaMate, PostgreSQL y brokers MQTT ([5511b44](https://github.com/rodolfoconcepcion/fleetmate/commit/5511b44fe9bbbe61b86d557ad97cc892792c6add))
* **release:** lanzamiento del motor de streaming mTLS de costo cero FleetMate v0.1.0 ([b33f658](https://github.com/rodolfoconcepcion/fleetmate/commit/b33f6585a15651f635775a1a2ee632a38a196aec))

### Correcciones de Errores (Bug Fixes)

* **core:** uso de `asyncio.gather` para esperar la tarea del consumidor cancelada y resolver la alerta de CodeQL `py/ineffectual-statement` ([b59dd6b](https://github.com/rodolfoconcepcion/fleetmate/commit/b59dd6b6041cd7205ef7ce60a507645bf49913da))

### Documentación (Documentation)

* **community:** establecimiento de estándares de la comunidad (código de conducta, contribución, accesibilidad) ([#9](https://github.com/rodolfoconcepcion/fleetmate/issues/9)) ([fddf068](https://github.com/rodolfoconcepcion/fleetmate/commit/fddf06831aa67c6d4ead61352918ebe22043c09d))
* **community:** implementación integral de estándares según opensource.guide ([#10](https://github.com/rodolfoconcepcion/fleetmate/issues/10)) ([6ad3cc0](https://github.com/rodolfoconcepcion/fleetmate/commit/6ad3cc0d14ce6c4b8e41ae6291d6ae84b9e1cc22))
* **es:** corrección de enlaces cruzados en la documentación en español hacia archivos en español ([4c9b834](https://github.com/rodolfoconcepcion/fleetmate/commit/4c9b834ed1d87f022b3b36cee13ec7224d51ef08))
