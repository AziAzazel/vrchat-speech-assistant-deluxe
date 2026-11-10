"""Preserve pytest's exit status and surface test failures in the job summary."""
import os
from pathlib import Path
import subprocess
import sys

result = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        encoding="utf-8", errors="replace")
print(result.stdout)
summary = os.getenv("GITHUB_STEP_SUMMARY")
if summary:
    with Path(summary).open("a", encoding="utf-8") as output:
        output.write("## Python tests\n\n```text\n" + result.stdout[-25000:] + "\n```\n")
raise SystemExit(result.returncode)
