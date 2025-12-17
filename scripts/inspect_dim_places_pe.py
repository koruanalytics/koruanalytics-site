import duckdb

con = duckdb.connect("data/osint_dw.duckdb")

print("Columns in dim_places_pe:")
print(con.execute("select count(*) from pragma_table_info('dim_places_pe')").fetchone())

print("\nRows in dim_places_pe:")
print(con.execute("select count(*) as n from dim_places_pe").df())

print("\nSample:")
print(con.execute("""
select
  place_id, adm1_name, adm2_name, adm3_name, lat, lon
from dim_places_pe
limit 5
""").df())

con.close()

