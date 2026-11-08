# Guía de Contribución para FleetMate

[English](CONTRIBUTING.md) | [Español](CONTRIBUTING.es.md)

¡Gracias por tu interés en contribuir a **FleetMate**! 🚗⚡

FleetMate es un motor de transmisión mTLS y puente de telemetría de alta velocidad y coste cero para TeslaMate y Home Assistant. Agradecemos enormemente las contribuciones de desarrolladores y propietarios de Tesla de todo el mundo.

---

## Código de Conducta

Al participar en este proyecto, aceptas cumplir con nuestro [Código de Conducta](CODE_OF_CONDUCT.es.md). Puedes reportar comportamientos inaceptables de forma privada a través de [GitHub Security Advisories](https://github.com/rodolfoconcepcion/fleetmate/security/advisories).

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
¡No necesitas hablar ambos idiomas para contribuir a FleetMate! Contamos con herramientas de asistencia de IA:
1. **Envía tu PR con normalidad**: Realiza tus cambios o mejoras en los archivos en inglés (`README.md`, `ROADMAP.md`, etc.).
2. **Utiliza CodeRabbit AI**: CodeRabbit está integrado en este repositorio y revisa automáticamente cada Pull Request. Puedes solicitarle la traducción directamente en cualquier comentario del PR:
   ```text
   @coderabbitai please generate the Spanish translation for my changes in README.md
   ```
3. **Confirma la traducción**: Revisa la traducción sugerida por CodeRabbit y confírmala en tu rama (o un mantenedor te asistirá con gusto antes de fusionar).
4. **Protección Automatizada en CI**: Nuestra suite de CI ejecuta `tests/test_doc_parity.py` en cada PR para verificar que todos los documentos clave, versiones y enlaces de cambio de idioma permanezcan 100% sincronizados.

### Opciones alternativas:
- **Traducción manual**: Si dominas ambos idiomas (u otros idiomas soportados), eres muy bienvenido a incluir directamente las traducciones en `*.es.md`.
- **Asistencia del mantenedor**: Si prefieres no utilizar IA, simplemente abre tu PR con tus cambios en inglés y solicita asistencia en la descripción. Nosotros nos encargaremos de traducirlo antes de fusionar.
