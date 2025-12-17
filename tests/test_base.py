import sys

print("=== Test base OSINT ===")
print("Ruta del intérprete actual:")
print(sys.executable)

print("\nProbando pandas y requests...")

try:
    import pandas as pd
    import requests
    from dotenv import load_dotenv

    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
    print("\nPandas OK. DataFrame:")
    print(df)

    # Petición sencilla a una web pública
    resp = requests.get("https://httpbin.org/get", timeout=5)
    print("\nRequests OK. Código de estado:", resp.status_code)

    print("\npython-dotenv importado correctamente.")

    print("\n✅ Todo correcto. La base del entorno está funcionando.")
except Exception as e:
    print("\n❌ Algo ha fallado:")
    print(repr(e))
