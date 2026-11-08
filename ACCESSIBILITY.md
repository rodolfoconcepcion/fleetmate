# Accessibility Statement for FleetMate

FleetMate is committed to providing an accessible, inclusive, and transparent experience for all users and contributors, including developers using assistive technologies.

---

## Commitment

We strive to ensure that all interfaces, command-line utilities, documentation, and error reports are usable by everyone regardless of ability or operating environment.

---

## Supported Environments & Terminal Accessibility

FleetMate's primary interface is a command-line interface (CLI) and background daemon. We adhere to the following accessibility standards for terminal and developer tooling:

1. **High-Contrast Terminal Output**:
   - CLI output is styled using `rich` with colors chosen for readability across both dark and light terminal palettes.
   - Information conveyed through color is always paired with textual indicators (e.g., status labels `[OK]`, `[ERROR]`, `[WARN]`, or checkmarks) so users with color vision deficiencies can easily navigate output.
   - Supports `NO_COLOR` standard ([no-color.org](https://no-color.org/))—running with `NO_COLOR=1` strips ANSI color escape codes for clean screen reader consumption.

2. **Screen Reader Friendly CLI & Logs**:
   - Structured JSON logging mode (`LOG_FORMAT=json`) is provided for automated tooling and screen readers.
   - Tables and progress bars gracefully degrade to sequential text in non-interactive terminals (`TERM=dumb` or non-TTY pipes).

3. **Semantic & Readable Documentation**:
   - Documentation is written in semantic GitHub Flavored Markdown (GFM) with structured heading hierarchies (`#`, `##`, `###`).
   - All code snippets, CLI examples, and diagrams include descriptive captions and code fences.
   - Color is never used as the sole method of communicating information in tables or guides.

---

## Known Limitations

- **Complex Terminal Tables**: Dense ASCII/Unicode tables displayed during `fleetmate status` may require wide terminal viewports. Screen reader users can pass `--format json` or `--plain` to obtain linear text representations.
- **Architectural Flowcharts**: Graphical Mermaid diagrams in documentation are accompanied by text descriptions, but external SVG renders may have varying screen reader support.

---

## Feedback & Reporting Barriers

We welcome your feedback on the accessibility of FleetMate. If you encounter accessibility barriers, difficult-to-parse terminal output, or have suggestions for improvements:

- **Discussions**: [GitHub Discussions](https://github.com/rodolfoconcepcion/fleetmate/discussions) (Category: `Ideas` or `General`)
- **GitHub Issues**: Open an issue on [GitHub Issues](https://github.com/rodolfoconcepcion/fleetmate/issues) detailing the barrier and the assistive technology used.

We aim to respond to accessibility reports within 2 business days.
