"""
Runs the real Continuity pipeline (Extractor -> Comparator -> Legal
Clearance -> Supervisor) against a demo set in data/sample_scripts/ and
reports how many of the planted, known inconsistencies were actually
detected.

Usage:
    export GROQ_API_KEY=your_key
    python -m app.eval                        # runs maya_demo.json (default)
    python -m app.eval weather_easy            # runs weather_easy.json
    python -m app.eval chain_of_custody_hard   # etc.
"""
import json
import os
import sys
from app.agents.supervisor import run_pipeline


def main():
    demo_name = sys.argv[1] if len(sys.argv) > 1 else "maya_demo"
    filename = demo_name if demo_name.endswith(".json") else f"{demo_name}.json"
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_scripts", filename)

    if not os.path.exists(path):
        available = [
            f for f in os.listdir(os.path.dirname(path))
            if f.endswith(".json") and f != "manifest.json"
        ]
        print(f"No demo file '{filename}' found. Available demos: {available}")
        return

    with open(path) as f:
        data = json.load(f)

    report = run_pipeline(data["script_id"], data["scenes"])

    print(f"\n=== Continuity Eval: {data['script_id']} ===")
    print(f"Scenes analyzed: {report.scenes_analyzed}")
    print(f"Facts extracted: {report.facts_extracted}")
    print(f"Conflicts detected: {len(report.conflicts)}")
    print(f"Legal clearance flags: {len(report.clearance_flags)}\n")

    print(f"Ground truth issues planted: {len(data['ground_truth'])}")
    for gt in data["ground_truth"]:
        print(f"  - [{gt['type']}] {gt['description']}")

    print("\nDetected conflicts:")
    for c in report.conflicts:
        print(f"  - [{c.conflict_type}/{c.severity}] {c.summary} "
              f"(confidence {c.confidence:.2f}, scenes {c.source_scene_ids})")

    print("\nDetected legal clearance flags:")
    for f in report.clearance_flags:
        print(f"  - {f.reference_text} ({f.reference_type}): {f.risk_note} "
              f"(confidence {f.confidence:.2f})")

    print(
        "\nNote: matching detected flags back to ground-truth entries is a "
        "manual/eyeball step here by design — the point of this script is "
        "to produce real output from the real pipeline to check against, "
        "not to auto-grade itself."
    )


if __name__ == "__main__":
    main()