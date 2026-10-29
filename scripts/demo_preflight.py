"""Check local demo prerequisites without inference, downloads or server changes."""
import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", help="Base URL of an already-running local API")
    parser.add_argument("--dashboard-url", help="URL of an already-running dashboard")
    parser.add_argument("--output", type=Path, help="Optional JSON evidence file")
    args = parser.parse_args()
    checks = []

    def record(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)})
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}", flush=True)

    record("python", sys.version_info >= (3, 10), sys.version.split()[0])
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = metadata.version(requirement.name)
            record(requirement.name, requirement.specifier.contains(installed), installed)
        except metadata.PackageNotFoundError:
            record(requirement.name, False, "not installed in this Python environment")

    for command, flag in (("ffmpeg", "-version"), ("ffprobe", "-version"), ("node", "--version")):
        executable = shutil.which(command)
        if not executable:
            record(command, False, "not on PATH")
            continue
        try:
            result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=15)
            record(command, result.returncode == 0, (result.stdout or result.stderr).splitlines()[0])
        except (OSError, subprocess.TimeoutExpired, IndexError) as error:
            record(command, False, error)

    for relative in (
        "models/vosk/vosk-model-small-en-us-0.15/am/final.mdl",
        "models/yunet/face_detection_yunet_2023mar.onnx",
        "models/pose_landmarker/pose_landmarker_lite.task",
        "models/wespeaker/voxceleb_resnet34_LM.onnx",
        "dashboard/package-lock.json",
        "dashboard/node_modules/vite/package.json",
    ):
        path = ROOT / relative
        record(relative, path.is_file() and path.stat().st_size > 0, "present" if path.is_file() else "missing")
    try:
        bundled_vad = Path(metadata.distribution("silero-vad").locate_file("silero_vad/data/silero_vad.onnx"))
        record("bundled Silero ONNX", bundled_vad.is_file() and bundled_vad.stat().st_size > 0, "installed package data")
    except metadata.PackageNotFoundError:
        record("bundled Silero ONNX", False, "silero-vad not installed")

    for name, command in (
        ("pip consistency", [sys.executable, "-m", "pip", "check"]),
        ("CLI entry point", [sys.executable, str(ROOT / "cli.py"), "--help"]),
    ):
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
            detail = "passed" if result.returncode == 0 else (result.stdout + result.stderr).strip()
            record(name, result.returncode == 0, detail)
        except (OSError, subprocess.TimeoutExpired) as error:
            record(name, False, error)

    for name, url in (("API health", args.api_url), ("dashboard HTTP", args.dashboard_url)):
        if not url:
            continue
        target = url.rstrip("/") + "/health" if name == "API health" else url
        try:
            with urlopen(target, timeout=5) as response:
                body = response.read()
                passed = response.status == 200
                if name == "API health":
                    health = json.loads(body)
                    passed = passed and health.get("status") == "ok" and health.get("service") == "Interview Analytics API"
                else:
                    passed = passed and b"<html" in body.lower()
                record(name, passed, f"HTTP {response.status}")
        except (URLError, OSError, ValueError, AttributeError) as error:
            record(name, False, error)

    passed = all(check["passed"] for check in checks)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "checked_utc": datetime.now(timezone.utc).isoformat(),
            "result": "passed" if passed else "failed", "checks": checks,
            "scope": "Prerequisites only; does not prove model integrity, inference or network isolation.",
        }, indent=2), encoding="utf-8")
    print("PASS: demo preflight" if passed else "FAIL: resolve the prerequisites listed above")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
