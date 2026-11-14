import unittest
from redaction import mask


class OrdinaryContentTests(unittest.TestCase):
    def unchanged(self, text):
        self.assertEqual(mask(text), text)

    def test_normal_prose(self):
        self.unchanged("The standard bearer delivered the news.")

    def test_source_code(self):
        self.unchanged("TOKEN_COUNT=12\nPASSWORD_MIN_LENGTH=12\ndef login(password: str):\n    return verify(password)")

    def test_git_commit_hashes(self):
        self.unchanged("commit 0123456789abcdef0123456789abcdef01234567 (0123456)")

    def test_uuid(self):
        self.unchanged("01906183-1934-7c2d-9c18-480f3214ef61")

    def test_base64_image(self):
        self.unchanged("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")

    def test_long_file_paths(self):
        self.unchanged("C:\\projects\\" + "documentation\\" * 25 + "secret-patterns.json")

    def test_numbers(self):
        self.unchanged("0 127.0.0.1 3.14159265358979 -42 987654321012345678901234567890")
