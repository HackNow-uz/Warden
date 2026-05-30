import html as _html

SEVERITIES = ["Critical", "High", "Medium", "Low"]
SEV_COLOR = {"Critical": "#b91c1c", "High": "#ea580c", "Medium": "#ca8a04", "Low": "#2563eb"}


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
        "Warden — kunlik xavfsizlik hisoboti",
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


# ---------------- HTML hisobot ----------------

def _e(v):
    return _html.escape(str(v if v is not None else ""))


def _badge(sev, n):
    c = SEV_COLOR.get(sev, "#6b7280")
    return (f'<span style="display:inline-block;background:{c};color:#fff;'
            f'border-radius:6px;padding:4px 10px;margin:0 6px 6px 0;font:13px/1.2 Arial">'
            f'{_e(sev)}: <b>{n}</b></span>')


def _table(rows):
    """rows: list of finding dicts -> HTML table with every detail."""
    head = (
        '<tr style="background:#0f172a;color:#e2e8f0;font:12px Arial;text-align:left">'
        '<th style="padding:6px 8px">Severity</th><th style="padding:6px 8px">CVE</th>'
        '<th style="padding:6px 8px">Paket</th><th style="padding:6px 8px">O\'rnatilgan</th>'
        '<th style="padding:6px 8px">Tuzatilgan</th><th style="padding:6px 8px">Joylashuv</th>'
        '<th style="padding:6px 8px">Manba</th><th style="padding:6px 8px">Tavsif</th></tr>'
    )
    body = []
    for i, f in enumerate(rows):
        sev = f.get("severity", "Low").title()
        c = SEV_COLOR.get(sev, "#6b7280")
        bg = "#ffffff" if i % 2 == 0 else "#f1f5f9"
        body.append(
            f'<tr style="background:{bg};font:12px Arial;color:#0f172a">'
            f'<td style="padding:5px 8px;border-left:4px solid {c};white-space:nowrap"><b>{_e(sev)}</b></td>'
            f'<td style="padding:5px 8px;white-space:nowrap">{_e(f.get("cve"))}</td>'
            f'<td style="padding:5px 8px">{_e(f.get("package"))}</td>'
            f'<td style="padding:5px 8px">{_e(f.get("installed"))}</td>'
            f'<td style="padding:5px 8px;color:#15803d">{_e(f.get("fixed"))}</td>'
            f'<td style="padding:5px 8px">{_e(f.get("location"))}</td>'
            f'<td style="padding:5px 8px">{_e(f.get("source"))}</td>'
            f'<td style="padding:5px 8px;color:#475569">{_e(f.get("title"))}</td></tr>'
        )
    return ('<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
            f'width:100%;border:1px solid #cbd5e1">{head}{"".join(body)}</table>')


def _sorted(findings):
    return sorted(findings, key=lambda f: SEVERITIES.index(f.get("severity", "Low").title())
                  if f.get("severity", "Low").title() in SEVERITIES else 99)


def _summary_block(findings, generated_at, prev_total):
    counts = aggregate_severities(findings)
    total = len(findings)
    badges = "".join(_badge(s, counts[s]) for s in SEVERITIES)
    return (
        '<div style="font:14px Arial;color:#0f172a">'
        '<h2 style="margin:0 0 4px;color:#0f172a">Warden — Xavfsizlik Hisoboti</h2>'
        f'<div style="color:#64748b;font-size:13px">Yaratildi: {_e(generated_at)}</div>'
        f'<div style="margin:14px 0;font-size:20px">Jami zaiflik: <b>{total}</b>'
        f'<span style="color:#64748b;font-size:14px">{_e(_trend(prev_total, total))}</span></div>'
        f'<div>{badges}</div></div>'
    )


def render_html_summary(findings, generated_at, prev_total=None):
    """Email body: xulosa + barcha CRITICAL to'liq (Gmail clipping'dan qochish)."""
    counts = aggregate_severities(findings)
    crit = [f for f in _sorted(findings) if f.get("severity", "").title() == "Critical"]
    parts = [_summary_block(findings, generated_at, prev_total)]
    if crit:
        parts.append('<h3 style="font:bold 15px Arial;color:#b91c1c;margin:18px 0 6px">'
                     f'CRITICAL ({len(crit)}) — to\'liq</h3>')
        parts.append(_table(crit))
    parts.append(
        '<p style="font:13px Arial;color:#475569;margin-top:16px">'
        f'High: <b>{counts["High"]}</b> · Medium: <b>{counts["Medium"]}</b> · '
        f'Low: <b>{counts["Low"]}</b> — to\'liq ro\'yxat ilova faylida '
        f'(<b>{len(findings)}</b> ta topilma).</p>'
    )
    return f'<body style="margin:0;padding:18px;background:#f8fafc">{"".join(parts)}</body>'


def render_html_full(findings, generated_at):
    """Ilova fayli: barcha topilma severity bo'yicha, har bir detal."""
    counts = aggregate_severities(findings)
    parts = [_summary_block(findings, generated_at, None)]
    for sev in SEVERITIES:
        group = [f for f in findings if f.get("severity", "Low").title() == sev]
        if not group:
            continue
        c = SEV_COLOR[sev]
        parts.append(f'<h3 style="font:bold 16px Arial;color:{c};margin:22px 0 6px">'
                     f'{sev} — {len(group)} ta</h3>')
        parts.append(_table(group))
    return (
        '<!DOCTYPE html><html lang="uz"><head><meta charset="utf-8">'
        '<title>Warden hisobot</title></head>'
        f'<body style="margin:0;padding:20px;background:#f8fafc">{"".join(parts)}'
        f'<p style="font:11px Arial;color:#94a3b8;margin-top:24px">Warden · jami {len(findings)} '
        f'topilma · {_e(generated_at)}</p></body></html>'
    )
