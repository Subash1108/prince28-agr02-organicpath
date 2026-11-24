"""Turn one raw file into clean pages.

No database here: a file goes in, and either a ParsedDoc comes out or a ParseError
with a reason. Every page keeps its page number and the section path it starts in,
because answers will cite "document, page, section".
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
import trafilatura
from lxml import html as lxml_html
from pypdf import PdfReader

TEXT_TYPES = {".md", ".mdx", ".markdown", ".txt", ".rst", ".adoc", ".sgml", ".py"}
DATA_TYPES = {".json", ".yaml", ".yml", ".csv", ".xml"}
PAGE_CHARS = 3000  # files without real pages are cut into "pages" of about this size
MIN_CHARS_PER_PAGE = 50  # a PDF below this average has no text layer: it is a scan


@dataclass
class ParsedPage:
    page_no: int
    text: str  # clean text, headings as "# ..." lines, tables as Markdown
    headings: list[str] = field(default_factory=list)  # section path the page starts in
    tables: int = 0


@dataclass
class ParsedDoc:
    parser: str
    kind: str  # pdf, html, text or data
    title: str
    pages: list[ParsedPage]


class ParseError(Exception):
    """A file we could not parse, with a short machine-readable reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail[:500]


# ---------- cleaning ----------
def clean_text(text: str) -> str:
    """The same small repairs for every parser."""
    text = unicodedata.normalize("NFKC", text)
    # Repair common broken ligature and soft-hyphen sequences in extracted PDF text.
    text = text.replace("\u00ad", "")
    text = text.replace("\x00", "")  # NUL breaks Postgres.
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)  # "treat-\nment" -> "treatment"
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def drop_repeated_lines(pages: list[str]) -> list[str]:
    """Remove headers and footers: lines that open or close most pages."""
    if len(pages) < 4:
        return pages

    def key(line: str) -> str:
        return re.sub(r"\d+", "#", line.strip().lower())  # "Page 3 of 9" == "Page 4 of 9"

    seen: Counter[str] = Counter()
    for page in pages:
        lines = [ln for ln in page.splitlines() if ln.strip()]
        seen.update({key(ln) for ln in lines[:2] + lines[-2:] if not ln.startswith("#")})
    repeated = {k for k, count in seen.items() if count >= 0.6 * len(pages)}
    cleaned = []
    for page in pages:
        lines = page.splitlines()
        edge = {i for i, ln in enumerate(lines) if ln.strip()}
        edge = set(sorted(edge)[:2] + sorted(edge)[-2:])
        cleaned.append(
            "\n".join(ln for i, ln in enumerate(lines) if not (i in edge and key(ln) in repeated))
        )
    return cleaned


HEADING = re.compile(r"^(#{1,6}) +(.+?)\s*$")


def heading_title(raw: str) -> str:
    """ "First Steps { #first-steps }" -> "First Steps": some sites add anchors to headings."""
    return re.sub(r"\s*\{\s*[#.][^}]*\}\s*$", "", raw).strip()


FENCE = re.compile(r"^\s*(```|~~~)")


def headings_in(text: str, in_code: bool = False) -> tuple[list[tuple[int, str]], bool]:
    """(level, title) of each heading in the text. A "# comment" inside a code block is not one."""
    found = []
    for line in text.splitlines():
        if FENCE.match(line):
            in_code = not in_code
        elif not in_code and (match := HEADING.match(line)):
            found.append((len(match.group(1)), heading_title(match.group(2))))
    return found, in_code


def with_heading_paths(
    texts: list[str], include_leading_headings: bool = False
) -> list[ParsedPage]:
    """Number the pages and remember, for each one, which section it starts in."""
    pages, path, in_code = [], [], False
    for number, text in enumerate(texts, start=1):
        leading = []
        if include_leading_headings:
            for line in text.splitlines():
                if FENCE.match(line):
                    break
                if not line.strip():
                    continue
                if match := HEADING.match(line):
                    level = len(match.group(1))
                    title = heading_title(match.group(2))
                    leading.append((level, title))
                    path = path[: level - 1] + [title]
                    continue
                break
        pages.append(ParsedPage(number, text, headings=list(path), tables=text.count("\n|---")))
        found, in_code = headings_in(text, in_code)
        remaining = found[len(leading) :] if found[: len(leading)] == leading else found
        for level, title in remaining:
            path = path[: level - 1] + [title]
    return pages


