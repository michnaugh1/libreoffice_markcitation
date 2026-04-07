"""
Citation data model and document property storage.

All TOA data lives as a single JSON blob in the document's user-defined
properties under the key 'TOA_DATA'. The blob travels with the .odt file
automatically — no sidecar files, no external database.

Schema:
{
  "citations": {
    "<32-char hex uuid>": {
      "long_form":  "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "short_form": "Brown v. Board of Education",
      "category":   "Cases"
    },
    ...
  },
  "custom_categories": ["Treatises"],
  "highlights_on": true,
  "passim_threshold": 5
}

Each citation ID is also the suffix of a LibreOffice Bookmark named
"TOA_<id>", which anchors the mark to its location in the document.
"""

import json
import uuid
from com.sun.star.beans.PropertyAttribute import REMOVEABLE as PROP_REMOVEABLE

PROP_KEY = "TOA_DATA"
BOOKMARK_PREFIX = "TOA_"

# Standard legal TOA categories, in the conventional order they appear in
# court briefs and appellate submissions.
DEFAULT_CATEGORIES = [
    "Cases",
    "Constitutional Provisions",
    "Statutes",
    "Regulations",
    "Rules",
    "Other Authorities",
]

DEFAULT_PASSIM_THRESHOLD = 5

_EMPTY_DATA = {
    "citations": {},
    "custom_categories": [],
    "highlights_on": True,
    "passim_threshold": DEFAULT_PASSIM_THRESHOLD,
}


def load(doc):
    """
    Load TOA data from the document's user-defined properties.
    Returns a dict matching the schema above; never raises.
    """
    props = doc.getDocumentProperties().getUserDefinedProperties()
    prop_info = props.getPropertySetInfo()
    if not prop_info.hasPropertyByName(PROP_KEY):
        return dict(_EMPTY_DATA)
    try:
        raw = props.getPropertyValue(PROP_KEY)
        data = json.loads(raw)
        # Forward-compat: ensure all top-level keys exist
        for key, default in _EMPTY_DATA.items():
            data.setdefault(key, default)
        return data
    except Exception:
        return dict(_EMPTY_DATA)


def save(doc, data):
    """
    Persist TOA data to the document's user-defined properties.
    Creates the property on first save; updates it thereafter.
    """
    props = doc.getDocumentProperties().getUserDefinedProperties()
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    prop_info = props.getPropertySetInfo()
    if prop_info.hasPropertyByName(PROP_KEY):
        props.setPropertyValue(PROP_KEY, raw)
    else:
        props.addProperty(PROP_KEY, PROP_REMOVEABLE, raw)


def all_categories(data):
    """Full ordered category list: standard + any user-defined ones."""
    return list(DEFAULT_CATEGORIES) + list(data.get("custom_categories", []))


def new_id():
    """Generate a unique citation ID (32-char hex, no dashes)."""
    return uuid.uuid4().hex


def bookmark_name(citation_id):
    return f"{BOOKMARK_PREFIX}{citation_id}"


def citation_id_from_bookmark(name):
    """Return the citation ID embedded in a bookmark name, or None."""
    if name.startswith(BOOKMARK_PREFIX):
        return name[len(BOOKMARK_PREFIX):]
    return None
