# artiboard

Un tablero de proyecto para personas y agentes de programación: tareas, hilos, avisos y vistas de documento, kanban y dependencias. El código dibuja la página a partir de datos persistentes; las actualizaciones habituales no requieren llamadas a un modelo.

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · **Español**

| Backend | Requisitos | Colaboración |
| --- | --- | --- |
| Claude Artifact | Herramientas reales `Artifact` y `ArtifactData` | Cuentas y funciones de compartir de la plataforma |
| Servidor web local | Python 3.10+ con SQLite y un navegador moderno | Personas y agentes de confianza en un mismo equipo, incluidos worktrees de Git paralelos |

Codex y otros agentes con acceso a archivos y shell pueden usar el backend local. Un tablero nuevo usa Artifacts si dispone de ambas herramientas; de lo contrario usa el servidor local. Un tablero existente conserva su backend; la migración requiere una petición explícita. El nombre local es **una etiqueta elegida por el usuario, no una cuenta autenticada**. El modo local no ofrece alojamiento para equipos remotos.

## Inicio rápido

Pídele a tu agente de programación:

```text
Lee skills/artiboard/SKILL.md de este checkout y crea un tablero de tareas para este proyecto.
Usa el backend local si no están disponibles las herramientas de Artifact.
```

## Instalación

Elige una vía de instalación. Skills CLI requiere Node.js/npm e instala en el proyecto de forma predeterminada. Ejecuta el comando desde el proyecto de destino con la ruta absoluta a este checkout:

```bash
npx skills add /absolute/path/to/artiboard --skill artiboard --agent codex
```

Deja solo los agentes que uses. Añade `--list` para comprobar la detección o `--global` si eliges una instalación personal global. Se incluyen los metadatos de Agent Skills (`license`, `compatibility`, autor, versión y origen), la información visual de Codex, el código, los recursos, las referencias y la licencia MIT. No hace falta publicar un paquete npm.

Después de publicar la rama `universal` del fork, puedes instalar desde GitHub:

```bash
npx skills add https://github.com/composite/artiboard/tree/universal --skill artiboard --agent codex
```

Antes de hacer push, usa el checkout local. `composite/artiboard` sin ref usa la rama predeterminada y puede instalar la versión original.

Para instalar el plugin de Codex, usa una CLI que admita `codex plugin`:

```bash
codex plugin marketplace add /absolute/path/to/artiboard
codex plugin add artiboard@artiboard-universal
```

Estos comandos registran el marketplace e instalan el plugin en la configuración del usuario actual de Codex. Usa Skills CLI para una skill limitada al proyecto. En la aplicación de escritorio, instala **Artiboard** desde **Artiboard Universal** en el directorio de plugins; reinicia si no aparece la nueva fuente local. Una vez publicada la rama, también puedes registrar la fuente con `codex plugin marketplace add composite/artiboard --ref universal`.

