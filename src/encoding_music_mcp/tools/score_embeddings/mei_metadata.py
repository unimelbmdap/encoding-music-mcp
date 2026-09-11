"""Catalog metadata extraction for arbitrary MEI score files."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScoreCatalogMetadata:
    """Nullable catalog fields sourced from an MEI work description."""

    title: str | None
    artist: str | None
    work_created_date: str | None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [
        candidate for candidate in element.iter() if _local_name(candidate.tag) == name
    ]


def _text(element: ET.Element) -> str | None:
    value = " ".join("".join(element.itertext()).split())
    return value or None


def _unambiguous(values: list[str]) -> str | None:
    """Return one unique value, or null when values conflict or are absent."""
    unique = list(dict.fromkeys(values))
    return unique[0] if len(unique) == 1 else None


def _element_values(elements: list[ET.Element]) -> list[str]:
    return [value for element in elements if (value := _text(element)) is not None]


def _date_value(element: ET.Element) -> str | None:
    for attribute in ("isodate", "when"):
        if value := element.attrib.get(attribute, "").strip():
            return value
    if value := _text(element):
        return value
    start = element.attrib.get("notbefore", element.attrib.get("startdate", "")).strip()
    end = element.attrib.get("notafter", element.attrib.get("enddate", "")).strip()
    if start and end:
        return f"{start}/{end}"
    return start or end or None


def _work_artist_values(work: ET.Element) -> list[str]:
    values: list[str] = []
    for composer in _children(work, "composer"):
        people = _descendants(composer, "persName")
        if people:
            values.extend(_element_values(people))
        elif value := _text(composer):
            values.append(value)
    return values


def extract_mei_catalog_metadata(path: str | Path) -> ScoreCatalogMetadata:
    """Read catalog fields directly from an MEI file.

    Work-level metadata takes precedence over file-description fallbacks. A
    field is null when its selected source contains conflicting non-empty
    values. Publication dates are deliberately outside the creation-date
    search boundary.
    """
    root = ET.parse(Path(path)).getroot()
    mei_heads = _children(root, "meiHead")
    mei_head = mei_heads[0] if mei_heads else root
    work_lists = _children(mei_head, "workList")
    works = [work for work_list in work_lists for work in _children(work_list, "work")]

    work_titles = [
        value
        for work in works
        for title in _children(work, "title")
        if (value := _text(title)) is not None
    ]
    file_titles = [
        value
        for file_desc in _children(mei_head, "fileDesc")
        for title_stmt in _children(file_desc, "titleStmt")
        for title in _children(title_stmt, "title")
        if (value := _text(title)) is not None
    ]

    work_artists = [value for work in works for value in _work_artist_values(work)]
    file_artists = [
        value
        for file_desc in _children(mei_head, "fileDesc")
        for title_stmt in _children(file_desc, "titleStmt")
        for person in _descendants(title_stmt, "persName")
        if person.attrib.get("role", "").strip().lower() == "composer"
        if (value := _text(person)) is not None
    ]

    creation_dates = [
        value
        for work in works
        for creation in _children(work, "creation")
        for date in _descendants(creation, "date")
        if (value := _date_value(date)) is not None
    ]
    return ScoreCatalogMetadata(
        title=_unambiguous(work_titles or file_titles),
        artist=_unambiguous(work_artists or file_artists),
        work_created_date=_unambiguous(creation_dates),
    )
