"""Google Docs integration for document creation and management.

Google Docs API allows:
- Creating documents from templates
- Inserting and formatting content
- Exporting to various formats (PDF, DOCX, etc.)
- Real-time collaboration

Use cases in ATLAS:
- Books (chapters, formatting)
- Technical documentation
- Reports and guides
- Content that needs human editing
"""

import os
import logging
from typing import Optional

import httpx

from .base import (
    PlatformIntegration,
    PlatformCategory,
    Requirement,
    RequirementType,
    ValidationResult,
    SubmissionResult,
    SubmissionStatus,
)

logger = logging.getLogger(__name__)


# Document templates by type
DOCUMENT_TEMPLATES = {
    "book_manuscript": {
        "name": "Book Manuscript",
        "description": "Standard manuscript format for books",
        "page_size": {"width": 8.5, "height": 11},  # inches
        "margins": {"top": 1, "bottom": 1, "left": 1.25, "right": 1.25},
    },
    "book_6x9": {
        "name": "Trade Paperback (6x9)",
        "description": "Common paperback size",
        "page_size": {"width": 6, "height": 9},
        "margins": {"top": 0.75, "bottom": 0.75, "left": 0.75, "right": 0.75},
    },
    "technical_doc": {
        "name": "Technical Documentation",
        "description": "Technical docs with code blocks",
        "page_size": {"width": 8.5, "height": 11},
        "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
    },
    "guide": {
        "name": "Guide/Tutorial",
        "description": "Step-by-step guide format",
        "page_size": {"width": 8.5, "height": 11},
        "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
    },
}


