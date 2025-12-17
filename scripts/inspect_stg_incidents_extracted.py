import duckdb

con = duckdb.connect("data/osint_dw.duckdb")
print(con.execute("describe stg_incidents_extracted").df())
con.close()
