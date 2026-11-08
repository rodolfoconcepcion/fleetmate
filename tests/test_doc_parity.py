import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Extensible registry of active target languages for multilingual documentation
SUPPORTED_LANGUAGES = ["es"]

# Markdown files subject to multilingual parity enforcement
CORE_DOC_PATTERNS = ["*.md", "docs/*.md"]


def get_base_markdown_files() -> list[Path]:
    """Return all primary (English) markdown documentation files."""
    base_files = []
    for pattern in CORE_DOC_PATTERNS:
        for file in REPO_ROOT.glob(pattern):
            # Skip language-specific files (*.<lang>.md) and hidden files
            if file.name.startswith(".") or any(
                file.name.endswith(f".{lang}.md") for lang in SUPPORTED_LANGUAGES
            ):
                continue
            base_files.append(file)
    return sorted(base_files)


def test_documentation_file_parity():
    """Ensure every primary documentation file has a matching counterpart in all supported languages."""
    base_files = get_base_markdown_files()
    assert len(base_files) > 0, "No base documentation files discovered."

    missing = []
    for base_file in base_files:
        for lang in SUPPORTED_LANGUAGES:
            target_file = base_file.parent / f"{base_file.stem}.{lang}.md"
            if not target_file.exists():
                missing.append(
                    f"{target_file.relative_to(REPO_ROOT)} (counterpart to {base_file.relative_to(REPO_ROOT)})"
                )

    assert not missing, "Missing multilingual documentation files:\n" + "\n".join(
        f"  - {m}" for m in missing
    )


def test_changelog_version_parity():
    """Ensure all version releases documented in CHANGELOG.md are mirrored across all language changelogs."""
    en_changelog = REPO_ROOT / "CHANGELOG.md"
    assert en_changelog.exists(), "Primary CHANGELOG.md not found."
    en_versions = set(
        re.findall(r"^##\s+\[(.*?)\]", en_changelog.read_text(encoding="utf-8"), re.MULTILINE)
    )

    for lang in SUPPORTED_LANGUAGES:
        lang_changelog = REPO_ROOT / f"CHANGELOG.{lang}.md"
        assert lang_changelog.exists(), f"CHANGELOG.{lang}.md does not exist."
        lang_versions = set(
            re.findall(r"^##\s+\[(.*?)\]", lang_changelog.read_text(encoding="utf-8"), re.MULTILINE)
        )
        missing_versions = en_versions - lang_versions
        assert not missing_versions, (
            f"CHANGELOG.{lang}.md is missing release versions: {missing_versions}"
        )


def test_language_switcher_navigation():
    """Ensure key root documents contain bilingual navigation links at the top."""
    bilingual_docs = ["README", "CHANGELOG", "ROADMAP", "CONTRIBUTING", "SECURITY"]
    missing_switcher = []

    for name in bilingual_docs:
        en_file = REPO_ROOT / f"{name}.md"
        es_file = REPO_ROOT / f"{name}.es.md"

        if en_file.exists():
            content = en_file.read_text(encoding="utf-8")[:1000]
            if f"[Español]({name}.es.md)" not in content and "[Español]" not in content:
                missing_switcher.append(str(en_file.relative_to(REPO_ROOT)))

        if es_file.exists():
            content = es_file.read_text(encoding="utf-8")[:1000]
            if f"[English]({name}.md)" not in content and "[English]" not in content:
                missing_switcher.append(str(es_file.relative_to(REPO_ROOT)))

    assert not missing_switcher, "Documents missing language navigation links:\n" + "\n".join(
        f"  - {m}" for m in missing_switcher
    )
