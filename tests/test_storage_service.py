import os
import io
import zipfile
import pytest
from unittest.mock import MagicMock, patch
from google.cloud.exceptions import NotFound, Conflict
from app.services.storage_service import StorageService

def test_storage_service_init_and_ensure_bucket():
    # 1. When storage.Client raises Exception
    with patch("google.cloud.storage.Client", side_effect=Exception("No credentials")):
        s_err = StorageService()
        assert s_err.client is None

    # 2. When storage.Client succeeds and bucket exists
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.get_bucket.return_value = mock_bucket
    with patch("google.cloud.storage.Client", return_value=mock_client):
        s_ok = StorageService()
        assert s_ok.client is mock_client

    # 3. When bucket not found, then create succeeds
    mock_client.get_bucket.side_effect = NotFound("Bucket not found")
    with patch("google.cloud.storage.Client", return_value=mock_client):
        s_created = StorageService()
        mock_client.create_bucket.assert_called()

    # 4. When create_bucket raises Conflict
    mock_client.get_bucket.side_effect = NotFound("Bucket not found")
    mock_client.create_bucket.side_effect = Conflict("Already exists")
    with patch("google.cloud.storage.Client", return_value=mock_client):
        s_conflict = StorageService()
        assert s_conflict.client is mock_client

    # 5. When create_bucket raises generic Exception
    mock_client.get_bucket.side_effect = NotFound("Bucket not found")
    mock_client.create_bucket.side_effect = Exception("Forbidden")
    with patch("google.cloud.storage.Client", return_value=mock_client):
        s_create_err = StorageService()
        assert s_create_err.client is mock_client

def test_upload_file_bytes_gcs_and_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # 1. GCS upload success
    s = StorageService()
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    s.client = mock_client

    uri, path = s.upload_file_bytes(b"sample bytes", "test.txt", "text/plain", "user-123")
    assert uri.startswith("gs://")
    assert "uploads/user-123/" in path
    mock_blob.upload_from_string.assert_called_once_with(b"sample bytes", content_type="text/plain")

    # 2. GCS upload error -> falls back to local disk
    mock_blob.upload_from_string.side_effect = Exception("Network timeout")
    uri_fb, path_fb = s.upload_file_bytes(b"fallback bytes", "fallback.txt", "text/plain", "user-123")
    assert uri_fb.startswith("file://")
    assert os.path.exists(path_fb)
    with open(path_fb, "rb") as f:
        assert f.read() == b"fallback bytes"

    # 3. Local disk fallback when client is None
    s.client = None
    uri_local, path_local = s.upload_file_bytes(b"pure local bytes", "local.txt", "text/plain", "user-456")
    assert uri_local.startswith("file://")
    assert os.path.exists(path_local)
    with open(path_local, "rb") as f:
        assert f.read() == b"pure local bytes"

