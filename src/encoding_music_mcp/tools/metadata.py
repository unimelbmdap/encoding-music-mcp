"""MEI metadata extraction tool."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

__all__ = ["get_mei_metadata"]


def get_mei_metadata(filename: str) -> dict[str, Any]:
    """Extract detailed metadata from built-in MEI files.

    Returns information including title, composer, editors, analysts,
    publication date, and more.

    Args:
        filename: Name of the MEI file (e.g., "Bartok_Mikrokosmos_001.mei")

    Returns:
        Dictionary containing metadata fields
    """
    # Convert filename to filepath
    resources_dir = Path(__file__).parent.parent / "resources"
    filepath = resources_dir / filename

    ns = {'mei': 'http://www.music-encoding.org/ns/mei'}
    tree = ET.parse(filepath)
    root = tree.getroot()

    metadata: dict[str, Any] = {
        'title': None,
        'composer': None,
        'mei_editors': [],
        'xml_editors': [],
        'analysts': [],
        'publication_date': None,
        'availability': None,
        'application': None,
        'work_title': None
    }

    # Title
    title = root.find('.//mei:titleStmt/mei:title', ns)
    if title is not None and title.text:
        metadata['title'] = title.text.strip()

    # People with roles
    people = root.findall('.//mei:titleStmt/mei:respStmt/mei:persName', ns)
    for person in people:
        role = person.attrib.get('role', '').lower()
        name = person.text.strip() if person.text else ''
        if role == 'composer':
            metadata['composer'] = name
        elif role == 'mei_editor':
            metadata['mei_editors'].append(name)
        elif role == 'xml_editor':
            metadata['xml_editors'].append(name)
        elif role == 'analyst':
            metadata['analysts'].append(name)

    # Publication date
    date = root.find('.//mei:pubStmt/mei:date', ns)
    if date is not None:
        metadata['publication_date'] = date.attrib.get('isodate', None)

    # Availability / copyright
    availability = root.find('.//mei:pubStmt/mei:availability', ns)
    if availability is not None and availability.text:
        metadata['availability'] = availability.text.strip()

    # Application name
    app_elem = root.find('.//mei:appInfo/mei:application/mei:name', ns)
    if app_elem is not None and app_elem.text:
        metadata['application'] = app_elem.text.strip()

    # Work title
    work_title = root.find('.//mei:workList/mei:work/mei:title', ns)
    if work_title is not None and work_title.text:
        metadata['work_title'] = work_title.text.strip()

    return metadata
