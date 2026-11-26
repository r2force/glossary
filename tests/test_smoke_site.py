import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("smoke_site", Path(__file__).resolve().parents[1] / "scripts/smoke_site.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeChecks(unittest.TestCase):
    def responses(self):
        result = {path: (200, needle.encode()) for path, needle in smoke.PAGES}
        result.update({path: (200, b"\xff\xd8" + b"x" * 2000) for path in smoke.IMAGES})
        result["/404.html"] = (200, "Страница не найдена".encode())
        result[smoke.UNKNOWN] = (404, "Страница не найдена".encode())
        return result

    def test_valid_published_responses_pass(self):
        self.assertEqual([], smoke.check(self.responses().__getitem__))

    def test_unknown_path_must_serve_the_custom_404(self):
        responses = self.responses()
        responses[smoke.UNKNOWN] = (404, b"Generic hosting error")
        self.assertTrue(smoke.check(responses.__getitem__))

    def test_pointer_instead_of_published_image_fails(self):
        responses = self.responses()
        responses[smoke.IMAGES[0]] = (200, b"version https://git-lfs.github.com/spec/v1")
        self.assertTrue(smoke.check(responses.__getitem__))


if __name__ == "__main__":
    unittest.main()
