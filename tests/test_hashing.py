import hashlib
from backend import watcher


def test_hash_file(tmp_path):
    path = tmp_path / "video.mp4"
    data = b"sample data"
    path.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert watcher._hash_file(path) == expected
