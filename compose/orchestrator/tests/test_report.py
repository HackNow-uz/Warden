from app.report import aggregate_severities, render_text_report


def test_aggregate_counts_by_severity():
    findings = [
        {"severity": "Critical", "cve": "CVE-1", "package": "openssl", "location": "web-01"},
        {"severity": "High", "cve": "CVE-2", "package": "nginx", "location": "img:a"},
        {"severity": "High", "cve": "CVE-3", "package": "curl", "location": "web-01"},
        {"severity": "Medium", "cve": "CVE-4", "package": "zlib", "location": "img:b"},
    ]
    counts = aggregate_severities(findings)
    assert counts == {"Critical": 1, "High": 2, "Medium": 1, "Low": 0}


def test_render_text_report_contains_totals_and_top():
    findings = [{"severity": "Critical", "cve": "CVE-1", "package": "openssl", "location": "web-01"}]
    text = render_text_report(findings, prev_total=5)
    assert "Jami zaiflik: 1" in text
    assert "CVE-1" in text
    assert "openssl" in text
    assert "↓4" in text  # 5 -> 1 trend
