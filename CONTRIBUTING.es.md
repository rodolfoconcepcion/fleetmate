# Guía de Contribución para FleetMate

[English](CONTRIBUTING.md) | [Español](CONTRIBUTING.es.md)

¡Gracias por tu interés en contribuir a **FleetMate**! 🚗⚡

FleetMate es un motor de transmisión mTLS y puente de telemetría de alta velocidad y coste cero para TeslaMate y Home Assistant. Agradecemos enormemente las contribuciones de desarrolladores y propietarios de Tesla de todo el mundo.

---

## Código de Conducta

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:abf0aa05d43e0031feae45157676ec859900509efc21ab00b1a04760cb04e335 -->

Al participar en este proyecto, aceptas cumplir con nuestro [Código de Conducta](CODE_OF_CONDUCT.es.md). Reporta el acoso u otros comportamientos inaceptables de forma privada mediante el [formulario de GitHub Security Advisories](https://github.com/rodolfoconcepcion/fleetmate/security/advisories/new) (requiere iniciar sesión en GitHub).

Usa el título «Reporte del Código de Conducta» y describe el incidente, las fechas o enlaces relevantes y su impacto en la descripción. Este formulario también acepta reportes de conducta: no se requiere una vulnerabilidad de seguridad ni una prueba de concepto. Sustituye las indicaciones de la plantilla sobre vulnerabilidades por tu reporte; en los campos obligatorios que no correspondan, incluida la prueba de concepto, escribe «No aplica — reporte de conducta». Haz clic en **Submit report** para enviarlo de forma privada a los mantenedores del repositorio. No publiques detalles sensibles en issues o debates públicos.

<!-- /coderabbit-ai-generated:v1 -->

---

## Configuración de Desarrollo Local

FleetMate utiliza Python 3.12+ asíncrono y [`uv`](https://docs.astral.sh/uv/) para la gestión de dependencias:

```bash
git clone https://github.com/<tu-usuario>/fleetmate.git
cd fleetmate
uv sync --all-extras
source .venv/bin/activate
fleetmate --help
```

---

## Pruebas y Calidad de Código

Antes de abrir una solicitud de extracción (PR), asegúrate de que todas las pruebas y análisis estáticos pasen correctamente:

```bash
# Ejecutar suite de pruebas
pytest --cov=src/fleetmate tests/

# Formato y linter
ruff check src tests
ruff format src tests

# Verificación de tipos estáticos
mypy src
```

---

## Convenciones de Commits

Seguimos la convención de [Conventional Commits](https://www.conventionalcommits.org/):

* `feat:` Nuevas funcionalidades
* `fix:` Correcciones de errores o parches de seguridad
* `docs:` Actualizaciones de documentación
* `test:` Adición o mejora de pruebas unitarias
* `chore:` Actualización de dependencias o herramientas de desarrollo

> [!IMPORTANT]
> Recuerda que los mensajes de commit, descripciones de PR y comentarios de código deben estar redactados en **inglés**.

---

## Documentación Multilingüe y Asistencia con IA (CodeRabbit)

FleetMate mantiene una **paridad documental multilingüe** completa (cada guía en inglés cuenta con su respectiva versión en español, ej. `README.md` y `README.es.md`).

### Si no dominas el español o el inglés:
¡No necesitas hablar ambos idiomas para contribuir a FleetMate! Si solo hablas español, puedes proponer tus cambios en español en un issue y solicitar ayuda de un mantenedor para traducirlos a los archivos originales en inglés.

Si puedes contribuir en inglés, contamos con herramientas de asistencia de IA:
1. **Envía tu PR con normalidad**: Realiza tus cambios o mejoras en los archivos en inglés (`README.md`, `ROADMAP.md`, etc.).
2. **Utiliza CodeRabbit AI**: CodeRabbit está integrado en este repositorio y revisa automáticamente cada Pull Request. Puedes solicitarle la traducción directamente en cualquier comentario del PR:
   ```text
   @coderabbitai please generate the Spanish translation for my changes in README.md
   ```
3. **Confirma la traducción**: Revisa la traducción sugerida por CodeRabbit y confírmala en tu rama (o un mantenedor te asistirá con gusto antes de fusionar).
4. **Protección Automatizada en CI**: Nuestra suite de CI ejecuta `tests/test_doc_parity.py` en los PR dirigidos a `main` para comprobar que existan los archivos de documentación correspondientes, que los encabezados de versiones del changelog en inglés aparezcan en los changelogs traducidos y que los documentos clave tengan enlaces para cambiar de idioma. No comprueba si el contenido traducido está sincronizado.

### Opciones alternativas:
- **Traducción manual**: Si dominas ambos idiomas (u otros idiomas soportados), eres muy bienvenido a incluir directamente las traducciones en `*.es.md`.
- **Asistencia del mantenedor**: Si prefieres no utilizar IA, simplemente abre tu PR con tus cambios en inglés y solicita asistencia en la descripción. Nosotros nos encargaremos de traducirlo antes de fusionar.