def finish(
    parser: str,
    kind: str,
    title: str,
    texts: list[str],
    include_leading_headings: bool = False,
) -> ParsedDoc:
    texts = drop_repeated_lines([clean_text(t) for t in texts])
    texts = [clean_text(t) for t in texts]
    if not any(texts):
        raise ParseError("empty", "no text after cleaning")
    found, _ = headings_in("\n".join(texts))
    # A document's own first heading beats file metadata like "Microsoft Word - final2.docx"
    return ParsedDoc(
        parser,
        kind,
        found[0][1] if found else title,
        with_heading_paths(texts, include_leading_headings=include_leading_headings),
    )


# ---------- PDF, parser 1: PyMuPDF (fast, sees font sizes and tables) ----------
def _body_size(doc: pymupdf.Document) -> float:
    """The most common font size, counted by characters: that is the body text."""
    sizes: Counter[float] = Counter()
    for page in list(doc)[:30]:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    sizes[round(span["size"], 1)] += len(span["text"])
    return sizes.most_common(1)[0][0] if sizes else 10.0


def _heading_level(text: str, size: float, bold: bool, body: float) -> int:
    if not 2 < len(text) <= 120 or not any(ch.isalpha() for ch in text):
        return 0
    if size >= body * 1.6:
        return 1
    if size >= body * 1.3:
        return 2
    if size >= body * 1.12 or (bold and len(text) <= 80 and not text.endswith((".", ",", ";"))):
        return 3
    return 0


def _open_pdf(path: Path) -> pymupdf.Document:
    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # PyMuPDF raises several error types for broken files
        raise ParseError("corrupt", str(exc)) from exc
    if doc.needs_pass:
        raise ParseError("encrypted", "the PDF needs a password")
    if doc.page_count == 0:
        raise ParseError("empty", "the PDF has no pages")
    return doc


def parse_pdf_pymupdf(path: Path) -> ParsedDoc:
    doc = _open_pdf(path)
    body = _body_size(doc)
    texts, chars = [], 0
    for page in doc:
        # Looking for tables is slow, so only do it on pages that have ruled lines at all.
        tables = list(page.find_tables().tables) if len(page.get_cdrawings()) >= 4 else []
        used: set[int] = set()
        out: list[str] = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue  # an image
            rect = pymupdf.Rect(block["bbox"])
            inside = next((i for i, t in enumerate(tables) if rect.intersects(t.bbox)), None)
            if inside is not None:
                if inside not in used:  # write the whole table once, as Markdown
                    used.add(inside)
                    out.append("\n" + tables[inside].to_markdown().strip() + "\n")
                continue
            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                if not text:
                    continue
                size = max(span["size"] for span in line["spans"])
                bold = all(span["flags"] & 16 for span in line["spans"])
                level = _heading_level(text, size, bold, body)
                out.append(f"{'#' * level} {text}" if level else text)
                chars += len(text)
            out.append("")  # blank line between blocks
        texts.append("\n".join(out))
    if chars < MIN_CHARS_PER_PAGE * len(texts):
        raise ParseError("no_text_layer", f"{chars} characters on {len(texts)} pages: needs OCR")
    return finish("pymupdf", "pdf", (doc.metadata or {}).get("title") or "", texts)


def parse_pdf_ocr(path: Path, language: str = "eng") -> ParsedDoc:
    """For scans: read the pixels with Tesseract, which must be installed. Seconds per page."""
    doc = _open_pdf(path)
    try:
        texts = [
            page.get_text(textpage=page.get_textpage_ocr(language=language, dpi=200, full=True))
            for page in doc
        ]
    except Exception as exc:  # Tesseract or its language file is missing
        raise ParseError("ocr_unavailable", str(exc)) from exc
    return finish(f"ocr-{language}", "pdf", "", texts)


# ---------- PDF, parser 2: pypdf (pure Python, text only) ----------
def parse_pdf_pypdf(path: Path) -> ParsedDoc:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ParseError("encrypted", "the PDF needs a password")
        texts = [page.extract_text() or "" for page in reader.pages]
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError("corrupt", str(exc)) from exc
    if not texts:
        raise ParseError("empty", "the PDF has no pages")
    if sum(len(t) for t in texts) < MIN_CHARS_PER_PAGE * len(texts):
        raise ParseError("no_text_layer", f"almost no text on {len(texts)} pages: needs OCR")
    return finish("pypdf", "pdf", "", texts)


