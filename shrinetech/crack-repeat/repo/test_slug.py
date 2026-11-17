import unittest
from slug import slugify

class SlugTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")
    def test_spaces_and_dashes(self):
        self.assertEqual(slugify("  Many   spaces -- here  "), "many-spaces-here")
    def test_accents(self):
        self.assertEqual(slugify("Café Déjà Vu"), "cafe-deja-vu")

if __name__ == "__main__":
    unittest.main()
