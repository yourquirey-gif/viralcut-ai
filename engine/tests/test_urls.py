import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from engine.app import list_segment_files, validate_youtube_url


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

    def test_mobile_watch_url_is_normalized(self):
        self.assertEqual(
            validate_youtube_url("https://m.youtube.com/watch?v=abc123XYZ_1"),
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

    def test_non_video_youtube_path_is_rejected(self):
        with self.assertRaises(HTTPException):
            validate_youtube_url("https://youtube.com/shorts/abc123XYZ_1")


class SegmentDiscoveryTests(unittest.TestCase):
    def test_only_non_empty_mp4_segments_are_returned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "first.mp4").write_bytes(b"video")
            (root / "empty.mp4").write_bytes(b"")
            (root / "notes.txt").write_text("not a video")
            nested = root / "attempt-02"
            nested.mkdir()
            (nested / "second.mp4").write_bytes(b"video two")

            names = [path.name for path in list_segment_files(root)]
            self.assertEqual(set(names), {"first.mp4", "second.mp4"})

    def test_missing_output_directory_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "does-not-exist"
            self.assertEqual(list_segment_files(missing), [])


if __name__ == "__main__":
    unittest.main()
