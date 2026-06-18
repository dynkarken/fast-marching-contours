#!/usr/bin/env python3
"""
husportræt.py
Genererer en skaleret SVG-plakat (A2) fra OpenStreetMap-data.
Valgt bygning vises i rødt, omgivende bygninger i sort.

Afhængigheder: Python 3.9+ og kun 'requests' (pip install requests).

Brug:
  python husportræt.py --address "Rådhuspladsen 1, København" --scale 1000
  python husportræt.py --lat 55.6761 --lon 12.5683 --scale 5000 --output mit_hus.svg
"""

from __future__ import annotations

import math
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import requests


# ── Papirformat A2 ─────────────────────────────────────────────────────────────
PAPER_W = 420.0   # mm
PAPER_H = 594.0   # mm

# ── Jordens radius ─────────────────────────────────────────────────────────────
R_EARTH = 6_371_000.0  # meter


# ── Kartografisk stil ──────────────────────────────────────────────────────────
BACKGROUND = "#f7f4ef"

BUILDING_STYLE = "fill:#000000;stroke:none"
BUILDING_SELECTED_STYLE = "fill:#c0392b;stroke:none"

PATH_TYPES = {"footway", "path", "cycleway", "steps", "track", "pedestrian"}

ROAD_CASING = "#2c2c2c"
ROAD_FILL = BACKGROUND

ROAD_WIDTHS: dict[str, float] = {
    "motorway":      12.0,
    "trunk":         10.0,
    "primary":        8.0,
    "secondary":      7.0,
    "tertiary":       6.0,
    "residential":    5.5,
    "living_street":  4.0,
    "service":        3.0,
    "unclassified":   5.0,
    "_waterway":      3.0,
}
ROAD_DEFAULT_WIDTH = 5.0

WATER_STYLE = "fill:#b8d8ea;stroke:#85b4cc;stroke-width:0.1"


