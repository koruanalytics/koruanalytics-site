# check_issues.py
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')

print('=== 1. REGISTROS NO_RELEVANTE EN GOLD ===')
df = con.execute("""
    SELECT incident_id, tipo_evento, LEFT(titulo, 60) as titulo, muertos, heridos
    FROM gold_incidents 
    WHERE tipo_evento = 'no_relevante'
""").fetchdf()
print(df)
print(f'Total: {len(df)} registros a eliminar')

print('\n=== 2. INCIDENTES SIN GEOLOCALIZACION ===')
df2 = con.execute("""
    SELECT incident_id, tipo_evento, LEFT(titulo, 60) as titulo, muertos, heridos
    FROM gold_incidents 
    WHERE departamento IS NULL
    ORDER BY muertos DESC
""").fetchdf()
print(df2)

print('\n=== 3. POSIBLES ARTICULOS DE RESUMEN (VICTIMAS ALTAS) ===')
df3 = con.execute("""
    SELECT incident_id, tipo_evento, departamento, muertos, heridos, 
           LEFT(titulo, 70) as titulo
    FROM gold_incidents 
    WHERE muertos >= 10 OR heridos >= 50
    ORDER BY muertos + heridos DESC
""").fetchdf()
print(df3)

con.close()
