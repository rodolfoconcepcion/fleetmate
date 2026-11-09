# Registro de Cambios

[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)

---

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:02b71d34e08d5cdf831abc314ae413fa78e304e30ca8cfa08907e7fba050bf25 -->

## [0.5.0](https://github.com/rodolfoconcepcion/fleetmate/compare/fleetmate-v0.4.0...fleetmate-v0.5.0) (2026-11-09)

### Características (Features)

* **charging:** implementación de una máquina de estados para sesiones de carga en tiempo real y seguimiento de kWh (cierra [#15](https://github.com/rodolfoconcepcion/fleetmate/issues/15)) ([8965e67](https://github.com/rodolfoconcepcion/fleetmate/commit/8965e672dff94e0b7515b4e437efb114d5b45490))
* **geofences:** incorporación de detección nativa de límites de geocercas y una calculadora de costos de electricidad (cierra [#16](https://github.com/rodolfoconcepcion/fleetmate/issues/16)) ([f5785ce](https://github.com/rodolfoconcepcion/fleetmate/commit/f5785cedd42439502bc80cfb270c88cc47fdad2a))

### Correcciones de Errores (Bug Fixes)

* **community:** priorización de los archivos canónicos de la comunidad en inglés en el directorio .github ([#21](https://github.com/rodolfoconcepcion/fleetmate/issues/21)) ([7496f50](https://github.com/rodolfoconcepcion/fleetmate/commit/7496f50d1206033e7eac639482b88234b7f8d760))

<!-- /coderabbit-ai-generated:v1 -->

## [0.4.0](https://github.com/rodolfoconcepcion/fleetmate/compare/fleetmate-v0.3.0...fleetmate-v0.4.0) (2026-11-08)

### Características (Features)

* **geocoding:** implementación del trabajador de geocodificación inversa con Nominatim para direcciones de trayectos ([#14](https://github.com/rodolfoconcepcion/fleetmate/issues/14)) ([b222a25](https://github.com/rodolfoconcepcion/fleetmate/commit/b222a255271e5dd44a4ae89c0397a28f22ab08bd))

## [0.3.0](https://github.com/rodolfoconcepcion/fleetmate/compare/fleetmate-v0.2.0...fleetmate-v0.3.0) (2026-11-08)

### Características (Features)

* **scope:** declaración de la descontinuación de TeslaMate y la independencia nativa como parte del alcance ([#18](https://github.com/rodolfoconcepcion/fleetmate/issues/18)) ([ebcef19](https://github.com/rodolfoconcepcion/fleetmate/commit/ebcef19b567e82c3570f29b094b9baf1509b141f))

### Documentación (Documentation)

* **changelog:** incorporación del registro de cambios en español y enlaces de navegación bilingües ([c7102ca](https://github.com/rodolfoconcepcion/fleetmate/commit/c7102cab4839eedc5351ee342766ea66ba22236e))
* **i18n:** finalización de las traducciones al español de gobernanza, colaboradores y hoja de ruta ([#12](https://github.com/rodolfoconcepcion/fleetmate/issues/12)) ([eaafe2c](https://github.com/rodolfoconcepcion/fleetmate/commit/eaafe2c3f90883cabc712dcc152da0caffc203c7))
* **roadmap:** incorporación de un motor automatizado de documentación multilingüe en la Fase 3 y enlaces para cambiar de idioma ([e38eba4](https://github.com/rodolfoconcepcion/fleetmate/commit/e38eba47bc0bb942012d13f84cb13c5076ad4c4e))
* **roadmap:** corrección de enlaces rotos a las mejores prácticas de Open Source Guide ([d8f7afe](https://github.com/rodolfoconcepcion/fleetmate/commit/d8f7afe782e9050cfe1856150104deee0eadc880))

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
