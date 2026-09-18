import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from api.media_catalog import MediaCatalog, _default_media_path


class MediaCatalogTest(TestCase):
    def test_returns_media_in_citation_order_and_deduplicates_documents(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "media.jsonl"
            rows = [
                {
                    "document_id": "aks:E1",
                    "article_title": "첫 문서",
                    "images": [{"mid": "M1", "role": "head", "title": "제목 &amp; 설명", "url": "https://example.com/1.jpg", "kogl_type": "KOGL1", "kogl_label": "공공누리 제1유형"}],
                },
                {
                    "document_id": "aks:E2",
                    "article_title": "둘째 문서",
                    "images": [{"mid": "M2", "role": "related", "url": "https://example.com/2.jpg", "kogl_type": "KOGL4", "kogl_label": "공공누리 제4유형"}],
                },
            ]
            path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

            result = MediaCatalog(path).get_many(["aks:E2", "aks:E1", "aks:E2", "aks:missing"])

        self.assertEqual([item["document_id"] for item in result], ["aks:E2", "aks:E1"])
        self.assertEqual(result[0]["images"][0]["role"], "related")
        self.assertEqual(result[1]["images"][0]["kogl_label"], "공공누리 제1유형")
        self.assertEqual(result[1]["images"][0]["title"], "제목 & 설명")

    def test_excludes_images_without_kogl_or_url(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "media.jsonl"
            row = {
                "document_id": "aks:E1",
                "images": [
                    {"mid": "ok", "url": "https://example.com/ok.jpg", "kogl_type": "KOGL2"},
                    {"mid": "no-kogl", "url": "https://example.com/no.jpg", "kogl_type": ""},
                    {"mid": "no-url", "url": "", "kogl_type": "KOGL1"},
                ],
            }
            path.write_text(json.dumps(row), encoding="utf-8")

            result = MediaCatalog(path).get_many(["aks:E1"])

        self.assertEqual([image["mid"] for image in result[0]["images"]], ["ok"])
        self.assertEqual(result[0]["images"][0]["kogl_label"], "공공누리 제2유형")
        self.assertEqual(result[0]["images"][0]["attribution"], "『한국민족문화대백과사전』")

    def test_missing_file_returns_empty_result(self):
        with TemporaryDirectory() as directory:
            result = MediaCatalog(Path(directory) / "missing.jsonl").get_many(["aks:E1"])

        self.assertEqual(result, [])

    def test_default_path_points_to_repository_processed_data(self):
        expected = Path(__file__).resolve().parents[3] / "data" / "processed" / "aks_article_medias.jsonl"

        with patch.dict("os.environ", {}, clear=True):
            result = _default_media_path()

        self.assertEqual(result, expected)

    def test_unexpected_json_shape_is_ignored(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "media.jsonl"
            path.write_text('["not", "an", "object"]\n', encoding="utf-8")

            result = MediaCatalog(path).get_many(["aks:E1"])

        self.assertEqual(result, [])

    def test_file_read_error_returns_empty_result(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "media.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            catalog = MediaCatalog(path)

            with patch.object(Path, "open", side_effect=OSError("read failed")):
                with self.assertLogs("api.media_catalog", level="WARNING"):
                    result = catalog.get_many(["aks:E1"])

        self.assertEqual(result, [])
