from __future__ import annotations

from html import escape

from .models import PeriodReport


_BACKGROUND = "#0b1220"
_PANEL = "#111c2e"
_GRID = "#26354b"
_TEXT = "#e8eef7"
_MUTED = "#91a0b5"
_LOSS = "#fb7185"
_GAIN = "#34d399"
_PALETTE = ("#60a5fa", "#fbbf24", "#c084fc", "#2dd4bf", "#fb923c", "#a3e635")


def _money(value: float, currency: str) -> str:
    return f"{'-' if value < 0 else ''}{currency} {abs(value):,.0f}"


def _label(value: str) -> str:
    return escape(value, quote=True)


def render_component_chart(report: PeriodReport) -> str:
    components = sorted(report.component_pnl.items(), key=lambda item: item[1])
    if not components:
        raise ValueError("period report must contain attribution components")

    width = 1120
    row_height = 64
    top = 260
    height = top + row_height * len(components) + 112
    center = 650
    half_width = 280
    extent = max(max(abs(value) for _, value in components), 1.0)
    scale = half_width / extent
    content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="chart-title chart-description">',
        '<title id="chart-title">Period P&amp;L attribution</title>',
        (
            '<desc id="chart-description">P&amp;L attribution from '
            f"{_label(report.start_date)} to {_label(report.end_date)} totals "
            f"{_label(_money(report.total_pnl, report.currency))}.</desc>"
        ),
        f'<rect width="{width}" height="{height}" rx="24" fill="{_BACKGROUND}"/>',
        f'<text x="56" y="64" fill="{_TEXT}" font-family="Inter,Arial,sans-serif" '
        'font-size="15" font-weight="700" letter-spacing="2">PORTFOLIO PERFORMANCE</text>',
        f'<text x="56" y="112" fill="{_TEXT}" font-family="Inter,Arial,sans-serif" '
        'font-size="34" font-weight="700">Where did P&amp;L come from?</text>',
        f'<text x="56" y="147" fill="{_MUTED}" font-family="Inter,Arial,sans-serif" '
        f'font-size="15">Attribution bridge • {_label(report.start_date)} to '
        f"{_label(report.end_date)} • {_label(report.currency)}</text>",
        f'<rect x="56" y="178" width="1008" height="58" rx="12" '
        f'fill="{_PANEL}" stroke="{_GRID}"/>',
        f'<text x="78" y="214" fill="{_MUTED}" font-family="Inter,Arial,sans-serif" '
        'font-size="13" font-weight="700" letter-spacing="1">TOTAL PORTFOLIO P&amp;L</text>',
        f'<text x="1038" y="216" text-anchor="end" fill="{_LOSS if report.total_pnl < 0 else _GAIN}" '
        'font-family="Inter,Arial,sans-serif" font-size="22" font-weight="700">'
        f"{_label(_money(report.total_pnl, report.currency))}</text>",
        f'<text x="{center}" y="{top - 24}" fill="{_MUTED}" '
        'font-family="Inter,Arial,sans-serif" font-size="12" text-anchor="middle">'
        "← LOSS      GAIN →</text>",
        f'<line x1="{center}" y1="{top - 10}" x2="{center}" '
        f'y2="{top + row_height * len(components) - 14}" stroke="{_GRID}" '
        'stroke-width="2" stroke-dasharray="4 6"/>',
    ]

    for index, (component, value) in enumerate(components):
        y = top + index * row_height
        color = _PALETTE[index % len(_PALETTE)]
        bar_width = abs(value) * scale
        x = center - bar_width if value < 0 else center
        content.extend(
            [
                f'<rect x="44" y="{y - 15}" width="{width - 88}" height="52" '
                f'rx="10" fill="{_PANEL if index % 2 == 0 else _BACKGROUND}"/>',
                f'<text x="64" y="{y + 8}" fill="{_TEXT}" '
                'font-family="Inter,Arial,sans-serif" font-size="14" '
                f'font-weight="700">{_label(component)}</text>',
                f'<rect x="{x:.2f}" y="{y - 7}" width="{bar_width:.2f}" '
                f'height="24" rx="4" fill="{color}">'
                f'<title>{_label(component)}: {_label(_money(value, report.currency))}</title>'
                "</rect>",
                f'<text x="1048" y="{y + 8}" text-anchor="end" '
                f'fill="{_LOSS if value < 0 else _GAIN}" '
                'font-family="Inter,Arial,sans-serif" font-size="13" '
                f'font-weight="700">{_label(_money(value, report.currency))}</text>',
            ]
        )

    footer_y = top + row_height * len(components) + 42
    content.extend(
        [
            f'<line x1="56" y1="{footer_y - 18}" x2="{width - 56}" '
            f'y2="{footer_y - 18}" stroke="{_GRID}"/>',
            f'<text x="56" y="{footer_y + 6}" fill="{_MUTED}" '
            'font-family="Inter,Arial,sans-serif" font-size="12">'
            "Currency contribution by component • Synthetic example data • "
            "Not investment advice</text>",
            "</svg>",
        ]
    )
    return "\n".join(content)


