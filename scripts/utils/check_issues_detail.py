# check_issues_detail.py
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')

print('=== DETALLE INCIDENTES SIN GEO ===')
df = con.execute("""
    SELECT incident_id, tipo_evento, muertos, heridos, titulo
    FROM gold_incidents 
    WHERE departamento IS NULL
    ORDER BY muertos DESC
""").fetchdf()
for _, row in df.iterrows():
    print(f"\n[{row['incident_id']}] {row['tipo_evento']} | M:{row['muertos']} H:{row['heridos']}")
    print(f"  {row['titulo'][:100]}")

print('\n\n=== DETALLE ARTICULOS VICTIMAS ALTAS ===')
df2 = con.execute("""
    SELECT incident_id, tipo_evento, departamento, muertos, heridos, titulo
    FROM gold_incidents 
    WHERE muertos >= 10 OR heridos >= 50
    ORDER BY muertos + heridos DESC
""").fetchdf()
for _, row in df2.iterrows():
    print(f"\n[{row['incident_id']}] {row['tipo_evento']} | {row['departamento']} | M:{row['muertos']} H:{row['heridos']}")
    print(f"  {row['titulo'][:100]}")

con.close()