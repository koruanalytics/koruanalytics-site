from pathlib import Path
import sys

# --- AÑADIR RAÍZ DEL PROYECTO AL sys.path --------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# --------------------------------------------------------------

import duckdb
import streamlit as st

from src.utils.config import load_config


def get_connection():
    """
    Devuelve una conexión a la base DuckDB definida en config/settings.yaml
    """
    cfg = load_config()
    db_path = Path(cfg["db"]["duckdb_path"])
    return duckdb.connect(str(db_path))


st.title("2026 EOM Peru - Dashboard básico de noticias (dummy)")

con = get_connection()
df = con.execute("SELECT * FROM stg_news_dummy").fetch_df()
con.close()

st.subheader("Resumen")
st.write(f"Número de noticias dummy: {len(df)}")

if not df.empty:
    st.subheader("Columnas disponibles en stg_news_dummy")
    st.write(list(df.columns))

    st.subheader("Noticias dummy")

    # columnas "ideales" que nos gustaría mostrar
    desired_cols = ["published_at", "country", "title", "content"]

    # nos quedamos solo con las que EXISTEN en el DataFrame
    cols_to_show = [c for c in desired_cols if c in df.columns]

    # si por lo que sea no hay ninguna de esas, mostramos todo
    if cols_to_show:
        st.dataframe(df[cols_to_show])
    else:
        st.dataframe(df)
else:
    st.write("No hay noticias en la tabla stg_news_dummy. Ejecuta primero el pipeline dummy.")