def render_cumulative_chart(report: PeriodReport) -> str:
    points = report.observations
    if not points:
        raise ValueError("period report must contain daily observations")

    width = 1120
    height = 560
    left, right, top, bottom = 100, 1050, 205, 430
    values = [point.cumulative_pnl for point in points]
    low = min(0.0, min(values))
    high = max(0.0, max(values))
    spread = max(high - low, 1.0)
    padding = spread * 0.12
    low -= padding
    high += padding
    x_step = (right - left) / max(len(points) - 1, 1)
    y_scale = (bottom - top) / (high - low)
    coordinates = [
        (left + index * x_step, bottom - (value - low) * y_scale)
        for index, value in enumerate(values)
    ]
    zero_y = bottom - (0.0 - low) * y_scale
    line_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
    area_points = (
        f"{coordinates[0][0]:.2f},{zero_y:.2f} "
        f"{line_points} {coordinates[-1][0]:.2f},{zero_y:.2f}"
    )
    currency = report.currency
    content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="chart-title chart-description">',
        '<title id="chart-title">Cumulative portfolio P&amp;L</title>',
        (
            '<desc id="chart-description">Cumulative P&amp;L from '
            f"{_label(report.start_date)} to {_label(report.end_date)} ends at "
            f"{_label(_money(report.total_pnl, currency))}.</desc>"
        ),
        f'<rect width="{width}" height="{height}" rx="24" fill="{_BACKGROUND}"/>',
        f'<text x="56" y="64" fill="{_TEXT}" font-family="Inter,Arial,sans-serif" '
        'font-size="15" font-weight="700" letter-spacing="2">PORTFOLIO PERFORMANCE</text>',
        f'<text x="56" y="112" fill="{_TEXT}" font-family="Inter,Arial,sans-serif" '
        'font-size="34" font-weight="700">P&amp;L through the period</text>',
        f'<text x="56" y="147" fill="{_MUTED}" font-family="Inter,Arial,sans-serif" '
        'font-size="15">Cumulative daily P&amp;L, excluding external flows • '
        f"{_label(report.currency)}</text>",
    ]

    grid_values = [low + (high - low) * index / 4 for index in range(5)]
    for value in grid_values:
        y = bottom - (value - low) * y_scale
        color = _GAIN if abs(value) < spread * 1e-9 else _MUTED
        content.extend(
            [
                f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" '
                f'stroke="{_GRID}" stroke-width="1"/>',
                f'<text x="{left - 14}" y="{y + 4:.2f}" text-anchor="end" '
                f'fill="{color}" font-family="Inter,Arial,sans-serif" font-size="11">'
                f"{_label(_money(value, currency))}</text>",
            ]
        )
    content.extend(
        [
            f'<polygon points="{area_points}" fill="#60a5fa" opacity="0.13"/>',
            f'<polyline points="{line_points}" fill="none" stroke="#60a5fa" '
            'stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>',
        ]
    )
    for index, (point, (x, y)) in enumerate(zip(points, coordinates)):
        content.extend(
            [
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#60a5fa" '
                f'stroke="{_BACKGROUND}" stroke-width="3"><title>{_label(point.date)}: '
                f'{_label(_money(point.cumulative_pnl, currency))}</title></circle>',
            ]
        )
        if index in (0, len(points) - 1) or len(points) <= 8:
            content.append(
                f'<text x="{x:.2f}" y="{bottom + 28}" text-anchor="middle" '
                f'fill="{_MUTED}" font-family="Inter,Arial,sans-serif" font-size="11">'
                f"{_label(point.date[5:])}</text>"
            )

    last_x, last_y = coordinates[-1]
    label_y = min(max(last_y - 20, top + 18), bottom - 18)
    content.extend(
        [
            f'<rect x="{right - 190}" y="174" width="190" height="54" rx="12" '
            f'fill="{_PANEL}" stroke="{_GRID}"/>',
            f'<text x="{right - 174}" y="196" fill="{_MUTED}" '
            'font-family="Inter,Arial,sans-serif" font-size="10" '
            'font-weight="700" letter-spacing="1">PERIOD P&amp;L</text>',
            f'<text x="{right - 174}" y="216" fill="{_GAIN if report.total_pnl >= 0 else _LOSS}" '
            'font-family="Inter,Arial,sans-serif" font-size="15" font-weight="700">'
            f"{_label(_money(report.total_pnl, currency))}</text>",
            f'<text x="56" y="{height - 54}" fill="{_MUTED}" '
            'font-family="Inter,Arial,sans-serif" font-size="12">'
            "NAV change less external flows • Synthetic example data • "
            "Not investment advice</text>",
            "</svg>",
        ]
    )
    return "\n".join(content)


