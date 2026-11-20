import unittest

from fastapi import HTTPException

from engine.app import validate_youtube_url


class YouTubeUrlValidationTests(unittest.TestCase):
    def test_watch_url_is_normalized(self):
        self.assertEqual(
            validate_youtube_url("https://www.youtube.com/watch?v=abc123XYZ_1"),
            "https://www.youtube.com/watch?v=abc123XYZ_1",
        )

    def test_live_url_is_accepted(self):
        self.assertEqual(
            validate_youtube_url("https://youtube.com/live/abc123XYZ_1"),
            "https://www.youtube.com/watch?v=abc123XYZ_1",
        )

    def test_short_url_is_accepted(self):
        self.assertEqual(
            validate_youtube_url("https://youtu.be/abc123XYZ_1"),
            "https://www.youtube.com/watch?v=abc123XYZ_1",
        )

    def test_non_youtube_host_is_rejected(self):
        with self.assertRaises(HTTPException):
            validate_youtube_url("https://example.com/watch?v=abc123XYZ_1")

    def test_non_https_url_is_rejected(self):
        with self.assertRaises(HTTPException):
            validate_youtube_url("http://youtube.com/watch?v=abc123XYZ_1")

    def test_invalid_video_id_is_rejected(self):
        with self.assertRaises(HTTPException):
            validate_youtube_url("https://youtube.com/watch?v=bad")


if __name__ == "__main__":
    unittest.main()
