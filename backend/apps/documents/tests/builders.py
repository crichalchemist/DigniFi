"""Synthetic uploads and model replies for document tests.

Every value here is invented. Nothing is a real person, account or creditor.
"""

import fitz  # pymupdf
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice


def text_pdf(pages: list[str], letterhead: str = "") -> bytes:
    """A PDF with a real text layer, one page per string. A letterhead, when given, is
    printed small at the top of every page, where a bill puts the creditor's name."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if letterhead:
            page.insert_text((72, 30), letterhead, fontsize=9)
        page.insert_text((72, 200), text, fontsize=11)
    return doc.tobytes()


def scanned_pdf(page_sizes: list[tuple[int, int]]) -> bytes:
    """An image-only PDF, like a phone scan: one page per (width, height) in points,
    each covered by a picture and carrying no text layer."""
    doc = fitz.open()
    for shade, (width, height) in enumerate(page_sizes):
        picture = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), False)
        picture.clear_with(40 + 50 * shade)
        page = doc.new_page(width=width, height=height)
        page.insert_image(page.rect, pixmap=picture)
    return doc.tobytes()


def pdf_with_no_pages() -> bytes:
    """A well-formed PDF whose page tree is empty. Written by hand, because pymupdf
    refuses to save a document with no pages."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
        b"%%EOF\n"
    )


def chat_completion(
    content: str | None, *, finish_reason: str = "stop", refusal: str | None = None
) -> ChatCompletion:
    """What openai's chat.completions.create returns, built from the SDK's own types so
    a test cannot read an attribute the real reply lacks."""
    return ChatCompletion(
        id="chatcmpl-test",
        object="chat.completion",
        created=0,
        model="gpt-4o",
        choices=[
            Choice(
                index=0,
                finish_reason=finish_reason,
                message=ChatCompletionMessage(role="assistant", content=content, refusal=refusal),
            )
        ],
    )
