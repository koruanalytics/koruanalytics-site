from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def flatten_keys(obj: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            keys.append(path)
            keys.extend(flatten_keys(v, path))
    elif isinstance(obj, list):
        # no “explosionar”: inspeccionamos solo el primer elemento
        if obj:
            keys.extend(flatten_keys(obj[0], prefix + "[]"))
    return keys


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventario de campos devueltos por NewsAPI.ai (RAW JSON).")
    parser.add_argument("--raw", required=True, help="Ruta del JSON RAW generado (data/raw/newsapi_ai/xxxx.json)")
    parser.add_argument("--out", default=None, help="Ruta opcional salida JSON con inventario")
    args = parser.parse_args()

    raw_path = Path(args.raw)
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    articles = payload.get("articles", [])

    counter = Counter()
    for a in articles:
        for k in flatten_keys(a):
            counter[k] += 1

    print(f"RAW: {raw_path}")
    print(f"Artículos analizados: {len(articles)}")
    print("\nTop 80 keys (más frecuentes):")
    for k, c in counter.most_common(80):
        print(f"{c:>4}  {k}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "raw_file": str(raw_path).replace("\\", "/"),
                    "article_count": len(articles),
                    "keys": counter.most_common(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nInventario guardado en: {out_path}")


if __name__ == "__main__":
    main()
