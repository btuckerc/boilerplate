from pathlib import Path
import subprocess
import sys

root = Path(__file__).parent
max_size = sys.maxsize * 2 + 1
independent = [0, 1, 1, 1, 2, 9, 0, (max_size + 7) // 8]
expected_lines = [int(line) for line in (root / "expected.txt").read_text().splitlines()]
if expected_lines != independent:
    print(f"FAIL: expected.txt is inconsistent with independent size_t oracle: {expected_lines!r}")
    sys.exit(1)
exe = root / ".row_bytes"
build = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "row_bytes.cpp", "-o", str(exe)], cwd=root, text=True, capture_output=True)
if build.returncode:
    print("FAIL compile:\n" + build.stderr)
    sys.exit(1)
run = subprocess.run([str(exe)], cwd=root, text=True, capture_output=True)
want = "".join(f"{value}\n" for value in independent)
if run.returncode or run.stdout != want:
    print(f"FAIL runtime: code={run.returncode}, stdout={run.stdout!r}, want={want!r}")
    sys.exit(1)
print("PASS C++ row-byte edge vectors")
