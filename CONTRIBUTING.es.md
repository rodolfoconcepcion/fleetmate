# Guía de Contribución para FleetMate

¡Gracias por tu interés en contribuir a **FleetMate**! 🚗⚡

FleetMate es un motor de transmisión mTLS y puente de telemetría de alta velocidad y coste cero para TeslaMate y Home Assistant. Agradecemos enormemente las contribuciones de desarrolladores y propietarios de Tesla de todo el mundo.

---

## Código de Conducta

Al participar en este proyecto, aceptas cumplir con nuestro [Código de Conducta](CODE_OF_CONDUCT.es.md). Puedes reportar comportamientos inaceptables a [rodolfo.concepcion@gmail.com](mailto:rodolfo.concepcion@gmail.com).

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
