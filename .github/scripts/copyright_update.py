"""Update copyright year in license notice."""

from dataclasses import dataclass
from pathlib import Path
import re

from CPAC.utils.typing import PATHSTR

COMMENTS = {"Python": "#"}
LOADED_TEMPLATE: str = ""


@dataclass
class CopyrightYear:
    """Store and display a single year or range of years."""

    created: int
    last_modified: int

    def __str__(self):
        """Represent copyright year(s) as a string."""
        if self.created == self.last_modified:
            return str(self.last_modified)
        return f"{self.created}-{self.last_modified}"


@dataclass
class Notice:
    """Store a notice and its containing file."""

    contents: str
    language: str
    notice: str
    path: Path
    template: Path

    def generate_notice(self, copyright_date: CopyrightYear) -> str:
        """Insert copyright date in template."""
        return "\n".join(
            [
                f"{COMMENTS.get(self.language)} {line}" if line else line
                for line in load_template(self.template)
                .format(copyright_year=str(copyright_date))
                .split("\n")
            ]
        )

    def update_year(self, year: CopyrightYear) -> None:
        """Update the year (or year range) in a license notice.

        This update is written directly to file.
        """
        with self.path.open("w", encoding="utf8") as _file:
            _file.write(self.contents.replace(self.notice, self.generate_notice(year)))


def find_notice(fp: PATHSTR, template: PATHSTR, language: str) -> Notice:
    """Find a license notice in a file."""
    fp = Path(fp)
    template = Path(template)
    with open(fp, "r", encoding="utf8") as _fp:
        contents = _fp.read()

    _regex = load_template(template)
    regex = rf"\s*{COMMENTS.get(language)}?\s*"
    rlines = _regex.split("\n")
    for symbol in [".", "(", ")", "<", ">"]:
        rlines[0] = rlines[0].replace(symbol, rf"\{symbol}")
        rlines[-1] = rlines[-1].replace(symbol, rf"\{symbol}")
    rlines[0] = re.sub(
        r"\s*{copyright_year}\s*", r"\\s*(\\d{4})(\\s*-\\s*\\d{4})?\\s*", rlines[0]
    )
    regex = f"{regex}.*{rlines[0]}.*{rlines[-1]}"
    match = re.search(regex.replace(".*.*", ".*"), contents, re.DOTALL)
    if match:
        return Notice(
            contents=contents,
            language=language,
            notice=match.group(),
            path=fp,
            template=template,
        )
    msg = "No match found"
    raise LookupError(msg)


def load_template(template: PATHSTR) -> str:
    """Load a template and memoize it."""
    global LOADED_TEMPLATE  # noqa: PLW0603
    if not LOADED_TEMPLATE:
        with open(template, "r", encoding="utf8") as _template:
            LOADED_TEMPLATE = _template.read()
    return LOADED_TEMPLATE