class GoogleDocsIntegration(PlatformIntegration):
    """Google Docs integration for document creation."""

    name = "Google Docs"
    icon = "📝"
    category = PlatformCategory.DOCUMENTS
    description = "Create and format documents, books, and guides"
    docs_url = "https://developers.google.com/docs/api"

    supported_types = ["document", "doc_book", "doc_technical", "doc_guide"]

    BASE_URL = "https://docs.googleapis.com/v1"
    DRIVE_URL = "https://www.googleapis.com/drive/v3"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Google uses OAuth, so we need credentials
        self.credentials_path = config.get("credentials_path") if config else os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.token = config.get("token") if config else os.getenv("GOOGLE_ACCESS_TOKEN")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_env_vars(self) -> list[str]:
        return ["GOOGLE_CREDENTIALS_PATH", "GOOGLE_ACCESS_TOKEN"]

    async def authenticate(self) -> bool:
        """Verify Google API credentials.

        Note: Full OAuth flow would require user interaction.
        This assumes a valid access token is available.
        """
        if not self.token:
            logger.warning("GOOGLE_ACCESS_TOKEN not set")
            return False

        try:
            response = await self.client.get(
                f"{self.DRIVE_URL}/about",
                params={"fields": "user"}
            )
            if response.status_code == 200:
                self._authenticated = True
                user = response.json().get("user", {})
                logger.info(f"Authenticated with Google as {user.get('displayName', 'Unknown')}")
                return True
            else:
                logger.error(f"Google auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"Google auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get Google Docs requirements based on project type."""
        requirements = [
            Requirement(
                name="google_credentials",
                type=RequirementType.CREDENTIAL,
                description="Google OAuth credentials",
                required=True,
            ),
        ]

        if project_type in ["doc_book", "document"]:
            requirements.extend([
                Requirement(
                    name="title",
                    type=RequirementType.TEXT,
                    description="Document/Book title",
                    required=True,
                ),
                Requirement(
                    name="content",
                    type=RequirementType.TEXT,
                    description="Document content (chapters, sections)",
                    required=True,
                ),
                Requirement(
                    name="table_of_contents",
                    type=RequirementType.TEXT,
                    description="Table of contents structure",
                    required=False,
                ),
            ])

        if project_type == "doc_technical":
            requirements.append(Requirement(
                name="code_samples",
                type=RequirementType.TEXT,
                description="Code samples to include",
                required=False,
            ))

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate product has required content for Google Docs."""
        requirements = self.get_requirements(project_type)
        missing = []
        warnings = []
        errors = []

        content = product.get("content", {})

        for req in requirements:
            if req.type == RequirementType.CREDENTIAL:
                if not self.token:
                    if req.required:
                        errors.append(f"Missing {req.name}: {req.description}")
                        missing.append(req)
                continue

            if req.name not in content and req.name not in product:
                if req.required:
                    missing.append(req)
                else:
                    warnings.append(f"Optional content missing: {req.name}")

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Create a document in Google Docs."""
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Not authenticated with Google",
            )

        title = product.get("title", product.get("name", "ATLAS Document"))

        try:
            # Create a new document
            response = await self.client.post(
                f"{self.BASE_URL}/documents",
                json={"title": title}
            )

            if response.status_code in [200, 201]:
                doc = response.json()
                doc_id = doc.get("documentId")

                # Insert content if provided
                content = product.get("content", {})
                if content:
                    await self._insert_content(doc_id, content, project_type)

                doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

                return SubmissionResult(
                    success=True,
                    submission_id=doc_id,
                    status=SubmissionStatus.PUBLISHED,
                    url=doc_url,
                    message=f"Created document: {title}",
                    metadata={"document_id": doc_id, "title": title},
                )
            else:
                return SubmissionResult(
                    success=False,
                    status=SubmissionStatus.FAILED,
                    message=f"Failed to create document: {response.status_code}",
                )

        except Exception as e:
            logger.exception(f"Error creating Google Doc: {e}")
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    async def _insert_content(
        self,
        doc_id: str,
        content: dict,
        project_type: str,
    ) -> bool:
        """Insert content into a Google Doc.

        Args:
            doc_id: Document ID
            content: Content dict with chapters/sections
            project_type: Type of document

        Returns:
            True if content inserted successfully
        """
        requests = []
        index = 1  # Start after title

        # Add table of contents if book
        if project_type == "doc_book" and content.get("chapters"):
            requests.append({
                "insertText": {
                    "location": {"index": index},
                    "text": "Table of Contents\n\n"
                }
            })
            index += len("Table of Contents\n\n")

            for i, chapter in enumerate(content["chapters"], 1):
                toc_entry = f"{i}. {chapter.get('title', f'Chapter {i}')}\n"
                requests.append({
                    "insertText": {
                        "location": {"index": index},
                        "text": toc_entry
                    }
                })
                index += len(toc_entry)

            requests.append({
                "insertText": {
                    "location": {"index": index},
                    "text": "\n\n"
                }
            })
            index += 2

        # Add chapters/sections
        chapters = content.get("chapters", content.get("sections", []))
        for chapter in chapters:
            # Chapter title
            title = chapter.get("title", "Untitled")
            requests.append({
                "insertText": {
                    "location": {"index": index},
                    "text": f"\n{title}\n\n"
                }
            })
            index += len(f"\n{title}\n\n")

            # Chapter content
            body = chapter.get("content", chapter.get("body", ""))
            if body:
                requests.append({
                    "insertText": {
                        "location": {"index": index},
                        "text": f"{body}\n\n"
                    }
                })
                index += len(f"{body}\n\n")

        if requests:
            try:
                response = await self.client.post(
                    f"{self.BASE_URL}/documents/{doc_id}:batchUpdate",
                    json={"requests": requests}
                )
                return response.status_code == 200
            except Exception as e:
                logger.exception(f"Error inserting content: {e}")
                return False

        return True

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check document status."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/documents/{submission_id}"
            )
            if response.status_code == 200:
                doc = response.json()
                return SubmissionResult(
                    success=True,
                    submission_id=submission_id,
                    status=SubmissionStatus.PUBLISHED,
                    url=f"https://docs.google.com/document/d/{submission_id}/edit",
                    metadata={"title": doc.get("title")},
                )
            else:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.FAILED,
                    message=f"Document not found: {response.status_code}",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    async def export_document(
        self,
        doc_id: str,
        format: str = "pdf",
    ) -> Optional[bytes]:
        """Export a document to a file.

        Args:
            doc_id: Document ID
            format: Export format (pdf, docx, txt, html)

        Returns:
            File content as bytes
        """
        mime_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "html": "text/html",
        }

        mime_type = mime_types.get(format, "application/pdf")

        try:
            response = await self.client.get(
                f"{self.DRIVE_URL}/files/{doc_id}/export",
                params={"mimeType": mime_type}
            )

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Export failed: {response.status_code}")
                return None

        except Exception as e:
            logger.exception(f"Error exporting document: {e}")
            return None

    async def create_asset(
        self,
        asset_type: str,
        specs: dict,
        content: Optional[dict] = None,
    ) -> Optional[dict]:
        """Create a document asset.

        Args:
            asset_type: Type from DOCUMENT_TEMPLATES
            specs: Page specs
            content: Content to include

        Returns:
            Document metadata
        """
        if asset_type not in DOCUMENT_TEMPLATES:
            asset_type = "book_manuscript"  # Default

        template = DOCUMENT_TEMPLATES[asset_type]
        title = content.get("title", content.get("name", "ATLAS Document")) if content else "ATLAS Document"

        result = await self.publish(
            {"title": title, "content": content or {}},
            "document"
        )

        if result.success:
            return {
                "id": result.submission_id,
                "type": asset_type,
                "url": result.url,
                "template": template,
            }
        return None
