# Gobernanza y Liderazgo del Proyecto

FleetMate tiene el compromiso de construir un proyecto de código abierto transparente, orientado a la comunidad y sostenible, siguiendo las directrices de la [Guía de Liderazgo y Gobernanza de Open Source](https://opensource.guide/leadership-and-governance/).

---

## 🏛️ Estructura de Gobernanza

Actualmente, FleetMate opera bajo el modelo de gobernanza de **Líder Principal de Mantenimiento / BDFL**, con el respaldo de colaboradores de la comunidad. A medida que la comunidad crezca, la gobernanza podrá transicionar hacia un comité directivo.

### Roles y Responsabilidades

#### 1. Mantenedor Principal / Líder del Proyecto
- **Líder Actual**: Rodolfo Concepcion ([@rodolfoconcepcion](https://github.com/rodolfoconcepcion))
- **Responsabilidades**:
  - Definir la dirección arquitectónica, protocolos y la hoja de ruta de lanzamientos.
  - Autoridad final de decisión sobre pull requests, cambios disruptivos (*breaking changes*) y parches de seguridad.
  - Hacer cumplir el [Código de Conducta](CODE_OF_CONDUCT.es.md).
  - Gestionar secretos del repositorio, publicación de paquetes en PyPI e imágenes de contenedores.

#### 2. Colaboradores Principales (*Core Contributors*)
- Colaboradores que demuestren una participación constante y de alta calidad técnica.
- **Responsabilidades**:
  - Triaje de incidencias (*issues*) y pull requests.
  - Revisión de código y control de calidad (pruebas, linting, tipado estático).
  - Ayudar a los usuarios en GitHub Discussions.

#### 3. Colaboradores Comunitarios
- Cualquier persona que reporte un fallo, mejore la documentación, corrija código o responda dudas en la comunidad.
- Toda contribución es bienvenida siempre que se respete nuestro Código de Conducta.

---

## 🗳️ Proceso de Toma de Decisiones

1. **Consenso Aproximado (*Rough Consensus*)**: Los mantenedores y la comunidad debaten cambios arquitectónicos no triviales en GitHub Issues o Discussions. La mayoría de las decisiones se resuelven por consenso constructivo.
2. **Cambios Disruptivos**: Modificaciones en esquemas de base de datos, especificaciones de telemetría o protocolos de certificados mTLS requieren debate documentado y la aprobación del Mantenedor Principal.
3. **Lanzamientos Automatizados**: FleetMate utiliza [Release Please](https://github.com/googleapis/release-please) y Conventional Commits para una gestión semántica y determinista de versiones.

---

## 🔑 Acceso de Commit y Fusión (*Merge*)

- Todo pull request debe superar los controles automatizados de CI (linting, verificación de tipos, pruebas unitarias, CodeQL y escaneo de secretos).
- Los commits se fusionan o compactan (*squash*) siguiendo las directrices de Conventional Commits.
- El acceso directo de commit lo otorga el Mantenedor Principal a colaboradores que demuestren fiabilidad técnica, buen criterio y compromiso activo con la comunidad.
