import os

files_to_show = [
    'src/enrichment/llm_enrichment_pipeline.py',
    'scripts/core/daily_pipeline.py'
]

for filepath in files_to_show:
    if os.path.exists(filepath):
        print(f'\n{"="*60}')
        print(f'ARCHIVO: {filepath}')
        print("="*60)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Mostrar primeras 150 líneas
            lines = content.split('\n')[:150]
            for i, line in enumerate(lines, 1):
                print(f'{i:4}: {line}')
            if len(content.split('\n')) > 150:
                print(f'\n... [{len(content.split(chr(10)))} líneas total]')
    else:
        print(f'\nNO EXISTE: {filepath}')