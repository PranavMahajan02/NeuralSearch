import subprocess
import sys

file_path = "data/Week-01_Report_IEEE.pdf"

subprocess.run(
    [
        sys.executable,
        "index_single.py",
        file_path
    ]
)