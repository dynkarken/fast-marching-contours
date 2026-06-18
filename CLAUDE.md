# Husportræt

Plakat-produkt til plotter-virksomhed. Kunden indtaster en adresse og køber en SVG-plakat i arkitektonisk skala der viser deres hus i rødt og omgivende bygninger i sort.

## Koncept

- **Format**: A2 (420×594 mm), skala 1:1000 eller 1:5000
- **Valgt bygning**: rød fyld
- **Omgivende bygninger**: sort kontur, lysegrå fyld
- **Øvrige lag**: veje, vandflader, individuelle træer
- **Output**: SVG (vektorgrafik klar til plotter)
- **Målgruppe**: indflyttergave, arkitekt-æstetik

## Stack

- **Datakilde**: OpenStreetMap via Overpass API (globalt skalerbart)
- **Geocoding**: Nominatim
- **Projektion**: Lokal ekvirektangulær (stdlib math, god til < 10 km)
- **SVG-generering**: xml.etree.ElementTree (stdlib)
- **Afhængigheder**: kun `requests` — ingen pyproj/shapely/GDAL

## Filer

- `husportræt.py` — standalone generator, klar til brug
- `requirements.txt` — `requests>=2.28`

## Brug

```bash
python3 husportræt.py --address "Strandvejen 100, Hellerup" --scale 1000
python3 husportræt.py --lat 55.6761 --lon 12.5683 --scale 5000 --output mit_hus.svg
```

## Kartografisk stil (hardkodet i scriptet)

| Lag | Stil |
|---|---|
| Baggrund | `#f7f4ef` (varm hvid) |
| Bygning | `#e8e4db` fyld, `#2c2c2c` kontur |
| Valgt bygning | `#c0392b` (rød) |
| Vand | `#b8d8ea` fyld |
| Træer | SVG `<symbol>` — grøn cirkel med kryds, radius 1.4 mm (1:1000) / 0.55 mm (1:5000) |

## TODO / næste skridt

- [ ] **Kotekurver**: kræver SRTM-elevationsdata + `gdal_contour` (eller python-isolines). Ikke i OSM.
- [ ] **Web-frontend**: simpel HTML-formular der kalder scriptet server-side. Ingen interaktivt kort — kunden søger kun på adresse.
- [ ] **Preview**: rasteriseret PNG til visning inden køb (fx `cairosvg` eller Inkscape CLI).
- [ ] **Betalingsintegration**: Stripe o.l. — SVG leveres efter betaling.
- [ ] **Papirstørrelser**: A1 / A0 som option (ændr `PAPER_W`/`PAPER_H`).
- [ ] **Klip til papirbaggrund**: bygninger ved kanten klippes korrekt via `clip-path="url(#paper)"` — allerede implementeret.

## Kendte begrænsninger

- OSM-trædata er sparsomt i mange områder
- Ekvirektangulær projektion giver < 0.1 % fejl inden for 5 km fra centrum — tilstrækkeligt til dette formål
- Overpass API: rate-limit ved højt volumen → overvej lokal OSM-mirror på sigt
