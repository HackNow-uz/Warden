import os
import sys
import json
import shutil
import tempfile
import subprocess

import yaml


def _run(cmd, timeout=900):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
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


def scan_images(settings):
    """Scan every image ref listed in IMAGES_FILE with both Trivy and Grype."""
    results = []
    images_file = os.environ.get("IMAGES_FILE", "/opt/tizim/scanning/images.txt")
    if os.path.exists(images_file):
        with open(images_file) as f:
            for line in f:
                ref = line.strip()
                if not ref or ref.startswith("#"):
                    continue
                results.append(run_trivy_image(ref))
                results.append(run_grype(ref))
    return results


def scan_repos(settings):
    """Clone each repo in REPOS_FILE and scan its dependencies with Trivy (dim 3)."""
    results = []
    repos_file = os.environ.get("REPOS_FILE", "/opt/tizim/scanning/repos.yml")
    if not os.path.exists(repos_file):
        return results
    with open(repos_file) as f:
        cfg = yaml.safe_load(f) or {}
    for repo in cfg.get("repos", []) or []:
        url = repo.get("url")
        name = repo.get("name", url)
        if not url:
            continue
        tmp = tempfile.mkdtemp(prefix="tizim-repo-")
        try:
            _run(["git", "clone", "--depth", "1", url, tmp], timeout=300)
            res = run_trivy_fs(tmp)
            res["target"] = name
            results.append(res)
        except Exception as e:  # noqa: BLE001 — skip-but-report (no silent failure)
            print(f"OGOHLANTIRISH: repo skani o'tkazib yuborildi {name}: {e}", file=sys.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return results


def scan_all(settings):
    """All scan dimensions: Docker images (2) + code dependencies (3)."""
    return scan_images(settings) + scan_repos(settings)


def parse_findings(scan_results):
    """Normalize Trivy/Grype JSON into common finding dicts for the report."""
    out = []
    for res in scan_results:
        target = res.get("target", "")
        try:
            data = json.loads(res.get("raw", ""))
        except (ValueError, TypeError):
            continue
        if res.get("scan_type") == "Trivy Scan":
            for r in data.get("Results", []) or []:
                for v in r.get("Vulnerabilities", []) or []:
                    out.append({
                        "cve": v.get("VulnerabilityID", ""),
                        "severity": v.get("Severity", "Low").title(),
                        "package": v.get("PkgName", ""),
                        "installed": v.get("InstalledVersion", ""),
                        "fixed": v.get("FixedVersion", ""),
                        "title": v.get("Title", "") or (v.get("Description") or "")[:140],
                        "location": target,
                        "source": "Trivy",
                    })
        elif res.get("scan_type") == "Anchore Grype":
            for m in data.get("matches", []) or []:
                vuln = m.get("vulnerability", {})
                art = m.get("artifact", {})
                fix = vuln.get("fix", {}) or {}
                out.append({
                    "cve": vuln.get("id", ""),
                    "severity": vuln.get("severity", "Low").title(),
                    "package": art.get("name", ""),
                    "installed": art.get("version", ""),
                    "fixed": ", ".join(fix.get("versions", []) or []),
                    "title": (vuln.get("description") or "")[:140],
                    "location": target,
                    "source": "Grype",
                })
    return out
