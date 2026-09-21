"""Load planted-inconsistency demo sets. Used by the eval CLI and /api/demos."""
import json
from pathlib import Path

DEMOS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_scripts"


def list_demo_files() -> list[dict]:
    manifest_path = DEMOS_DIR / "manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data.get("demos", [])
    demos = []
    for path in sorted(DEMOS_DIR.glob("*.json")):
        if path.name == "manifest.json":
            continue
        demos.append({"id": path.stem, "file": path.name, "title": path.stem})
    return demos


def load_demo(name: str) -> dict:
    filename = name if name.endswith(".json") else f"{name}.json"
    # allow ids like weather-easy to map to weather_easy.json
    candidates = [
        DEMOS_DIR / filename,
        DEMOS_DIR / filename.replace("-", "_"),
        DEMOS_DIR / f"{name.replace('-', '_')}.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    available = [p.name for p in DEMOS_DIR.glob("*.json") if p.name != "manifest.json"]
    raise FileNotFoundError(f"No demo '{name}'. Available: {available}")
