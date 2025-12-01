"""HTML templates for the Markdown Analysis Service test UI."""

from .styles import STYLES
from .scripts import SCRIPTS
from .layout import LAYOUT

__all__ = ["STYLES", "SCRIPTS", "LAYOUT", "build_html_page"]


def build_html_page() -> str:
    """Build the complete HTML page from modular components."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markdown Analysis Service Test</title>
    <style>
{STYLES}
    </style>
</head>
<body>
{LAYOUT}
    <script>
{SCRIPTS}
    </script>
</body>
</html>
"""