# ---------- HTML ----------
HIDDEN_CLASSES = {"visually-hidden", "visuallyhidden", "sr-only", "usa-sr-only", "d-none", "hidden"}


def _html_text(element) -> str:
    return " ".join(" ".join(element.itertext()).split())


def _is_hidden_or_chrome(element) -> bool:
    for ancestor in (element, *element.iterancestors()):
        classes = set((ancestor.get("class") or "").split())
        if (
            ancestor.tag in {"nav", "footer", "script", "style"}
            or "hidden" in ancestor.attrib
            or ancestor.get("aria-hidden", "").lower() == "true"
            or ancestor.get("role") == "navigation"
            or classes & HIDDEN_CLASSES
        ):
            return True
    return False


def _html_document_title(tree, markdown: str) -> str:
    candidates = [
        node for node in tree.xpath("//h1") if _html_text(node) and not _is_hidden_or_chrome(node)
    ]
    for node in candidates:
        if "universal-page-title" in (node.get("class") or "").split():
            return _html_text(node)

    markdown_titles = {title.casefold() for level, title in headings_in(markdown)[0] if level == 1}
    for node in reversed(candidates):
        title = _html_text(node)
        if title.casefold() in markdown_titles:
            return title
    return _html_text(candidates[-1]) if candidates else ""


def _promote_markdown_line(markdown: str, label: str, level: int) -> str:
    """Mark a source-backed heading when Trafilatura rendered it as plain or bold text."""
    lines = markdown.splitlines()
    wanted = label.casefold()
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = HEADING.match(stripped)
        if match and heading_title(match.group(2)).casefold() == wanted:
            return markdown
        if stripped in {label, f"**{label}**", f"_{label}_"}:
            lines[index] = f"{'#' * level} {label}"
            return "\n".join(lines)
        bold_label = f"**{label}**"
        if stripped.startswith(bold_label) and stripped[len(bold_label) :].startswith(" "):
            remainder = stripped[len(bold_label) :].strip()
            lines[index] = f"{'#' * level} {label}"
            if remainder:
                lines[index + 1 : index + 1] = ["", remainder]
            return "\n".join(lines)
    return markdown


def _html_section_labels(tree) -> list[tuple[str, int]]:
    """Find paragraph-leading bold labels, excluding inline bold values and prose."""
    labels = []
    heading_level = 1
    for paragraph in tree.xpath("//h1|//h2|//h3|//h4|//h5|//h6|//p"):
        if _is_hidden_or_chrome(paragraph):
            continue
        if paragraph.tag.startswith("h"):
            heading_level = int(paragraph.tag[1])
            continue
        if (paragraph.text or "").strip():
            continue
        first = next(
            (child for child in paragraph if isinstance(child.tag, str) and child.tag != "br"),
            None,
        )
        if first is None or first.tag not in {"strong", "b"}:
            continue
        label = _html_text(first)
        paragraph_text = _html_text(paragraph)
        remainder = paragraph_text[len(label) :].strip()
        words = label.split()
        if (
            not label
            or len(label) > 80
            or len(words) > 6
            or not any(char.isalpha() for char in label)
            or label.endswith((".", ",", ";", ":", "?", "!"))
        ):
            continue
        if remainder and len(remainder) < 40:
            continue
        if not remainder and not label.isupper():
            continue
        labels.append((label, min(heading_level + 1, 6)))
    return labels


def split_html_pages(text: str, size: int = PAGE_CHARS) -> list[str]:
    """Keep a new HTML section at a page boundary when the current page has body text."""
    pages, current, length = [], [], 0
    has_body = False
    for paragraph in re.split(r"\n\s*\n", text):
        is_heading = bool(re.fullmatch(r"\s*#{1,6} +.+?\s*", paragraph))
        if is_heading and current and has_body:
            pages.append("\n\n".join(current))
            current, length, has_body = [], 0, False
        if current and length + len(paragraph) > size:
            pages.append("\n\n".join(current))
            current, length, has_body = [], 0, False
        current.append(paragraph)
        length += len(paragraph)
        has_body = not is_heading
    if current:
        pages.append("\n\n".join(current))
    return pages


