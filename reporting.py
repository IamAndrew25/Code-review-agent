"""Readable Markdown output; model severity is an estimate, not a verified rating."""
import html

ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'unknown': 4}


def esc(value):
    return html.escape(str(value)).replace('`', '&#96;').replace('*', '&#42;').replace('_', '&#95;').replace('[', '&#91;').replace(']', '&#93;').replace('\n', '<br>')


def render_markdown(report):
    lines = ['# Revisión de seguridad', '', f"Estado: **{report['status']}**", '',
             f"Alcance: {esc(report.get('scope', {}).get('mode', 'all'))}. Llamadas al modelo: {report['model_calls']}.",
             'Cobertura completa no significa ausencia de vulnerabilidades. La gravedad de la IA es una estimación.', '',
             '## Hallazgos del modelo', '']
    if not report['findings']:
        lines.append('No se registraron hallazgos del modelo. Consulta la cobertura y los errores antes de interpretar este resultado.')
    for f in sorted(report['findings'], key=lambda f: (ORDER.get(f.get('severity'), 4), f['file'], f['line'])):
        lines += [f"### {esc(f.get('severity', 'unknown').upper())} · {esc(f['file'])}:{f['line']}",
                  '', esc(f['problem']), '', f"**Código:** <code>{esc(f['snippet'])}</code>", '',
                  '**Riesgo:** ' + esc(f['risk']), '', '**Solución:** ' + esc(f['fix']), '']
        if f.get('static_matches'):
            lines += ['Bandit también señaló esta ubicación: ' + ', '.join(f['static_matches']) + '. Esto no confirma que ambos diagnósticos sean equivalentes.', '']
    lines += ['## Análisis estático independiente', '']
    static = report.get('static_analysis', {})
    lines.append('Estado: ' + esc(static.get('status', 'disabled')))
    for f in sorted(static.get('findings', []), key=lambda f: ORDER.get(f['severity'], 4)):
        lines.append(f"- **{esc(f['severity'].upper())} {esc(f['rule'])}** {esc(f['file'])}:{f['line']} — {esc(f['problem'])}")
    for error in static.get('errors', []):
        lines.append('- Error: ' + esc(error))
    lines += ['', '## Cobertura', '']
    for item in report['coverage']:
        lines.append(f"- {esc(item['file'])}: **{item['status']}**. {esc(item.get('reason', ''))}")
        context = item.get('context', {})
        if context.get('files'):
            lines.append('  Contexto: ' + esc(', '.join(context['files'])))
        if context.get('truncated') or context.get('omitted'):
            lines.append('  Contexto limitado: ' + esc(context))
    lines += ['', '## Exclusiones y archivos eliminados', '']
    for item in report.get('excluded', []) + report.get('skipped', []) + report.get('scope', {}).get('deleted', []):
        lines.append('- ' + esc(item))
    return '\n'.join(lines) + '\n'
