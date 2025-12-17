from src.utils.config import load_config

cfg = load_config()
print("=== Config cargada ===")
print(cfg)

print("\nRutas de datos:")
for k, v in cfg["data_paths"].items():
    print(f" - {k}: {v}")

print("\nRuta DuckDB:", cfg["db"]["duckdb_path"])