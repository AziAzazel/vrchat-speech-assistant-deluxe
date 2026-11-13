"""Preserve pytest's exit status and surface test failures in the job summary."""
import os
from pathlib import Path
import subprocess
import sys

result = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        encoding="utf-8", errors="replace")
print(result.stdout)
if result.returncode:
    # GitHub hides raw logs from signed-out readers. Keep the failure itself
    # visible in the public run annotations as well as the job summary.
    marker = result.stdout.find(' FAILURES ')
    details = result.stdout[marker:] if marker >= 0 else result.stdout
    details = details[-18000:].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Python test failures::' + details)
summary = os.getenv("GITHUB_STEP_SUMMARY")
if summary:
    with Path(summary).open("a", encoding="utf-8") as output:
        output.write("## Python tests\n\n```text\n" + result.stdout[-25000:] + "\n```\n")
raise SystemExit(result.returncode)
