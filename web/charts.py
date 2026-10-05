"""
Generation de graphiques en SVG cote serveur.

Aucune bibliotheque JavaScript tierce (CDN) n'est chargee par l'interface :
les graphiques (courbes, anneaux) sont calcules en Python et rendus comme
SVG statique, ce qui evite toute dependance externe au moment du rendu et
simplifie l'audit de securite (pas de script tiers charge dans le
navigateur).
"""
from __future__ import annotations

PALETTE = ["#0a5c4c", "#2db4a3", "#8fd4c8", "#c7e8e2", "#e2f3f0"]


def line_chart(values, width=640, height=230, padding=32):
    """
    Construit les points d'une courbe simple a partir d'une liste de
    nombres. Retourne un dictionnaire pret a etre injecte dans un template
    (points de la polyline, points de la zone remplie, position des
    graduations).
    """
    values = [float(v) for v in values]
    if not values:
        return {"points": "", "area_points": "", "width": width, "height": height, "markers": [], "max_value": 0}

    max_value = max(values) or 1
    min_value = min(0, min(values))
    span = (max_value - min_value) or 1
    usable_w = width - 2 * padding
    usable_h = height - 2 * padding
    step = usable_w / (len(values) - 1) if len(values) > 1 else 0

    markers = []
    for i, v in enumerate(values):
        x = padding + i * step
        y = padding + usable_h - ((v - min_value) / span) * usable_h
        markers.append({"x": round(x, 1), "y": round(y, 1), "value": v})

    points = " ".join(f"{m['x']},{m['y']}" for m in markers)
    area_points = f"{padding},{height - padding} " + points + f" {width - padding},{height - padding}"

    return {
        "points": points,
        "area_points": area_points,
        "width": width,
        "height": height,
        "markers": markers,
        "max_value": max_value,
        "baseline_y": height - padding,
    }


def dual_line_chart(series_a, series_b, width=640, height=230, padding=32):
    """Deux courbes partageant la meme echelle (ex : revenus vs depenses)."""
    all_values = [float(v) for v in list(series_a) + list(series_b)] or [0]
    max_value = max(all_values) or 1

    def build(values):
        usable_w = width - 2 * padding
        usable_h = height - 2 * padding
        step = usable_w / (len(values) - 1) if len(values) > 1 else 0
        markers = []
        for i, v in enumerate(values):
            x = padding + i * step
            y = padding + usable_h - (float(v) / max_value) * usable_h
            markers.append({"x": round(x, 1), "y": round(y, 1)})
        return " ".join(f"{m['x']},{m['y']}" for m in markers)

    return {
        "points_a": build(series_a),
        "points_b": build(series_b),
        "width": width,
        "height": height,
        "baseline_y": height - padding,
    }


def donut_chart(segments, radius=52, stroke=16):
    """
    segments : liste de dict {"label": str, "value": float, "color": str}
    Retourne les segments enrichis d'un dasharray/dashoffset pret a l'emploi
    pour des <circle> superposes formant un anneau.
    """
    total = sum(s["value"] for s in segments) or 1
    circumference = 2 * 3.14159265 * radius
    cumulative = 0
    enriched = []
    for i, seg in enumerate(segments):
        pct = (seg["value"] / total) * 100
        dash = (pct / 100) * circumference
        enriched.append({
            "label": seg["label"],
            "value": seg["value"],
            "pct": round(pct, 1),
            "color": seg.get("color") or PALETTE[i % len(PALETTE)],
            "dasharray": f"{dash:.2f} {circumference - dash:.2f}",
            "dashoffset": f"{-cumulative:.2f}",
        })
        cumulative += dash
    return {"segments": enriched, "radius": radius, "stroke": stroke, "circumference": circumference}
