import urllib.request
from backend import instagram


def test_local_http_url(tmp_path):
    file_path = tmp_path / "vid.mp4"
    data = b"hello"
    file_path.write_bytes(data)

    url = instagram._local_http_url(str(file_path))
    with urllib.request.urlopen(url) as resp:
        assert resp.read() == data

    instagram.stop_http_server()