def test_read_file_text_sample_all_formats(tmp_path):
    s = StorageService()
    s.client = None  # test local reading directly

    # 1. Non-existent file
    assert s.read_file_text_sample(str(tmp_path / "missing.txt")) is None

    # 2. Empty file
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    assert s.read_file_text_sample(str(empty_file)) is None

    # 3. Plain text file
    txt_file = tmp_path / "plain.txt"
    txt_file.write_text("Hello LegalLens plain text contract.", encoding="utf-8")
    assert s.read_file_text_sample(str(txt_file)) == "Hello LegalLens plain text contract."

    # 4. Rich Text Format (.rtf)
    rtf_file = tmp_path / "sample.rtf"
    rtf_content = rb"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}\f0\fs24 This is RTF legal content.}"
    rtf_file.write_bytes(rtf_content)
    rtf_parsed = s.read_file_text_sample(str(rtf_file))
    assert "This is RTF legal content." in rtf_parsed

    # RTF parsing exception: falls back to plain text decode
    with patch("re.sub", side_effect=Exception("Regex failed")):
        rtf_fallback = s.read_file_text_sample(str(rtf_file))
        assert "This is RTF legal content." in rtf_fallback

    # 5. PDF document parsing
    pdf_file = tmp_path / "test.pdf"
    # Create a minimal valid PDF
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(pdf_file, "wb") as f:
        writer.write(f)
    
    # Read PDF (should handle pdf reader without crashing)
    pdf_read = s.read_file_text_sample(str(pdf_file))
    # Blank page returns None or empty
    assert pdf_read is None or isinstance(pdf_read, str)

    # PDF parsing with mocked page text
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page 1 Content: Confidentiality Clause"
    mock_reader.pages = [mock_page]
    with patch("pypdf.PdfReader", return_value=mock_reader):
        pdf_res = s.read_file_text_sample(str(pdf_file))
        assert "[Page 1]\nPage 1 Content: Confidentiality Clause" in pdf_res

    # PDF parsing exception with binary bytes (real PDF structure with null bytes)
    pdf_corrupt_bin = tmp_path / "corrupt_bin.pdf"
    pdf_corrupt_bin.write_bytes(b"%PDF-1.4\x00\x00\xffstream corrupted")
    with patch("pypdf.PdfReader", side_effect=Exception("Corrupted PDF")):
        assert s.read_file_text_sample(str(pdf_corrupt_bin)) is None

    # 6. DOCX document parsing (built-in OpenXML parser)
    docx_file = tmp_path / "test.docx"
    xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p><w:r><w:t>First Paragraph of NDA Agreement.</w:t></w:r></w:p>
            <w:p><w:r><w:t>Second Paragraph governing California law.</w:t></w:r></w:p>
        </w:body>
    </w:document>
    """
    with zipfile.ZipFile(str(docx_file), "w") as z:
        z.writestr("word/document.xml", xml_content)

    docx_text = s.read_file_text_sample(str(docx_file))
    assert "First Paragraph of NDA Agreement." in docx_text
    assert "Second Paragraph governing California law." in docx_text

    # DOCX parsing with python-docx branch
    mock_doc = MagicMock()
    p1 = MagicMock()
    p1.text = "Python Docx Paragraph"
    mock_doc.paragraphs = [p1]
    table = MagicMock()
    row = MagicMock()
    c1 = MagicMock()
    c1.text = "Cell A"
    row.cells = [c1]
    table.rows = [row]
    mock_doc.tables = [table]

    with patch.dict("sys.modules", {"docx": MagicMock(Document=MagicMock(return_value=mock_doc))}):
        docx_res_pydocx = s.read_file_text_sample(str(docx_file))
        assert "Python Docx Paragraph" in docx_res_pydocx
        assert "Cell A" in docx_res_pydocx

    # DOCX corrupt zip exception
    corrupt_docx = tmp_path / "corrupt.docx"
    corrupt_docx.write_bytes(b"PK\x03\x04corruptedbytes")
    assert s.read_file_text_sample(str(corrupt_docx)) is None

    # 7. Binary check: files containing \x00 or unparsed PK archives
    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"some\x00binary\x00data")
    assert s.read_file_text_sample(str(bin_file)) is None

    # 8. Plain text decoding error fallback
    bad_utf8 = tmp_path / "bad.txt"
    bad_utf8.write_bytes(b"\xff\xfe\x00\x00")
    assert s.read_file_text_sample(str(bad_utf8)) is None

def test_read_file_text_sample_from_gcs():
    s = StorageService()
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    s.client = mock_client

    # GCS download success
    mock_blob.download_as_bytes.return_value = b"Text downloaded from GCS bucket."
    text = s.read_file_text_sample("uploads/user/doc.txt")
    assert text == "Text downloaded from GCS bucket."

    # GCS download exception
    mock_blob.download_as_bytes.side_effect = Exception("GCS error")
    assert s.read_file_text_sample("uploads/user/doc.txt") is None

def test_storage_service_edge_cases(tmp_path):
    s = StorageService()
    # 1. _ensure_bucket when client is None
    s.client = None
    assert s._ensure_bucket() is None

    # 2. File read error on local file
    unreadable_file = tmp_path / "unreadable.txt"
    unreadable_file.write_text("content", encoding="utf-8")
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        assert s.read_file_text_sample(str(unreadable_file)) is None

    # 3. Plain text decode exception (line 190-191)
    mock_bytes = MagicMock()
    mock_bytes.startswith.return_value = False
    mock_bytes.__getitem__.return_value = b"normal"
    mock_bytes.__contains__.return_value = False
    mock_bytes.decode.side_effect = Exception("Decode crashed")
    with patch("builtins.open", mock_open_bytes := MagicMock()):
        mock_file = MagicMock()
        mock_file.read.return_value = mock_bytes
        mock_open_bytes.return_value.__enter__.return_value = mock_file
        assert s.read_file_text_sample(str(unreadable_file)) is None

    # 4. Whitespace-only file (line 189)
    whitespace_file = tmp_path / "whitespace.txt"
    whitespace_file.write_text("   \n\t  \n  ", encoding="utf-8")
    assert s.read_file_text_sample(str(whitespace_file)) is None

def test_storage_service_multimodal_and_bytes(tmp_path):
    s = StorageService()
    # 1. get_file_bytes with None/empty path
    assert s.get_file_bytes(None) is None
    assert s.get_file_bytes("") is None

    # 2. _extract_text_via_gemini_multimodal success
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Extracted OCR Contract Text"
    mock_client.models.generate_content.return_value = mock_resp
    with patch("google.genai.Client", return_value=mock_client):
        ocr_result = s._extract_text_via_gemini_multimodal(b"fake pdf bytes", "application/pdf")
        assert ocr_result == "Extracted OCR Contract Text"

    # 3. _extract_text_via_gemini_multimodal exception
    with patch("google.genai.Client", side_effect=Exception("GenAI unavailable")):
        assert s._extract_text_via_gemini_multimodal(b"bytes", "application/pdf") is None

    # 4. read_file_text_sample with image (PNG / JPEG) using multimodal OCR
    img_file = tmp_path / "scan.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\nfake image data")
    with patch.object(s, "_extract_text_via_gemini_multimodal", return_value="Scanned Invoice Text") as mock_ocr:
        res = s.read_file_text_sample(str(img_file))
        assert res == "Scanned Invoice Text"
        mock_ocr.assert_called_once()

    # 5. Scanned PDF fallback (pypdf returns empty string, gemini OCR succeeds)
    scan_pdf = tmp_path / "scan.pdf"
    scan_pdf.write_bytes(b"%PDF-1.4 empty text")
    with patch("pypdf.PdfReader") as mock_pdf_reader:
        mock_reader_inst = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader_inst.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_inst
        with patch.object(s, "_extract_text_via_gemini_multimodal", return_value="Scanned PDF Page 1 Terms"):
            pdf_res = s.read_file_text_sample(str(scan_pdf))
            assert pdf_res == "Scanned PDF Page 1 Terms"
