from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_kml_and_get_measurements(tmp_path: Path):
    kml = '''<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
    <Placemark><name>Point</name><Point><coordinates>78,17,0</coordinates></Point></Placemark>
    <Placemark><name>Line</name><LineString><coordinates>78,17,0 78.01,17,0</coordinates></LineString></Placemark>
    </Document></kml>'''
    path = tmp_path / "test.kml"
    path.write_text(kml, encoding="utf-8")

    with path.open("rb") as handle:
        response = client.post("/api/files/", files={"file": ("test.kml", handle, "application/vnd.google-earth.kml+xml")})

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["feature_count"] == 2

    info = client.get(f"/api/files/{payload['id']}/")
    assert info.status_code == 200
    assert info.json()["crs"] == "EPSG:4326"

    measurements = client.get(f"/api/files/{payload['id']}/measurements/")
    assert measurements.status_code == 200
    rows = measurements.json()["measurements"]
    assert rows[0]["measurement"] is None
    assert rows[1]["measurement"] > 1000


def test_unknown_file_returns_404():
    assert client.get("/api/files/does-not-exist/").status_code == 404
