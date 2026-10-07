from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from shapely.geometry import LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon


class KMLParseError(ValueError):
    """Raised when a KML file cannot be parsed."""


SUPPORTED_GEOMETRY_BUILDERS = {
    "Point": Point,
    "LineString": LineString,
    "Polygon": Polygon,
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _coordinates(text: str | None) -> list[tuple[float, float]]:
    if not text:
        return []
    coords: list[tuple[float, float]] = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        coords.append((float(parts[0]), float(parts[1])))
    return coords


def _polygon_from_element(element: ET.Element) -> Polygon | MultiPolygon | None:
    rings: list[list[tuple[float, float]]] = []
    for child in element.iter():
        if _local_name(child.tag) == "coordinates":
            coords = _coordinates(child.text)
            if len(coords) >= 4:
                rings.append(coords)

    if not rings:
        return None
    outer = rings[0]
    holes = rings[1:]
    return Polygon(outer, holes=holes)


def _geometry_from_placemark(placemark: ET.Element):
    for element in placemark.iter():
        name = _local_name(element.tag)
        if name == "Point":
            for child in element.iter():
                if _local_name(child.tag) == "coordinates":
                    coords = _coordinates(child.text)
                    return Point(coords[0]) if coords else None
        elif name == "LineString":
            for child in element.iter():
                if _local_name(child.tag) == "coordinates":
                    coords = _coordinates(child.text)
                    return LineString(coords) if len(coords) >= 2 else None
        elif name == "Polygon":
            return _polygon_from_element(element)
        elif name == "MultiGeometry":
            parts = []
            for sub in element.iter():
                sub_name = _local_name(sub.tag)
                if sub_name == "Point":
                    for child in sub.iter():
                        if _local_name(child.tag) == "coordinates":
                            coords = _coordinates(child.text)
                            if coords:
                                parts.append(Point(coords[0]))
                            break
                elif sub_name == "LineString":
                    for child in sub.iter():
                        if _local_name(child.tag) == "coordinates":
                            coords = _coordinates(child.text)
                            if len(coords) >= 2:
                                parts.append(LineString(coords))
                            break
                elif sub_name == "Polygon":
                    polygon = _polygon_from_element(sub)
                    if polygon is not None:
                        parts.append(polygon)
            if not parts:
                return None
            if all(isinstance(p, Point) for p in parts):
                return MultiPoint(parts)
            if all(isinstance(p, LineString) for p in parts):
                return MultiLineString(parts)
            if all(isinstance(p, (Polygon, MultiPolygon)) for p in parts):
                polygons = []
                for p in parts:
                    polygons.extend(list(p.geoms) if isinstance(p, MultiPolygon) else [p])
                return MultiPolygon(polygons)
    return None


def _properties(placemark: ET.Element) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    name = next((el.text for el in placemark.iter() if _local_name(el.tag) == "name"), None)
    if name:
        properties["name"] = name

    for data in placemark.iter():
        if _local_name(data.tag) != "Data":
            continue
        key = data.attrib.get("name")
        value = next((el.text for el in data.iter() if _local_name(el.tag) == "value"), None)
        if key:
            properties[key] = value
    return properties


def read_kml(path: str) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError, ValueError) as exc:
        raise KMLParseError(f"Invalid KML file: {exc}") from exc

    features = []
    for index, placemark in enumerate(
        el for el in root.iter() if _local_name(el.tag) == "Placemark"
    ):
        geometry = _geometry_from_placemark(placemark)
        if geometry is None:
            continue
        features.append(
            {
                "id": index,
                "geometry": geometry,
                "properties": _properties(placemark),
            }
        )
    return features
