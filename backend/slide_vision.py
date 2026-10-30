"""
backend/slide_vision.py

강의자료(PPT/PDF)를 슬라이드 이미지로 렌더링한 뒤 Claude Vision에게 보여줘서,
텍스트뿐 아니라 표/다이어그램/그래프 같은 시각 자료까지 상세한 텍스트로 옮겨 적게 한다.
PPTX는 LibreOffice(soffice)로 PDF로 변환한 다음, PDF 페이지를 PyMuPDF로 이미지化한다.

주의: 이 모듈을 쓰려면 LibreOffice가 설치되어 있어야 한다 (brew install --cask libreoffice).
설치가 안 되어 있으면 ValueError를 던지므로, 호출하는 쪽에서 text_extraction.py의 순수
텍스트 추출로 대체(fallback)하는 것을 권장한다.
"""

import base64
import os
import shutil
import subprocess
import tempfile

SOFFICE_CANDIDATES = [
    "soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/opt/homebrew/bin/soffice",
    "/usr/local/bin/soffice",
]


def _find_soffice():
    for candidate in SOFFICE_CANDIDATES:
        if shutil.which(candidate) or os.path.exists(candidate):
            return candidate
    return None


def _pptx_to_pdf_bytes(file_bytes: bytes) -> bytes:
    soffice = _find_soffice()
    if soffice is None:
        raise ValueError(
            "LibreOffice가 설치되어 있지 않아 PPT를 이미지로 변환할 수 없습니다. "
            "'brew install --cask libreoffice'로 설치해주세요."
        )

    with tempfile.TemporaryDirectory() as tmp_dir:
        pptx_path = os.path.join(tmp_dir, "input.pptx")
        with open(pptx_path, "wb") as f:
            f.write(file_bytes)

        result = subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", tmp_dir, pptx_path],
            capture_output=True,
            timeout=120,
        )
        pdf_path = os.path.join(tmp_dir, "input.pdf")
        if result.returncode != 0 or not os.path.exists(pdf_path):
            stderr = result.stderr.decode(errors="ignore")
            raise ValueError(f"PPT를 PDF로 변환하지 못했습니다: {stderr or '알 수 없는 오류'}")

        with open(pdf_path, "rb") as f:
            return f.read()


def _pdf_to_images(pdf_bytes: bytes, zoom: float = 1.5) -> list:
    import fitz  # PyMuPDF

    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images


def render_slides_to_images(filename: str, file_bytes: bytes) -> list:
    lower = filename.lower()
    if lower.endswith(".pptx"):
        pdf_bytes = _pptx_to_pdf_bytes(file_bytes)
        return _pdf_to_images(pdf_bytes)
    if lower.endswith(".pdf"):
        return _pdf_to_images(file_bytes)
    raise ValueError("지원하지 않는 파일 형식입니다. PDF 또는 PPTX 파일만 업로드해주세요.")


def describe_slides_with_vision(images: list, model: str = "claude-sonnet-5") -> str:
    from anthropic import Anthropic

    client = Anthropic()

    content = [
        {
            "type": "text",
            "text": (
                "아래는 강의자료 슬라이드 이미지들입니다. 각 슬라이드의 내용을 순서대로 "
                "빠짐없이 글로 옮겨 적으세요. 단순 텍스트뿐 아니라 표, 다이어그램, 그래프, "
                "회로도, 그림 같은 시각 자료도 그 안의 요소와 관계(화살표로 연결된 흐름, "
                "표의 각 셀 내용, 그래프의 축과 추세 등)까지 최대한 자세히 설명하세요. "
                "프로그래밍 코드가 있는 슬라이드는 절대 요약하지 말고, 들여쓰기와 문법 기호까지 "
                "한 글자도 빠짐없이 코드블록(```)으로 그대로 옮겨 적으세요. "
                "슬라이드마다 제목이 있으면 먼저 적고, '--- 슬라이드 N ---' 형식으로 "
                "구분해서 적으세요. 이미지에 실제로 없는 내용을 지어내지 마세요."
            ),
        }
    ]

    for img_bytes in images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                },
            }
        )

    response = client.messages.create(
        model=model,
        max_tokens=8000,
        messages=[{"role": "user", "content": content}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "\n".join(text_parts).strip()
