import csv
from collections import defaultdict
from pathlib import Path

path = Path("tests/voice/scenarios.csv")
with path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

tested = [r for r in rows if r["actual_intent"].strip()]
correct = [r for r in tested if r["actual_intent"].strip() == r["expected_intent"].strip()]

print(f"Tested: {len(tested)} of {len(rows)}")

if not tested:
    print("No results yet. Fill in actual_intent for a few tests, then run this again.")
else:
    print(f"Intent accuracy: {len(correct)}/{len(tested)} = {100 * len(correct) / len(tested):.1f}%")

    by_cat = defaultdict(lambda: [0, 0])
    for r in tested:
        by_cat[r["category"]][1] += 1
        if r["actual_intent"].strip() == r["expected_intent"].strip():
            by_cat[r["category"]][0] += 1

    print("\nBy category:")
    for cat, (ok, total) in by_cat.items():
        print(f"  {cat}: {ok}/{total}")

    print("\nFailures:")
    failures = [r for r in tested if r["actual_intent"].strip() != r["expected_intent"].strip()]
    if not failures:
        print("  None")
    for r in failures:
        print(f"  {r['test_id']}: expected {r['expected_intent']}, got {r['actual_intent']}")