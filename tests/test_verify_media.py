import hashlib
import importlib.util
import io
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location("verify_media", Path(__file__).resolve().parents[1] / "scripts/verify_media.py")
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


class MediaChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "site"
        self.images = self.source / "images"
        self.images.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        output = io.BytesIO()
        Image.new("RGB", (8, 8), "blue").save(output, format="PNG")
        self.data = output.getvalue()

    def git(self, *args, input=None):
        return subprocess.run(["git", "-C", str(self.root), *args], input=input,
                              capture_output=True, check=True).stdout

    def test_empty_image_directory_fails(self):
        self.assertTrue(media.verify(self.source)["errors"])

    def test_fake_png_with_dimensions_fails(self):
        fake = b"\x89PNG\r\n\x1a\n" + b"garbage!" + struct.pack(">II", 8, 8)
        (self.images / "corrupt.png").write_bytes(fake)
        self.assertTrue(media.verify(self.source)["errors"])

    def test_truncated_image_fails(self):
        with self.assertRaises(ValueError):
            media.image_info(self.data[:40])

    def test_lfs_pointer_is_not_an_image(self):
        pointer = media.POINTER + b"\noid sha256:" + b"0" * 64 + b"\nsize 1\n"
        with self.assertRaisesRegex(ValueError, "Git LFS pointer"):
            media.image_info(pointer)

    def stage_pointer(self, data, size=None):
        pointer = media.POINTER + b"\noid sha256:" + hashlib.sha256(data).hexdigest().encode()
        pointer += b"\nsize " + str(len(data) if size is None else size).encode() + b"\n"
        oid = self.git("hash-object", "-w", "--stdin", input=pointer).decode().strip()
        self.git("update-index", "--add", "--cacheinfo", f"100644,{oid},site/images/photo.png")

    def test_lfs_oid_size_and_published_bytes_are_verified(self):
        (self.images / "photo.png").write_bytes(self.data)
        self.stage_pointer(self.data)
        built = self.root / "_site"
        (built / "images").mkdir(parents=True)
        (built / "images/photo.png").write_bytes(self.data)
        result = media.verify(self.source, built)
        self.assertEqual([], result["errors"])
        self.assertEqual(1, result["lfs_verified"])
        (built / "images/photo.png").write_bytes(b"different")
        self.assertTrue(media.verify(self.source, built)["errors"])

    def test_wrong_lfs_hash_or_size_fails(self):
        (self.images / "photo.png").write_bytes(self.data)
        for original, size in [(b"other bytes", None), (self.data, len(self.data) + 1)]:
            with self.subTest(size=size):
                self.stage_pointer(original, size)
                self.assertTrue(media.verify(self.source)["errors"])

    def test_missing_tracked_image_fails(self):
        self.stage_pointer(self.data)
        self.assertTrue(media.verify(self.source)["errors"])


if __name__ == "__main__":
    unittest.main()
