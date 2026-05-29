import io
import requests


def import_scan(dd_url, token, product_id, scan_type, target, raw_json):
    headers = {"Authorization": f"Token {token}"}
    data = {
        "scan_type": scan_type,
        "product_name": "TIZIM Infra",
        "engagement_name": f"daily-{target}",
        "auto_create_context": "true",
        "active": "true",
        "verified": "false",
        "close_old_findings": "true",  # dedup/trend across runs
    }
    files = {"file": (f"{target}.json", io.StringIO(raw_json), "application/json")}
    r = requests.post(f"{dd_url}/api/v2/import-scan/", headers=headers,
                      data=data, files=files, timeout=120)
    r.raise_for_status()
    return r.json().get("test")


def import_to_defectdojo(settings, results):
    n = 0
    for res in results:
        import_scan(settings.defectdojo_url, settings.dd_api_token,
                    settings.dd_product_id, res["scan_type"], res["target"], res["raw"])
        n += 1
    return n
