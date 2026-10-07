from pathlib import Path

from app.geospatial import normalize_features, read_geospatial_file
from app.kml_parser import read_kml


def test_kml_measurements(tmp_path: Path):
    kml = '''<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark><name>Point A</name><Point><coordinates>78.0,17.0,0</coordinates></Point></Placemark>
        <Placemark><name>Line A</name><LineString><coordinates>78.0,17.0,0 78.01,17.0,0</coordinates></LineString></Placemark>
        <Placemark><name>Polygon A</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
          78.0,17.0,0 78.01,17.0,0 78.01,17.01,0 78.0,17.01,0 78.0,17.0,0
        </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
      </Document>
    </kml>'''
    path = tmp_path / "sample.kml"
    path.write_text(kml, encoding="utf-8")

    features, crs = read_geospatial_file(str(path))
    result = normalize_features(features, crs)

    assert len(result) == 3
    assert result[0]["geometry_type"] == "Point"
    assert result[0]["measurement"] is None
    assert result[1]["geometry_type"] == "LineString"
    assert result[1]["measurement"] > 1000
    assert result[2]["geometry_type"] == "Polygon"
    assert result[2]["measurement"] > 1_000_000
    assert result[2]["measurement_crs"].startswith("EPSG:326")


def test_kml_properties(tmp_path: Path):
    kml = '''<kml xmlns="http://www.opengis.net/kml/2.2"><Placemark>
    <name>Test Place</name><ExtendedData><Data name="owner"><value>Kalyan</value></Data></ExtendedData>
    <Point><coordinates>78,17,0</coordinates></Point></Placemark></kml>'''
    path = tmp_path / "properties.kml"
    path.write_text(kml, encoding="utf-8")
    features = read_kml(str(path))
    assert features[0]["properties"] == {"name": "Test Place", "owner": "Kalyan"}
