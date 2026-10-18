"""CRUD and schema tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.crud import create_item, read_content, update_item
from app.database import get_item, init_db
from app.schemas import ItemCreate, ItemUpdate


class CrudTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "catalog.sqlite"
        init_db(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_update_and_content(self) -> None:
        created = create_item(
            ItemCreate(
                file_name="test-memo.md",
                rel_path="legal/test-memo.md",
                content="# Hello\n\nTest body.",
                department="legal",
                doc_type="rights_clearance",
            ),
            db_path=self.db,
        )
        self.assertEqual(created["file_name"], "test-memo.md")
        self.assertTrue(created["publish_pending"])
        self.assertIn("Hello", read_content(created["item_id"]))

        updated = update_item(
            created["item_id"],
            ItemUpdate(content="# Hello\n\nUpdated paragraph."),
            db_path=self.db,
        )
        self.assertTrue(updated["publish_pending"])
        item = get_item(self.db, created["item_id"])
        assert item
        self.assertNotEqual(item.content_hash, item.published_content_hash)


if __name__ == "__main__":
    unittest.main()