def render_project_screenshot(report: PeriodReport) -> str:
    """Render a white project overview card with the period component chart."""
    components = sorted(report.component_pnl.items(), key=lambda item: item[1])
    if not components:
        raise ValueError("period report must contain attribution components")

    width = 1200
    height = 820
    center = 770
    chart_half_width = 230
    chart_top = 430
    row_height = 44
    extent = max(max(abs(value) for _, value in components), 1.0)
    scale = chart_half_width / extent
    content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="chart-title chart-description">',
        '<title id="chart-title">P&amp;L Attribution Engine project overview</title>',
        (
            '<desc id="chart-description">White project overview with summary '
            f"metrics and a component attribution chart. Period P&amp;L: "
            f"{_label(_money(report.total_pnl, report.currency))}.</desc>"
        ),
        '<rect width="1200" height="820" fill="#ffffff"/>',
        '<rect x="34" y="30" width="1132" height="760" rx="24" fill="#ffffff" stroke="#e5eaf1" stroke-width="2"/>',
        '<rect x="66" y="64" width="48" height="48" rx="14" fill="#eaf2ff"/>',
        '<path d="M80 97V83h7v14m5 0V74h7v23m5 0V88h7v9" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
        '<text x="130" y="84" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700" letter-spacing="1.5">QUANT ANALYSIS • PORTFOLIO TOOLING</text>',
        '<text x="130" y="111" fill="#0f172a" font-family="Inter,Arial,sans-serif" font-size="25" font-weight="700">P&amp;L Attribution Engine</text>',
        '<text x="66" y="168" fill="#0f172a" font-family="Inter,Arial,sans-serif" font-size="31" font-weight="700">A clear bridge from NAV movement to its drivers.</text>',
        '<text x="66" y="199" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="16">Daily portfolio P&amp;L, cash flows, component attribution, and transparent residual reconciliation.</text>',
    ]

    metrics = [
        ("PERIOD P&amp;L", _money(report.total_pnl, report.currency), "#15803d"),
        ("EXTERNAL FLOWS", _money(report.external_flows, report.currency), "#1d4ed8"),
        ("RECONCILIATION GAP", _money(report.reconciliation_residual, report.currency), "#b45309"),
    ]
    for index, (heading, value, color) in enumerate(metrics):
        x = 66 + index * 356
        content.extend(
            [
                f'<rect x="{x}" y="230" width="332" height="94" rx="16" fill="#f8fafc" stroke="#e2e8f0"/>',
                f'<text x="{x + 20}" y="260" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="700" letter-spacing="1.1">{heading}</text>',
                f'<text x="{x + 20}" y="298" fill="{color}" font-family="Inter,Arial,sans-serif" font-size="24" font-weight="700">{_label(value)}</text>',
            ]
        )

    content.extend(
        [
            '<text x="66" y="372" fill="#0f172a" font-family="Inter,Arial,sans-serif" font-size="20" font-weight="700">Period attribution by component</text>',
            f'<text x="66" y="397" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="13">{_label(report.start_date)} to {_label(report.end_date)} • Currency P&amp;L</text>',
            f'<text x="{center}" y="416" text-anchor="middle" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="12">← LOSS      GAIN →</text>',
            f'<line x1="{center}" y1="{chart_top - 8}" x2="{center}" y2="{chart_top + row_height * len(components) - 8}" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="4 5"/>',
        ]
    )

    for index, (component, value) in enumerate(components):
        y = chart_top + index * row_height
        bar_width = abs(value) * scale
        x = center - bar_width if value < 0 else center
        bar_color = "#dc2626" if value < 0 else "#16a34a"
        content.extend(
            [
                f'<text x="80" y="{y + 5}" fill="#334155" font-family="Inter,Arial,sans-serif" font-size="14" font-weight="600">{_label(component)}</text>',
                f'<rect x="{x:.2f}" y="{y - 8}" width="{bar_width:.2f}" height="18" rx="5" fill="{bar_color}"><title>{_label(component)}: {_label(_money(value, report.currency))}</title></rect>',
                f'<text x="1105" y="{y + 5}" text-anchor="end" fill="{bar_color}" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700">{_label(_money(value, report.currency))}</text>',
                f'<line x1="66" y1="{y + 20}" x2="1134" y2="{y + 20}" stroke="#f1f5f9"/>',
            ]
        )
    content.extend(
        [
            '<text x="66" y="766" fill="#94a3b8" font-family="Inter,Arial,sans-serif" font-size="12">Synthetic sample • Signed currency contributions • External flows excluded from P&amp;L</text>',
            "</svg>",
        ]
    )
    return "\n".join(content)


