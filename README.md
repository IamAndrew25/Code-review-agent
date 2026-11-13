# Code Review Agent

Revisor de posibles problemas de seguridad con un modelo compatible con OpenAI y análisis independiente de Bandit para Python. No ejecuta el proyecto revisado. Los ejemplos vulnerables solo se leen.

## Preparación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configura `OPENAI_BASE_URL`, `OPENAI_API_KEY` y `MODEL` según tu servidor. Por defecto usa `http://localhost:8080/v1` con `mlx-community/Qwen3.6-35B-A3B-4bit`. El código y el contexto seleccionado se envían al servidor configurado.

## Uso

```bash
# JSON, contexto entre archivos y Bandit
python agent.py /ruta/al/proyecto --bandit --max-steps 50

# Reporte Markdown ordenado por gravedad
python agent.py /ruta/al/proyecto --bandit --max-steps 50 --format markdown --output reporte.md

# Archivos que cambiaron respecto de HEAD (incluye cambios preparados y no preparados)
python agent.py /ruta/al/repositorio --changed --bandit

# Comparar con otra revisión de Git
python agent.py /ruta/al/repositorio --changed --base HEAD~1 --bandit
```

Guarda el reporte fuera de la carpeta analizada para evitar revisarlo en una ejecución posterior. Sin ruta se usa `target_project`.

## Cinco capacidades

1. **Contexto entre archivos Python.** Analiza importaciones locales con AST y añade dependencias e importadores hasta dos conexiones. Incluye importaciones relativas, archivos `__init__.py` y líneas numeradas. No importa módulos ni ejecuta código. El contexto se limita a 6.000 caracteres por archivo y 20.000 en total; el reporte registra truncamientos y omisiones. `--no-context` lo desactiva. Las importaciones dinámicas y otros lenguajes no tienen resolución de contexto.
2. **Cambios de Git.** `--changed` revisa el contenido actual completo de los archivos distintos de `--base`, además de archivos nuevos no ignorados por Git. No se limita a líneas modificadas y no analiza el índice como una versión separada. Los archivos eliminados se enumeran, pero no se analiza su contenido anterior. Requiere la raíz de un repositorio con al menos un commit. Los archivos relacionados sin cambios pueden usarse como contexto, aunque no sean objetivos de la revisión.
3. **Reporte legible.** `--format markdown` muestra gravedad estimada, archivo, línea, fragmento, riesgo, solución, cobertura y exclusiones. El fragmento se valida contra el código enviado. Esto no valida la interpretación del modelo.
4. **Bandit.** `--bandit` ejecuta sus reglas sobre los archivos Python seleccionados y entrega los candidatos de gravedad media o alta al modelo como pistas que este debe verificar. Conserva las alertas originales de Bandit por separado aunque el modelo las omita. Coincidir en una línea no demuestra que ambos diagnósticos sean equivalentes. Una alerta estática tampoco demuestra explotabilidad. Los errores del analizador hacen que el resultado general sea incompleto. Documentación: https://bandit.readthedocs.io/en/latest/man/bandit.html
5. **Evaluación reproducible.** Pruebas unitarias, CLI, casos aislados y dos proyectos de tres archivos (rutas, consultas y repositorio), uno vulnerable y otro con parámetros. Incluye una regresión de Git con un cambio inseguro y contexto de los archivos no modificados.

## Límites y estados

Los archivos objetivo se procesan por fragmentos de 5.000 caracteres y cada llamada consume un paso. La cobertura `complete` significa que el contenido seleccionado se procesó sin los errores registrados; no certifica ausencia de vulnerabilidades ni comprensión completa del proyecto. Los fragmentos del mismo archivo todavía se analizan por separado. Las importaciones se resuelven estáticamente y el contexto es acotado.

Se excluyen explícitamente `.git`, `.venv`, `venv`, `__pycache__`, `node_modules`, `.pytest_cache`, archivos `.env*` y bytecode. Los enlaces simbólicos no se siguen. Archivos binarios, ilegibles o mayores de 2 MB figuran como no revisados. Las exclusiones y la cobertura quedan visibles. Los secretos en archivos de código sí pueden analizarse; no se garantiza excluir cualquier archivo sensible.

Códigos de salida: **0** revisión completa, con o sin hallazgos; **2** argumentos o referencia Git inválidos; **3** revisión incompleta. Para decidir si hay hallazgos, consulta `findings` y `static_analysis.findings` del JSON.

## Pruebas

```bash
python -m unittest discover -s tests -v
python verify_cli.py
python benchmark.py
python benchmark.py --bandit
python evaluate.py
python evaluate_projects.py
```

Las pruebas unitarias usan respuestas simuladas y Bandit real cuando está instalado. Los otros scripts usan el modelo real. `evaluate_projects.py` prueba las nuevas funciones juntas y guarda `project-evaluation-results.json` y `example-report.md`. Las pruebas se ajustaron durante el desarrollo: son regresiones, no una evaluación independiente sobre código de producción. Consulta `TEST_RESULTS.md` para ver los resultados de la versión entregada.
