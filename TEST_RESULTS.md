# Resultado de las cinco mejoras

Se implementaron y verificaron las cinco capacidades en la copia local del Code Review Agent.

## Funciones entregadas

1. Contexto entre archivos Python: resolución de importaciones locales, importadores y dependencias hasta dos conexiones. No ejecuta el código. Límites visibles de 6.000 caracteres por archivo y 20.000 en total.
2. Revisión de Git: `--changed --base HEAD` selecciona archivos con cambios preparados, no preparados y archivos nuevos no ignorados. Revisa cada archivo seleccionado completo, con contexto de los relacionados. Enumera los eliminados.
3. Reporte Markdown: `--format markdown --output reporte.md`, ordenado por gravedad estimada, con archivo, línea, fragmento, riesgo, solución, cobertura y exclusiones.
4. Bandit para Python: `--bandit`, resultados independientes y candidatos de gravedad media/alta como pistas para el modelo. Las advertencias de baja gravedad se conservan en el reporte, sin usarlas como pistas. Coincidir en ubicación no demuestra que ambos diagnósticos sean correctos ni equivalentes.
5. Pruebas más realistas: dos proyectos de tres archivos (rutas HTTP, construcción de consultas y acceso a base de datos), más un cambio inseguro en Git analizado con los otros archivos como contexto.

## Resultados finales observados

| Prueba | Resultado |
|---|---|
| Pruebas automatizadas | 19/19 aprobadas, incluido Bandit real |
| Casos aislados con modelo, sin Bandit | 10/10 aprobados |
| Casos aislados con modelo y Bandit | 10/10 aprobados para los hallazgos del modelo |
| Ejecución desde CLI y manejo de errores | 8/8 aprobados |
| Proyectos de varios archivos y cambios de Git | 8/8 comprobaciones aprobadas |
| Ejemplo vulnerable original, tres repeticiones | Detectó ambos problemas en las tres |
| Ejemplo seguro original, tres repeticiones | Ninguna alerta del modelo |
| Archivo largo | Detectó el problema al final, línea 603 |

Modelo local: `mlx-community/Qwen3.6-35B-A3B-4bit`, servidor `localhost:8080/v1`. Bandit instalado: 1.9.4.

En el proyecto vulnerable, la IA señaló tres ubicaciones del mismo flujo de inyección SQL y Bandit detectó B608. No son tres vulnerabilidades independientes. En el proyecto seguro, ambos devolvieron cero alertas. En la prueba de Git, solo se revisó queries.py como objetivo; se aportó contexto de routes.py y repository.py, y ambos analizadores señalaron la consulta insegura.

## Fallos encontrados y corregidos durante la implementación

- Una consulta construida con interpolación podía pasar inadvertida cuando después se suministraba una tupla vacía como parámetros. Las pistas independientes de Bandit ayudaron al modelo a reconocerla; el caso quedó incluido en la regresión.
- Entregar todas las advertencias estáticas podía inducir falsas alarmas sobre comandos seguros. Ahora solo se suministran pistas de gravedad media/alta; se mantienen todas las alertas estáticas por separado.
- Se normalizó la gravedad devuelta por el modelo y se precisó su formato para que el reporte pudiera ordenarla correctamente.

## Cómo reproducir

```bash
python -m unittest discover -s tests -v
python benchmark.py
python benchmark.py --bandit
python verify_cli.py
python evaluate.py
python evaluate_projects.py
```

Instala primero requirements.txt y configura el servidor del modelo según README.md. Los scripts generan los resultados completos en benchmark-results.json, benchmark-bandit-results.json, cli-results.json, evaluation-results.json y project-evaluation-results.json. Estos archivos generados no se versionan. example-report.md contiene el reporte de muestra generado a partir del proyecto vulnerable.

## Límites de la verificación

Las pruebas se ajustaron durante el desarrollo: son regresiones, no validación independiente en proyectos de producción. Los proyectos de varios archivos siguen siendo pequeños. El contexto usa importaciones Python estáticas; no resuelve importaciones dinámicas, todos los frameworks ni otros lenguajes. El modo Git revisa archivos completos cambiados, no únicamente líneas nuevas. No analiza el contenido anterior de archivos eliminados.

Bandit conserva advertencias que pueden ser falsos positivos: por ejemplo, emitió tres advertencias de baja gravedad sobre el caso de subprocess seguro, aunque la IA no reportó vulnerabilidades en él. Los resultados de ambos requieren interpretación. El modelo puede exagerar el impacto en sus descripciones. La gravedad es estimada y el reporte no certifica explotabilidad.

La cobertura complete se refiere al procesamiento del alcance seleccionado. Los fragmentos del mismo archivo aún se analizan por separado; el contexto relacionado es limitado y se documentan los truncamientos. Se excluyen carpetas generadas, Git y archivos .env; se registran los archivos ilegibles y los límites.

Los resultados corresponden a la versión de código entregada con estas pruebas.
