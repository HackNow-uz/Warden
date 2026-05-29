import os
import subprocess


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[0]} xato (rc={p.returncode}): {p.stderr[:400]}")
    return p.stdout


def run_trivy_image(ref):
    out = _run(["trivy", "image", "--quiet", "--format", "json", ref])
    return {"scan_type": "Trivy Scan", "target": ref, "raw": out}


def run_trivy_fs(path):
    out = _run(["trivy", "fs", "--quiet", "--scanners", "vuln", "--format", "json", path])
    return {"scan_type": "Trivy Scan", "target": path, "raw": out}


def run_grype(ref):
    out = _run(["grype", ref, "-o", "json"])
    return {"scan_type": "Anchore Grype", "target": ref, "raw": out}


def scan_all(settings):
    """Scan every image ref listed in IMAGES_FILE with both Trivy and Grype."""
    results = []
    images_file = os.environ.get("IMAGES_FILE", "/opt/tizim/scanning/images.txt")
    if os.path.exists(images_file):
        for line in open(images_file):
            ref = line.strip()
            if not ref or ref.startswith("#"):
                continue
            results.append(run_trivy_image(ref))
            results.append(run_grype(ref))
    return results
