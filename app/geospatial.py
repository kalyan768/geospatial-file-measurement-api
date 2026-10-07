from __future__ import annotations

from typing import Any

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import mapping
from shapely.ops import transform

from .kml_parser import read_kml


def _crs_label(crs: Any) -> str | None:
    if crs is None:
        return None
    try:
        return CRS.from_user_input(crs).to_string()
    except Exception:
        return str(crs)


def read_geospatial_file(path: str) -> tuple[list[dict[str, Any]], CRS | None]:
    """Read KML or zipped Shapefile into normalized feature records."""
    lower = path.lower()
    if lower.endswith(".kml"):
        features = read_kml(path)
        return features, CRS.from_epsg(4326)

    gdf = gpd.read_file(path)
    features = []
    for index, row in gdf.iterrows():
        properties = {}
        for key, value in row.items():
            if key == gdf.geometry.name:
                continue
            # Convert pandas/numpy scalars into JSON-safe Python values.
            try:
                if hasattr(value, "item"):
                    value = value.item()
            except Exception:
                pass
            if value is not None:
                properties[str(key)] = value
        features.append(
            {
                "id": int(index) if isinstance(index, (int, float)) else str(index),
                "geometry": row.geometry,
                "properties": properties,
            }
        )
    return features, CRS.from_user_input(gdf.crs) if gdf.crs else None


def _representative_lon_lat(geometry, source_crs: CRS | None) -> tuple[float, float]:
    if source_crs and not source_crs.is_geographic:
        point = transform(
            CRS.from_user_input(source_crs).get_geod().inv,
            geometry,
        ) if False else None
    if source_crs and source_crs.is_geographic:
        point = geometry.representative_point()
        return float(point.x), float(point.y)

    # For projected source CRS, transform a representative point to WGS84.
    point = geometry.representative_point()
    from pyproj import Transformer
    transformer = Transformer.from_crs(source_crs, 4326, always_xy=True)
    lon, lat = transformer.transform(point.x, point.y)
    return float(lon), float(lat)


def metric_crs_for_geometry(geometry, source_crs: CRS | None) -> CRS | None:
    if source_crs is None:
        return None
    if source_crs.is_projected:
        axis_units = [axis.unit_name.lower() for axis in source_crs.axis_info if axis.unit_name]
        if axis_units and all("metre" in unit or "meter" in unit for unit in axis_units):
            return source_crs

    lon, lat = _representative_lon_lat(geometry, source_crs)
    # UTM zone from longitude. Clamp at the valid UTM latitude range.
    zone = int((lon + 180) // 6) + 1
    zone = max(1, min(zone, 60))
    if lat >= 0:
        return CRS.from_epsg(32600 + zone)
    return CRS.from_epsg(32700 + zone)


def calculate_measurement(geometry, source_crs: CRS | None) -> tuple[float | None, str | None, str | None]:
    """Return (measurement, unit, measurement_crs)."""
    if geometry is None or geometry.is_empty:
        return None, None, None
    geom_type = geometry.geom_type
    if geom_type in {"Point", "MultiPoint"}:
        return None, None, None
    if source_crs is None:
        return None, None, None

    target_crs = metric_crs_for_geometry(geometry, source_crs)
    if target_crs is None:
        return None, None, None

    from pyproj import Transformer
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    projected = transform(transformer.transform, geometry)

    if geom_type in {"Polygon", "MultiPolygon"}:
        return float(projected.area), "m²", target_crs.to_string()
    if geom_type in {"LineString", "MultiLineString"}:
        return float(projected.length), "m", target_crs.to_string()
    return None, None, target_crs.to_string()


def normalize_features(features: list[dict[str, Any]], source_crs: CRS | None) -> list[dict[str, Any]]:
    normalized = []
    for feature in features:
        geometry = feature["geometry"]
        measurement, unit, measurement_crs = calculate_measurement(geometry, source_crs)
        normalized.append(
            {
                "feature_id": feature["id"],
                "geometry_type": geometry.geom_type,
                "geometry": mapping(geometry),
                "crs": _crs_label(source_crs),
                "properties": feature.get("properties", {}),
                "measurement": measurement,
                "measurement_unit": unit,
                "measurement_crs": measurement_crs,
                "measurement_supported": measurement is not None,
            }
        )
    return normalized
