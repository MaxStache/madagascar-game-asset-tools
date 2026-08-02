from pathlib import Path

DIR1 = Path("test")
DIR2 = Path("Levels/beach")


def build_file_map(root: Path) -> dict[str, Path]:
    return {p.name: p for p in root.rglob("*") if p.is_file()}


files1 = build_file_map(DIR1)
files2 = build_file_map(DIR2)

only_in_test = sorted(files2.keys() - files1.keys())

print(f"Files only in {DIR2}: {len(only_in_test)}")

for name in only_in_test:
    print(files2[name])