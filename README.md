# Systematic Review Tool

> **Portfolio / Demo Version** — esta rama `demo` está preparada para mostrar el proyecto de forma rápida, segura y con datos ficticios.

## Descripción

Aplicación web colaborativa para gestionar la selección de estudios de una revisión sistemática. Permite importar referencias de Web of Science o Scopus, revisar títulos y resúmenes, comparar decisiones entre revisores, resolver conflictos, registrar motivos de exclusión y exportar resultados a Excel.

Este proyecto se desarrolló para cubrir las necesidades personalizadas de un proyecto de revisión sistemática, adaptando el flujo de trabajo a sus fases de selección, coordinación entre revisores y extracción de estudios.

La inteligencia artificial se utilizó como herramienta de apoyo durante su elaboración, especialmente para asistir en tareas de desarrollo, depuración y documentación, manteniendo la revisión y validación humana de las decisiones técnicas.

La rama **`demo`** utiliza una base de datos local con contenido de ejemplo para que cualquiera pueda probar el flujo sin cuentas ni credenciales.

El proyecto completo de la rama **`main`** se despliega como aplicación web con **PostgreSQL** y utiliza **Tailscale** para conectar de forma privada distintos equipos, permitiendo que varias personas trabajen juntas sobre la misma revisión.

## Cómo probar la demo

No necesitas PostgreSQL, Tailscale, contraseñas ni claves de API. Elige solo una opción:

### 1. Ejecutable para Windows — recomendado

La forma más sencilla: no requiere instalar Python, Git ni Docker.

1. Abre la [última versión publicada](https://github.com/DiegoJSN/syst_rev_tool/releases/latest).
2. En **Assets**, descarga `SystRevTool-Demo-Windows.zip`.
3. Haz clic derecho sobre el ZIP y selecciona **Extraer todo**.
4. Abre la carpeta extraída y ejecuta `SystRevTool-Demo.exe`.
5. Mantén abierta la ventana negra mientras utilizas la demo. El navegador se abrirá automáticamente.

Para terminar, cierra la ventana negra. No ejecutes versiones antiguas que Microsoft Defender haya identificado como malware; descarga siempre la versión más reciente desde este repositorio.

### 2. Con Python

Requiere [Git](https://git-scm.com/downloads) y [Python 3.11 o superior](https://www.python.org/downloads/).

**Windows — PowerShell:**

```powershell
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

**macOS o Linux — Terminal:**

```bash
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
sh ./run_demo.sh
```

Cuando aparezca la dirección local, abre <http://127.0.0.1:5000>. Para detener la aplicación, vuelve a la terminal y pulsa **Ctrl+C**.

### 3. Con Docker Desktop

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/).

1. Descarga la rama [`demo`](https://github.com/DiegoJSN/syst_rev_tool/tree/demo) mediante **Code → Download ZIP** y extrae el archivo.
2. Abre una terminal dentro de la carpeta extraída.
3. Ejecuta:

```bash
docker build -t syst-rev-demo .
docker run --rm -p 5000:5000 syst-rev-demo
```

Abre <http://127.0.0.1:5000>. Para detener la demo, pulsa **Ctrl+C**.

## Qué puedes probar

- Revisar títulos y resúmenes con distintos revisores.
- Escribir notas y guardar decisiones de inclusión o exclusión.
- Generar conflictos cuando dos revisores discrepan y resolverlos desde la aplicación.
- Cerrar la demo y continuar más tarde: el progreso se conserva en SQLite.
- Crear motivos de exclusión.
- Ver el progreso y la contribución de cada revisor.
- Importar los ejemplos incluidos de Web of Science y Scopus.
- Exportar decisiones y listados a Excel.
- Restaurar los datos iniciales con el botón **Reset demo**.

## Tecnología y funcionamiento

- **Python + Flask:** lógica del servidor, rutas y flujo de revisión.
- **Jinja2, Bootstrap y DataTables:** interfaz web renderizada en el navegador.
- **PostgreSQL + Psycopg:** almacenamiento centralizado de la versión completa y colaborativa.
- **Tailscale:** conexión privada entre los equipos que acceden al despliegue completo.
- **SQLite:** base de datos local sin configuración que conserva decisiones, notas, conflictos y resoluciones de la demo.
- **OpenPyXL y Python Calamine:** importación y exportación de hojas de cálculo.
- **Docker y Gunicorn:** empaquetado y ejecución reproducible de la aplicación.

## Limitaciones de la demo

Los datos son ficticios, el acceso de revisores no es autenticación segura y el almacenamiento local no está pensado para investigación real o información sensible. Esta rama conserva el flujo principal del proyecto, pero sustituye la infraestructura privada de PostgreSQL y Tailscale por SQLite para facilitar la prueba.

---

La rama `demo` ha sido preparada específicamente como **versión demostrativa para portfolio**. El desarrollo completo se mantiene en la rama `main`.
