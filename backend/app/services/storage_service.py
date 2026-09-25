import os
import uuid
import logging
from typing import Tuple, Optional
from google.cloud import storage
from google.cloud.exceptions import NotFound, Conflict
from app.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.client: Optional[storage.Client] = None
        self._init_client()

    def _init_client(self):
        try:
            self.client = storage.Client(project=self.project_id)
            # Ensure bucket exists
            self._ensure_bucket()
        except Exception as e:
            logger.warning(f"Could not initialize GCP Storage Client: {e}. Fallback to local storage if needed.")
            self.client = None

    def _ensure_bucket(self):
        if not self.client:
            return
        try:
            bucket = self.client.get_bucket(self.bucket_name)
            logger.info(f"Connected to existing GCS bucket: {self.bucket_name}")
        except NotFound:
            try:
                logger.info(f"Creating GCS bucket {self.bucket_name} in location {settings.GOOGLE_CLOUD_LOCATION}...")
                bucket = self.client.create_bucket(self.bucket_name, location=settings.GOOGLE_CLOUD_LOCATION)
                logger.info(f"Bucket {self.bucket_name} successfully created.")
            except Conflict:
                logger.info(f"Bucket {self.bucket_name} already exists.")
            except Exception as ex:
                logger.error(f"Error creating GCS bucket {self.bucket_name}: {ex}")

    def upload_file_bytes(
        self,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
        user_id: str
    ) -> Tuple[str, str]:
        """
        Uploads document bytes to GCS.
        Returns: (gcs_uri, gcs_path)
        """
        ext = os.path.splitext(original_filename)[1]
        unique_id = str(uuid.uuid4())
        gcs_path = f"uploads/{user_id}/{unique_id}_{original_filename}"
        
        if self.client:
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(gcs_path)
                blob.upload_from_string(file_bytes, content_type=content_type)
                gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
                logger.info(f"Successfully uploaded {original_filename} to {gcs_uri}")
                return gcs_uri, gcs_path
            except Exception as e:
                logger.error(f"Failed to upload to GCS: {e}. Falling back to local disk.")

        # Local fallback if GCS credentials/network not available
        local_dir = os.path.join(os.getcwd(), "local_storage", user_id)
        os.makedirs(local_dir, exist_ok=True)
        local_filepath = os.path.join(local_dir, f"{unique_id}_{original_filename}")
        with open(local_filepath, "wb") as f:
            f.write(file_bytes)
        
        local_uri = f"file://{local_filepath}"
        return local_uri, local_filepath

    def read_file_text_sample(self, gcs_path: str, max_chars: int = 25000) -> Optional[str]:
        """
        Extracts clean, readable document text content from GCS or local disk.
        Supports:
        - PDF documents (via pypdf)
        - Microsoft Word (.docx) documents (via OpenXML / zipfile)
        - RTF documents
        - Plain text / Markdown / HTML
        Guarantees that raw binary archives (PK-compressed files) are NEVER decoded as raw junk text.
        """
        raw_bytes = None
        if self.client and not gcs_path.startswith("/"):
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob(gcs_path)
                raw_bytes = blob.download_as_bytes()
            except Exception as e:
                logger.warning(f"Could not download file from GCS: {e}")
        elif os.path.exists(gcs_path):
            try:
                with open(gcs_path, "rb") as f:
                    raw_bytes = f.read()
            except Exception as e:
                logger.warning(f"Could not read local file: {e}")

        if not raw_bytes:
            return None

        # 1. Check if PDF document
        if raw_bytes.startswith(b"%PDF"):
            try:
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw_bytes))
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages_text.append(f"[Page {idx+1}]\n{text.strip()}")
                extracted = "\n\n".join(pages_text).strip()
                if extracted:
                    return extracted[:max_chars]
            except Exception as ex:
                logger.error(f"Error parsing PDF content: {ex}")

        # 2. Check if Microsoft Word (.docx) document (PK-compressed zip archive)
        if raw_bytes.startswith(b"PK\x03\x04"):
            try:
                import io
                import zipfile
                import xml.etree.ElementTree as ET

                # Try python-docx if installed
                try:
                    import docx
                    doc = docx.Document(io.BytesIO(raw_bytes))
                    doc_texts = [p.text for p in doc.paragraphs if p.text.strip()]
                    for table in doc.tables:
                        for row in table.rows:
                            row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                            if row_text:
                                doc_texts.append(row_text)
                    extracted = "\n\n".join(doc_texts).strip()
                    if extracted:
                        return extracted[:max_chars]
                except Exception:
                    pass

                # Built-in robust OpenXML parser
                with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                    if "word/document.xml" in z.namelist():
                        xml_bytes = z.read("word/document.xml")
                        tree = ET.fromstring(xml_bytes)
                        ns_p = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
                        ns_t = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                        paragraphs = []
                        for p in tree.iter(ns_p):
                            t_nodes = [node.text for node in p.iter(ns_t) if node.text]
                            if t_nodes:
                                paragraphs.append("".join(t_nodes).strip())
                        extracted = "\n\n".join(paragraphs).strip()
                        if extracted:
                            return extracted[:max_chars]
            except Exception as ex:
                logger.warning(f"Error parsing DOCX file: {ex}")

        # 3. Check for Rich Text Format (.rtf)
        if raw_bytes.startswith(b"{\\rtf"):
            try:
                import re
                text = raw_bytes.decode("ascii", errors="ignore")
                clean_text = re.sub(r"\\[a-z0-9]+-?", " ", text)
                clean_text = re.sub(r"[{}]", "", clean_text)
                clean_text = "\n".join(line.strip() for line in clean_text.splitlines() if line.strip())
                if clean_text:
                    return clean_text[:max_chars]
            except Exception as ex:
                logger.warning(f"Error parsing RTF content: {ex}")

        # 4. Binary check: Never return raw PK archives or binary byte streams to the LLM
        sample_slice = raw_bytes[:512]
        if b"\x00" in sample_slice or raw_bytes.startswith(b"PK\x03\x04"):
            logger.warning("File is binary / unparsed archive; refusing to decode raw bytes to prevent PK-compression error.")
            return None

        # 5. Plain text / Markdown / CSV fallback
        try:
            decoded = raw_bytes.decode("utf-8", errors="ignore").strip()
            if decoded and not decoded.startswith("PK"):
                return decoded[:max_chars]
            return None
        except Exception:
            return None

storage_service = StorageService()
