SEVERITIES = ["Critical", "High", "Medium", "Low"]


def aggregate_severities(findings):
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        sev = f.get("severity", "Low").title()
        if sev not in counts:
            sev = "Low"  # noma'lum severity -> Low (jami bilan mos bo'lishi uchun)
        counts[sev] += 1
    return counts


def _trend(prev_total, total):
    if prev_total is None:
        return ""
    d = prev_total - total
    if d > 0:
        return f" ↓{d}"
    if d < 0:
        return f" ↑{-d}"
    return " ="


def render_text_report(findings, prev_total=None):
    counts = aggregate_severities(findings)
    total = len(findings)
    lines = [
        "TIZIM — kunlik xavfsizlik hisoboti",
        "=" * 32,
        f"Jami zaiflik: {total}{_trend(prev_total, total)}",
        "-" * 32,
    ]
    for s in SEVERITIES:
        lines.append(f"{s:<10} {counts[s]}")
    lines.append("-" * 32)
    top = sorted(
        findings,
        key=lambda f: SEVERITIES.index(f.get("severity", "Low").title())
        if f.get("severity", "Low").title() in SEVERITIES
        else 99,
    )[:10]
    for f in top:
        lines.append(
            f"{f['severity'][:4].upper():<5} {f['cve']:<16} {f['package']} @ {f['location']}"
        )
    lines.append("=" * 32)
    return "\n".join(lines)
