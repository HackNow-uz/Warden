from app.report import (aggregate_severities, render_text_report,
                        render_html_summary, render_html_full)


F = [
    {"severity": "Critical", "cve": "CVE-1", "package": "openssl", "installed": "1.0",
     "fixed": "1.1", "location": "nginx:1.27", "source": "Trivy", "title": "buffer overflow"},
    {"severity": "High", "cve": "CVE-2", "package": "nginx", "installed": "a",
     "fixed": "", "location": "img", "source": "Grype", "title": ""},
]


def test_render_html_summary_has_critical_detail_and_attachment_note():
    h = render_html_summary(F, "2026-05-29 10:00 UTC")
    assert "CVE-1" in h and "openssl" in h and "1.1" in h  # critical to'liq
    assert "buffer overflow" in h
    assert "Jami zaiflik" in h
    assert "ilova faylida" in h
    assert "CVE-2" not in h  # high faqat sanoqda, body'da emas


def test_render_html_full_has_all_severities():
    h = render_html_full(F, "2026-05-29 10:00 UTC")
    assert "CVE-1" in h and "CVE-2" in h
    assert "Critical" in h and "High" in h
    assert "<!DOCTYPE html>" in h


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