# ── Projektion ─────────────────────────────────────────────────────────────────
def latlon_to_local(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """
    Lokal ekvirektangulær projektion centreret på (lat0, lon0).
    Returnerer (x, y) i meter. Præcis til < ~10 km fra centrum.
    """
    mid_lat = math.radians((lat + lat0) / 2.0)
    x = math.radians(lon - lon0) * math.cos(mid_lat) * R_EARTH
    y = math.radians(lat - lat0) * R_EARTH
    return x, y


def m_to_svg(x: float, y: float, scale: int) -> tuple[float, float]:
    """
    Meter (lokal projektion, origo = valgt adresse) → SVG-mm.
    1 SVG-enhed = 1 mm. Origo placeres i papirets centrum.
    """
    mm_per_m = 1000.0 / scale
    sx = PAPER_W / 2.0 + x * mm_per_m
    sy = PAPER_H / 2.0 - y * mm_per_m   # vend y-akse
    return sx, sy


# ── Geometrihjælpere ───────────────────────────────────────────────────────────
def point_in_polygon(px: float, py: float, coords: list[tuple[float, float]]) -> bool:
    """Ray-casting algoritme."""
    n = len(coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = coords[i]
        xj, yj = coords[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def centroid(coords: list[tuple[float, float]]) -> tuple[float, float]:
    cx = sum(x for x, _ in coords) / len(coords)
    cy = sum(y for _, y in coords) / len(coords)
    return cx, cy


def dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def offset_polyline(coords: list[tuple[float, float]], d: float) -> list[tuple[float, float]]:
    """Offset a polyline by d meters (positive = left side). Returns offset points."""
    pts: list[tuple[float, float]] = []
    n = len(coords)
    if n < 2:
        return pts
    normals = []
    for i in range(n - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            normals.append((0.0, 0.0))
        else:
            normals.append((-dy / length, dx / length))

    for i in range(n):
        if i == 0:
            nx, ny = normals[0]
        elif i == n - 1:
            nx, ny = normals[-1]
        else:
            nx = normals[i - 1][0] + normals[i][0]
            ny = normals[i - 1][1] + normals[i][1]
            length = math.hypot(nx, ny)
            if length < 1e-9:
                nx, ny = normals[i][0], normals[i][1]
            else:
                nx /= length
                ny /= length
        pts.append((coords[i][0] + nx * d, coords[i][1] + ny * d))
    return pts


# ── Geocoding + matrikel via DAWA ─────────────────────────────────────────────
def geocode(address: str) -> tuple[float, float]:
    r = requests.get(
        "https://dawa.aws.dk/adresser",
        params={"q": address, "format": "json", "struktur": "mini"},
        timeout=15,
    )
    r.raise_for_status()
    results = r.json()
    if not results:
        raise ValueError(f"Adresse ikke fundet: {address!r}")
    a = results[0]
    lat, lon = a["y"], a["x"]
    print(f"  Fundet:      {a['betegnelse']}")
    print(f"  Koordinater: {lat:.6f}, {lon:.6f}")
    return lat, lon


def fetch_matrikel(address: str, lat0: float, lon0: float) -> list[tuple[float, float]] | None:
    r = requests.get(
        "https://dawa.aws.dk/adresser",
        params={"q": address, "format": "json", "struktur": "nestet"},
        timeout=15,
    )
    r.raise_for_status()
    results = r.json()
    if not results:
        return None

    js = results[0].get("adgangsadresse", {}).get("jordstykke")
    if not js:
        return None

    ejerlav = js["ejerlav"]["kode"]
    matrnr = js["matrikelnr"]
    print(f"  Matrikel:    {matrnr}, {js['ejerlav']['navn']}")

    r2 = requests.get(
        f"https://dawa.aws.dk/jordstykker/{ejerlav}/{matrnr}",
        params={"format": "geojson"},
        timeout=15,
    )
    r2.raise_for_status()
    geo = r2.json()
    if geo.get("geometry", {}).get("type") != "Polygon":
        return None

    ring = geo["geometry"]["coordinates"][0]
    return [latlon_to_local(pt[1], pt[0], lat0, lon0) for pt in ring]


# ── Overpass datahentning ──────────────────────────────────────────────────────
def fetch_osm(lat: float, lon: float, radius_m: float) -> dict:
    query = f"""
[out:json][timeout:90];
(
  way["building"](around:{radius_m:.0f},{lat},{lon});
  node["natural"="tree"](around:{radius_m:.0f},{lat},{lon});
  way["highway"](around:{radius_m:.0f},{lat},{lon});
  way["natural"="water"](around:{radius_m:.0f},{lat},{lon});
  way["waterway"~"^(river|stream|canal|drain)$"](around:{radius_m:.0f},{lat},{lon});
  relation["natural"="water"](around:{radius_m:.0f},{lat},{lon});
);
out body;
>;
out skel qt;
""".strip()

    OVERPASS_URLS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    print(f"  Henter OSM-data inden for {radius_m:.0f} m …")
    for url in OVERPASS_URLS:
        try:
            r = requests.get(
                url,
                params={"data": query},
                headers={"User-Agent": "husportraet-generator/1.0"},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            print(f"  Modtaget {len(data['elements'])} elementer")
            return data
        except (requests.RequestException, ValueError):
            print(f"  ⚠ {url} fejlede, prøver næste …")
            continue
    raise RuntimeError("Alle Overpass-servere fejlede")


# ── OSM-parsing ────────────────────────────────────────────────────────────────
def parse_osm(
    data: dict, lat0: float, lon0: float
) -> tuple[list, list, list, list]:
    """
    Returnerer (buildings, roads, waters, trees) alle i lokal (x, y) meter.
    """
    # Byg node-opslag: osm_id → (x_m, y_m)
    node_xy: dict[int, tuple[float, float]] = {}
    for el in data["elements"]:
        if el["type"] == "node":
            node_xy[el["id"]] = latlon_to_local(el["lat"], el["lon"], lat0, lon0)

    buildings: list[dict] = []
    roads:     list[dict] = []
    waters:    list[list] = []
    trees:     list[tuple[float, float]] = []

    for el in data["elements"]:
        tags = el.get("tags", {})

        if el["type"] == "node" and tags.get("natural") == "tree":
            if el["id"] in node_xy:
                trees.append(node_xy[el["id"]])

        elif el["type"] == "way":
            coords = [node_xy[nid] for nid in el.get("nodes", []) if nid in node_xy]
            if not coords:
                continue

            if "building" in tags:
                addr = None
                street = tags.get("addr:street")
                number = tags.get("addr:housenumber")
                if street and number:
                    addr = f"{street} {number}"
                buildings.append({"id": el["id"], "coords": coords, "addr": addr})
            elif "highway" in tags and tags["highway"] not in PATH_TYPES:
                if tags.get("service") == "driveway":
                    continue
                roads.append({"type": tags["highway"], "coords": coords})
            elif tags.get("natural") == "water" and len(coords) >= 3:
                waters.append(coords)
            elif "waterway" in tags and len(coords) >= 2:
                roads.append({"type": "_waterway", "coords": coords})

    return buildings, roads, waters, trees


# ── Find valgte bygninger (inden for matrikel) ────────────────────────────────
def find_selected(buildings: list[dict], matrikel: list[tuple[float, float]] | None = None) -> set[int]:
    selected = set()

    if matrikel and len(matrikel) >= 3:
        for b in buildings:
            if len(b["coords"]) >= 3:
                cx, cy = centroid(b["coords"])
                if point_in_polygon(cx, cy, matrikel):
                    selected.add(b["id"])
        if selected:
            return selected

    # Fallback: nærmeste bygning til (0,0)
    best_id, best_d = None, float("inf")
    for b in buildings:
        if len(b["coords"]) >= 3:
            cx, cy = centroid(b["coords"])
            d = dist(cx, cy, 0.0, 0.0)
            if d < best_d:
                best_d, best_id = d, b["id"]
    if best_id is not None:
        selected.add(best_id)
    return selected


# ── SVG-generering (xml.etree.ElementTree) ────────────────────────────────────
def coords_to_svg_pts(coords: list[tuple], scale: int) -> str:
    return " ".join(
        f"{m_to_svg(x, y, scale)[0]:.3f},{m_to_svg(x, y, scale)[1]:.3f}"
        for x, y in coords
    )


def tree_radius(scale: int) -> float:
    return 1.4 if scale <= 1000 else 0.55


def generate_svg(
    buildings: list[dict],
    roads: list[dict],
    waters: list[list],
    trees: list[tuple],
    selected_ids: set[int],
    scale: int,
    matrikel: list[tuple[float, float]] | None = None,
    output: Path | None = None,
):
    NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", NS)

    root = ET.Element(f"{{{NS}}}svg", {
        "width":   f"{PAPER_W}mm",
        "height":  f"{PAPER_H}mm",
        "viewBox": f"0 0 {PAPER_W} {PAPER_H}",
    })

    # ── <defs> ────────────────────────────────────────────────────────────────
    defs = ET.SubElement(root, f"{{{NS}}}defs")

    # Klip til papirkant
    clip = ET.SubElement(defs, f"{{{NS}}}clipPath", {"id": "paper"})
    ET.SubElement(clip, f"{{{NS}}}rect", {
        "x": "0", "y": "0",
        "width": str(PAPER_W), "height": str(PAPER_H),
    })

    # Trækrone-symbol centreret i (0,0)
    r = tree_radius(scale)
    arm = f"{r * 0.4:.3f}"
    sym = ET.SubElement(defs, f"{{{NS}}}symbol", {
        "id": "tree",
        "overflow": "visible",
    })
    ET.SubElement(sym, f"{{{NS}}}circle", {
        "cx": "0", "cy": "0", "r": f"{r:.3f}",
        "style": "fill:#4d7c3f;stroke:#2d5a1b;stroke-width:0.08",
    })
    ET.SubElement(sym, f"{{{NS}}}line", {
        "x1": f"-{arm}", "y1": "0", "x2": arm, "y2": "0",
        "style": "stroke:#2d5a1b;stroke-width:0.06",
    })
    ET.SubElement(sym, f"{{{NS}}}line", {
        "x1": "0", "y1": f"-{arm}", "x2": "0", "y2": arm,
        "style": "stroke:#2d5a1b;stroke-width:0.06",
    })

    # ── Indholdsgruppe ────────────────────────────────────────────────────────
    g = ET.SubElement(root, f"{{{NS}}}g", {"clip-path": "url(#paper)"})

    # Baggrund
    ET.SubElement(g, f"{{{NS}}}rect", {
        "x": "0", "y": "0",
        "width": str(PAPER_W), "height": str(PAPER_H),
        "style": f"fill:{BACKGROUND}",
    })

    # Vand (polygoner)
    for coords in waters:
        if len(coords) >= 3:
            ET.SubElement(g, f"{{{NS}}}polygon", {
                "points": coords_to_svg_pts(coords, scale),
                "style": WATER_STYLE,
            })

    # Veje — samlet vejnet: bred sort casing → smal baggrundsfyld
    mm_per_m = 1000.0 / scale
    edge_w = 0.12

    # Pass 1: alle veje som brede sorte streger (vejflade + kant)
    for road in roads:
        coords_m = road["coords"]
        if len(coords_m) < 2 or road["type"] == "_waterway":
            continue
        w_mm = ROAD_WIDTHS.get(road["type"], ROAD_DEFAULT_WIDTH) * mm_per_m + edge_w * 2
        ET.SubElement(g, f"{{{NS}}}polyline", {
            "points": coords_to_svg_pts(coords_m, scale),
            "style": f"fill:none;stroke:{ROAD_CASING};stroke-width:{w_mm:.3f};stroke-linecap:round;stroke-linejoin:round",
        })

    # Pass 2: alle veje som smallere baggrundsstreger (vejflade)
    for road in roads:
        coords_m = road["coords"]
        if len(coords_m) < 2 or road["type"] == "_waterway":
            continue
        w_mm = ROAD_WIDTHS.get(road["type"], ROAD_DEFAULT_WIDTH) * mm_per_m
        ET.SubElement(g, f"{{{NS}}}polyline", {
            "points": coords_to_svg_pts(coords_m, scale),
            "style": f"fill:none;stroke:{BACKGROUND};stroke-width:{w_mm:.3f};stroke-linecap:round;stroke-linejoin:round",
        })

    # Vandløb
    for road in roads:
        coords_m = road["coords"]
        if len(coords_m) < 2 or road["type"] != "_waterway":
            continue
        w_mm = ROAD_WIDTHS.get(road["type"], ROAD_DEFAULT_WIDTH) * mm_per_m
        ET.SubElement(g, f"{{{NS}}}polyline", {
            "points": coords_to_svg_pts(coords_m, scale),
            "style": f"fill:none;stroke:#85b4cc;stroke-width:{w_mm:.3f};stroke-linecap:round;stroke-linejoin:round",
        })

    # Matrikelgrænse (under bygninger)
    if matrikel and len(matrikel) >= 3:
        ET.SubElement(g, f"{{{NS}}}polygon", {
            "points": coords_to_svg_pts(matrikel, scale),
            "style": "fill:none;stroke:#c0392b;stroke-width:0.2",
        })

    # Bygninger
    for b in buildings:
        if len(b["coords"]) < 3:
            continue
        style = BUILDING_SELECTED_STYLE if b["id"] in selected_ids else BUILDING_STYLE
        ET.SubElement(g, f"{{{NS}}}polygon", {
            "points": coords_to_svg_pts(b["coords"], scale),
            "style": style,
        })

    # Træer
    for (tx, ty) in trees:
        sx, sy = m_to_svg(tx, ty, scale)
        ET.SubElement(g, f"{{{NS}}}use", {
            "href": "#tree",
            "x": f"{sx:.3f}",
            "y": f"{sy:.3f}",
        })

    # Returnér som string eller skriv fil
    tree_xml = ET.ElementTree(root)
    ET.indent(tree_xml, space="  ")
    if output is None:
        import io
        buf = io.StringIO()
        buf.write('<?xml version="1.0" encoding="utf-8"?>\n')
        tree_xml.write(buf, encoding="unicode", xml_declaration=False)
        return buf.getvalue()
    with output.open("w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        tree_xml.write(f, encoding="unicode", xml_declaration=False)
    return None


def generate_from_address(address: str, scale: int = 1000) -> tuple[str, dict]:
    lat, lon = geocode(address)
    matrikel = fetch_matrikel(address, lat, lon)
    diag_m = math.hypot(PAPER_W, PAPER_H) / 2.0 / 1000.0 * scale
    radius_m = diag_m * 1.10
    raw = fetch_osm(lat, lon, radius_m)
    buildings, roads, waters, trees = parse_osm(raw, lat, lon)
    selected_ids = find_selected(buildings, matrikel)
    svg = generate_svg(buildings, roads, waters, trees, selected_ids, scale, matrikel, output=None)
    info = {
        "lat": lat, "lon": lon,
        "buildings": len(buildings), "roads": len(roads),
        "waters": len(waters), "trees": len(trees),
        "selected_ids": list(selected_ids),
    }
    return svg, info


# ── CLI ────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Husportræt — SVG-plakat fra OpenStreetMap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--address", metavar="ADRESSE",
                     help="Adresse (geocodes via Nominatim)")
    src.add_argument("--lat", type=float, metavar="LAT",
                     help="Breddegrad (WGS84)")
    parser.add_argument("--lon", type=float, metavar="LON",
                        help="Længdegrad — kræves med --lat")
    parser.add_argument("--scale", type=int, choices=[1000, 5000], default=1000,
                        help="Kortskala (standard: 1000)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output-sti (standard: husportræt_<skala>.svg)")
    args = parser.parse_args()

    print("\n── Husportræt Generator ──────────────────────────────────────────────")

    if args.address:
        print(f"\nGeocoder: {args.address!r}")
        lat, lon = geocode(args.address)
        matrikel = fetch_matrikel(args.address, lat, lon)
    else:
        if args.lon is None:
            parser.error("--lon kræves når --lat bruges")
        lat, lon = args.lat, args.lon
        matrikel = None
        print(f"\nKoordinater: {lat}, {lon}")

    # Radius dækker papirets diagonal + 10 % margin
    diag_m = math.hypot(PAPER_W, PAPER_H) / 2.0 / 1000.0 * args.scale
    radius_m = diag_m * 1.10
    print(f"\nSkala 1:{args.scale}  →  papir dækker {PAPER_W/1000*args.scale:.0f}×{PAPER_H/1000*args.scale:.0f} m")

    raw = fetch_osm(lat, lon, radius_m)

    buildings, roads, waters, trees = parse_osm(raw, lat, lon)
    print(
        f"  Bygninger: {len(buildings)}"
        f"  |  Veje: {len(roads)}"
        f"  |  Vand: {len(waters)}"
        f"  |  Træer: {len(trees)}"
    )

    selected_ids = find_selected(buildings, matrikel)
    if selected_ids:
        print(f"  Valgte bygninger ({len(selected_ids)}): {', '.join(f'#{i}' for i in selected_ids)}")
    else:
        print("  ⚠ Ingen bygning fundet ved koordinaterne")

    output = args.output or Path(f"husportræt_{args.scale}.svg")
    print(f"\nGenererer {output} …")
    generate_svg(buildings, roads, waters, trees, selected_ids, args.scale, matrikel, output)

    size_kb = output.stat().st_size // 1024
    print(f"✓ Færdig: {output}  ({size_kb} KB)\n")


if __name__ == "__main__":
    main()
