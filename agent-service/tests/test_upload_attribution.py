import unittest
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import Response, UploadFile
from starlette.requests import Request

from app.admin.router import upload_document
from app.admin.service import DocumentAdminService


class UploadAttributionTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_uses_verified_account_identity(self):
        request = Request({"type": "http", "headers": []})
        file = UploadFile(file=io.BytesIO(b"sample"), filename="sample.txt")
        response = Response()
        service = SimpleNamespace(upload_document=AsyncMock(return_value=("saved", False)))
        actor = SimpleNamespace(email="reader@example.org", display_name="Reader")

        with patch("app.admin.router.require_actor", return_value=actor):
            result = await upload_document(
                request=request,
                response=response,
                file=file,
                area=None,
                role=None,
                vigencia=None,
                source_url=None,
                service=service,
            )

        self.assertEqual(result, "saved")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(service.upload_document.await_args.kwargs["uploaded_by_email"], actor.email)
        self.assertEqual(service.upload_document.await_args.kwargs["uploaded_by_name"], actor.display_name)

    def test_document_detail_preserves_attribution(self):
        from datetime import datetime, timezone
        from uuid import uuid4

        row = {
            "id": uuid4(), "filename": "sample.txt", "status": "ready", "size_bytes": 12,
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
            "checksum": "abc", "uploaded_by_email": "reader@example.org",
            "uploaded_by_name": "Reader",
        }
        detail = DocumentAdminService._to_detail(row)
        self.assertEqual(detail.uploaded_by_email, "reader@example.org")
        self.assertEqual(detail.uploaded_by_name, "Reader")


if __name__ == "__main__":
    unittest.main()