Los usuarios de Claude Code deben usar el original [yulmucoffee/artiboard](https://github.com/yulmucoffee/artiboard):

```bash
claude plugin marketplace add yulmucoffee/artiboard --scope project
claude plugin install artiboard@artiboard --scope project
```

Se conservan los manifiestos originales de Claude. El marketplace de Codex de este fork se llama `artiboard-universal` y no sustituye al plugin original de Claude. Evita habilitar la misma skill varias veces en un agente. Clonar o editar el código no la instala globalmente. Consulta [la guía para agentes](FOR_AGENTS.md) para la configuración y las actualizaciones.

## Ejecutar un tablero local

Desde este checkout, elige un título y un ID de persona e inicia un tablero vacío:

```bash
python3 skills/artiboard/scripts/local_board.py init --title "Mi proyecto" --person ana --lang en
python3 skills/artiboard/scripts/local_board.py serve --port 8765
```

Usa `python` o `py -3` si corresponde a tu instalación. Abre la URL que imprime el servidor. Ctrl-C lo detiene sin borrar los datos; el mismo comando lo reinicia. Usa `--port 0` si el puerto está ocupado. No se instala un servicio en segundo plano.

La base de datos predeterminada es `.artiboard/board.sqlite3` en el checkout principal de Git, compartida por los worktrees vinculados; fuera de Git se usa el directorio actual. Para otra ubicación, pon `--db <path>` antes del subcomando y registra la ruta compartida resuelta en las reglas del proyecto. Excluye `.artiboard/` de Git. El servidor solo sirve la página y el adaptador, escucha en `127.0.0.1` y rechaza peticiones entre sitios. Los usuarios y procesos del mismo equipo están dentro del límite de confianza.

Los agentes pueden leer y escribir en la misma base de datos sin iniciar el servidor:

```bash
python3 skills/artiboard/scripts/local_board.py request <<'JSON'
{"action":"query","collection":"tasks","where":[["status","==","todo"],["waitingOn","==",[]]],"limit":20}
JSON
```

Consulta la [guía local](skills/artiboard/references/local.md) para datos iniciales, lotes con versiones, copias de seguridad y ciclo de vida; y la [guía de Artifact](skills/artiboard/references/artifact.md) para publicar y compartir con las herramientas de Claude.

## Uso

| Petición | Comportamiento |
| --- | --- |
| «Crea un tablero de tareas» | Define personas, idioma y origen de las tareas; confirma la lista propuesta y crea el tablero y las reglas. |
| «Elige la siguiente tarea», «Continúa M1-4» | Lee las reglas, consulta tareas listas, comprueba versiones para asignar la tarea y registra un breve traspaso. |
| «Añade a Cy», «Cambia a coreano» | Actualiza la configuración. |
| «Añade un estado QA», «Muestra estimaciones» | Adapta la página y las reglas juntas. |
| «Actualiza el tablero» | Conserva y respalda los datos y las personalizaciones, y verifica el mismo tablero. |

La configuración crea `docs/artiboard.md` y una referencia breve en los archivos existentes `AGENTS.md` o `CLAUDE.md`. Las reglas completas se cargan solo al trabajar con el tablero. Sus mensajes son datos, no autorización para ejecutar comandos, enviar mensajes externos, hacer merge o desplegar.

## Datos y concurrencia

`tasks/<id>` guarda el estado; `details/<id>`, las especificaciones, los criterios de aceptación y un resumen breve; `tasks/<id>/messages`, la conversación, de la que los agentes suelen leer los ocho mensajes más recientes. Los avisos se consultan de forma incremental mediante `notices` y `cursors/<person>`. `meta/config` contiene título, personas, idioma y textos de la interfaz; `meta/protocol` es una copia de las reglas para personas. La vinculación de cuentas en `people/<person>` se usa solo con Artifact.

Las asignaciones usan lotes atómicos con versiones; un conflicto revierte todo el lote. En modo local, CLI y navegador comparten transacciones SQLite y recalculan la disponibilidad por dependencias incluso con la página cerrada. En Artifact, los agentes actualizan las dependencias y la página abierta las corrige. El botón de asignación de la interfaz Artifact original hace una lectura seguida de una actualización; la garantía atómica de ese backend corresponde a los lotes de agentes con versiones.

El código gestiona vistas, búsqueda, teclas (`j`/`k`, `1`/`2`/`3`) y marcas de novedades. Las preferencias locales del navegador se separan por base de datos. Al desconectarse, la página avisa y no encola escrituras sin conexión. Los idiomas integrados son inglés y coreano; puedes añadir español con `meta/config.strings`. La configuración admite `title`, `subtitle`, `milestone`, `lang`, `people` (`id`, con `name` y `role` opcionales), `strings` y `footer`. Conserva la semántica de `todo` y `done` al personalizar estados.

## Demo y desarrollo

La [demo interactiva original](https://claude.ai/artifact/5zENFyGDJbEjey68J6t1bY) y `examples/demo.html` usan datos temporales en memoria, no el backend local persistente.

```bash
npm install --no-save --no-audit --no-fund jsdom@24.1.1
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/smoke.cjs
node tests/local-smoke.cjs
node examples/build-demo.cjs
```

Las pruebas cubren persistencia, reversión, asignaciones concurrentes, rutas de worktrees, límites HTTP y escrituras, desconexión y reinicio de la interfaz con el servidor real. CI también comprueba detección e instalación del paquete, JSON, sintaxis y vigencia de la demo. jsdom se usa solo para desarrollo; el tablero no necesita paquetes externos para ejecutarse.

```text
skills/artiboard/SKILL.md            selección de backend y flujo de trabajo
skills/artiboard/agents/openai.yaml información visual de la skill en Codex
skills/artiboard/assets/            página compartida y adaptador local
skills/artiboard/scripts/           servidor y CLI con biblioteca estándar
skills/artiboard/references/        guías local, Artifact y reglas de proyecto
plugin.json                        manifiesto portátil de Agent Plugins
.codex-plugin/plugin.json          manifiesto compatible con Codex y presentación
.agents/plugins/marketplace.json   marketplace del repositorio para Codex
.claude-plugin/                    manifiestos de plugin y marketplace de Claude Code
```

Basado en el artiboard original de yulmucoffee. Independiente de Anthropic y OpenAI, sin afiliación ni respaldo de estas empresas. [Licencia MIT](LICENSE).