def render_flow_screenshot(report: PeriodReport) -> str:
    """Render a white workflow screenshot with the real cumulative P&L chart."""
    points = report.observations
    if not points:
        raise ValueError("period report must contain daily observations")

    width = 1200
    height = 820
    left, right, top, bottom = 155, 1080, 604, 722
    values = [point.cumulative_pnl for point in points]
    low = min(0.0, min(values))
    high = max(0.0, max(values))
    spread = max(high - low, 1.0)
    low -= spread * 0.12
    high += spread * 0.12
    x_step = (right - left) / max(len(points) - 1, 1)
    y_scale = (bottom - top) / (high - low)
    coordinates = [
        (left + index * x_step, bottom - (value - low) * y_scale)
        for index, value in enumerate(values)
    ]
    line_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
    zero_y = bottom - (0.0 - low) * y_scale
    area_points = (
        f"{coordinates[0][0]:.2f},{zero_y:.2f} "
        f"{line_points} {coordinates[-1][0]:.2f},{zero_y:.2f}"
    )

    steps = [
        ("01", "Daily inputs", ("Opening/closing NAV", "Cash flows", "Component amounts")),
        ("02", "Calculate P&amp;L", ("Closing NAV less", "opening NAV and", "external flows")),
        ("03", "Attribute", ("Sum signed component", "contributions")),
        ("04", "Reconcile", ("Show unexplained", "amount as residual")),
        ("05", "Report", ("Period totals, daily", "trail, JSON and charts")),
    ]
    content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="chart-title chart-description">',
        '<title id="chart-title">P&amp;L Attribution Engine workflow</title>',
        (
            '<desc id="chart-description">White workflow diagram from daily '
            'portfolio inputs through P&amp;L calculation, attribution and '
            'reconciliation, with the included cumulative P&amp;L chart.</desc>'
        ),
        '<rect width="1200" height="820" fill="#ffffff"/>',
        '<rect x="34" y="30" width="1132" height="760" rx="24" fill="#ffffff" stroke="#e5eaf1" stroke-width="2"/>',
        '<text x="66" y="86" fill="#2563eb" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700" letter-spacing="1.5">HOW IT WORKS</text>',
        '<text x="66" y="126" fill="#0f172a" font-family="Inter,Arial,sans-serif" font-size="31" font-weight="700">From portfolio ledger to explainable P&amp;L</text>',
        '<text x="66" y="157" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="15">Each step is explicit, validated, and traceable to the final report.</text>',
    ]
    box_y = 196
    box_width = 202
    gap = 22
    for index, (number, heading, detail_lines) in enumerate(steps):
        x = 66 + index * (box_width + gap)
        content.extend(
            [
                f'<rect x="{x}" y="{box_y}" width="{box_width}" height="150" rx="16" fill="#f8fafc" stroke="#dbe4ef"/>',
                f'<circle cx="{x + 28}" cy="{box_y + 31}" r="15" fill="#dbeafe"/>',
                f'<text x="{x + 28}" y="{box_y + 36}" text-anchor="middle" fill="#1d4ed8" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="700">{number}</text>',
                f'<text x="{x + 18}" y="{box_y + 69}" fill="#0f172a" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="700">{heading}</text>',
                f'<text x="{x + 18}" y="{box_y + 96}" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="11">',
            ]
        )
        for line_index, line in enumerate(detail_lines):
            content.append(
                f'<tspan x="{x + 18}" dy="{0 if line_index == 0 else 15}">{_label(line)}</tspan>'
            )
        content.append("</text>")
        if index < len(steps) - 1:
            content.append(
                f'<path d="M{x + box_width + 5} {box_y + 75}h12m-5 -5 5 5-5 5" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    content.extend(
        [
            '<text x="66" y="397" fill="#0f172a" font-family="Inter,Arial,sans-serif" font-size="20" font-weight="700">Cumulative P&amp;L output</text>',
            f'<text x="66" y="421" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="13">{_label(report.start_date)} to {_label(report.end_date)} • {_label(report.currency)} • NAV change less external flows</text>',
            '<rect x="66" y="442" width="1068" height="306" rx="16" fill="#fbfdff" stroke="#e2e8f0"/>',
        ]
    )
    grid_values = [low + (high - low) * index / 3 for index in range(4)]
    for value in grid_values:
        y = bottom - (value - low) * y_scale
        content.extend(
            [
                f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#e2e8f0"/>',
                f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="10">{_label(_money(value, report.currency))}</text>',
            ]
        )
    content.extend(
        [
            f'<polygon points="{area_points}" fill="#3b82f6" opacity="0.10"/>',
            f'<polyline points="{line_points}" fill="none" stroke="#2563eb" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>',
        ]
    )
    for point, (x, y) in zip(points, coordinates):
        content.extend(
            [
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#2563eb" stroke="#ffffff" stroke-width="2"><title>{_label(point.date)}: {_label(_money(point.cumulative_pnl, report.currency))}</title></circle>',
                f'<text x="{x:.2f}" y="{bottom + 23}" text-anchor="middle" fill="#64748b" font-family="Inter,Arial,sans-serif" font-size="10">{_label(point.date[5:])}</text>',
            ]
        )
    content.extend(
        [
            f'<text x="66" y="775" fill="#94a3b8" font-family="Inter,Arial,sans-serif" font-size="12">Synthetic example • Residual remains visible rather than being silently assigned to another component</text>',
            "</svg>",
        ]
    )
    return "\n".join(content)