def normalize_html_heading_levels(text: str) -> str:
    """Collapse skipped source heading levels so section paths remain unambiguous."""
    lines, previous_source_level, previous_level, in_code = [], 0, 0, False
    for line in text.splitlines():
        if FENCE.match(line):
            in_code = not in_code
            lines.append(line)
            continue
        match = HEADING.match(line) if not in_code else None
        if match:
            source_level = len(match.group(1))
            if source_level > previous_source_level:
                level = min(source_level, previous_level + 1)
            else:
                level = min(source_level, previous_level)
            lines.append(f"{'#' * level} {match.group(2)}")
            previous_source_level = source_level
            previous_level = level
        else:
            lines.append(line)
    return "\n".join(lines)


def parse_html(path: Path) -> ParsedDoc:
    html = path.read_text(encoding="utf-8", errors="replace")
    tree = lxml_html.fromstring(html)
    # trafilatura keeps the article and drops menus, footers, scripts and cookie banners
    markdown = trafilatura.extract(html, output_format="markdown", include_tables=True)
    if not markdown or len(markdown) < 40:
        raise ParseError("empty", "no main content found (a page built by JavaScript?)")
    meta = trafilatura.extract_metadata(html)
    for heading in tree.xpath("//h2|//h3|//h4|//h5|//h6"):
        label = _html_text(heading)
        if label and not _is_hidden_or_chrome(heading):
            markdown = _promote_markdown_line(markdown, label, int(heading.tag[1]))
    for label, level in _html_section_labels(tree):
        markdown = _promote_markdown_line(markdown, label, level)

    title = _html_document_title(tree, markdown) or (meta.title if meta else "") or ""
    heading_titles = {name.casefold() for level, name in headings_in(markdown)[0] if level == 1}
    if title and title.casefold() not in heading_titles:
        markdown = f"# {title}\n\n{markdown}"
    markdown = normalize_html_heading_levels(markdown)
    return finish(
        "trafilatura",
        "html",
        title,
        split_html_pages(markdown),
        include_leading_headings=True,
    )


# ---------- text files ----------
RST_MARKS = {"=": 1, "-": 2, "~": 3, "^": 3, '"': 3}


def markup_to_markdown(text: str, suffix: str) -> str:
    """Rewrite reStructuredText and AsciiDoc headings as "# ..." so one rule finds them all."""
    lines = text.splitlines()
    if suffix == ".adoc":
        return "\n".join(
            re.sub(r"^(=+) ", lambda m: "#" * len(m.group(1)) + " ", ln) for ln in lines
        )
    if suffix not in {".rst", ".txt"}:
        return text
    out: list[str] = []
    for i, line in enumerate(lines):
        under = lines[i + 1] if i + 1 < len(lines) else ""
        is_rule = len(under) >= 3 and len(set(under)) == 1 and under[0] in RST_MARKS
        if line.strip() and is_rule and len(under) >= len(line.rstrip()):
            out.append("#" * RST_MARKS[under[0]] + " " + line.strip())
        elif not (out and len(line) >= 3 and len(set(line)) == 1 and line[0] in RST_MARKS):
            out.append(line)
    return "\n".join(out)


def split_pages(text: str, size: int = PAGE_CHARS) -> list[str]:
    """Cut on blank lines into pieces of about `size` characters."""
    pages, current, length = [], [], 0
    for para in re.split(r"\n\s*\n", text):
        if current and length + len(para) > size:
            pages.append("\n\n".join(current))
            current, length = [], 0
        current.append(para)
        length += len(para)
    if current:
        pages.append("\n\n".join(current))
    return pages


def parse_text(path: Path) -> ParsedDoc:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in DATA_TYPES:
        return finish("plain", "data", path.stem, split_pages(text))
    return finish("plain", "text", "", split_pages(markup_to_markdown(text, suffix)))


PDF_PARSERS = {"pymupdf": parse_pdf_pymupdf, "pypdf": parse_pdf_pypdf}


def parse_file(path: Path, pdf_parser: str = "pymupdf") -> ParsedDoc:
    """Pick the parser by file type. Raises ParseError, never anything else."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return PDF_PARSERS[pdf_parser](path)
        if suffix in {".html", ".htm"}:
            return parse_html(path)
        if suffix in TEXT_TYPES | DATA_TYPES:
            return parse_text(path)
    except ParseError:
        raise
    except Exception as exc:  # a parser bug must become a recorded failure, not a crash
        raise ParseError("crash", f"{type(exc).__name__}: {exc}") from exc
    raise ParseError("unsupported_type", suffix or "no file extension")
