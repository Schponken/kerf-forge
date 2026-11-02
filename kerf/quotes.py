"""Validate researched options before Studio presents them or starts a design."""
from __future__ import annotations

import math
from urllib.parse import urlsplit


def validate(quote: dict, *, scenario: bool = False) -> dict:
    """Old architecture quotes remain readable; scenario quotes carry the decision evidence."""
    if not isinstance(quote, dict):
        raise ValueError("the quote must be an object")
    scenario = scenario or quote.get("request_kind") == "scenario"
    options = quote.get("options")
    if not isinstance(options, list) or not (2 if scenario else 1) <= len(options) <= 3:
        raise ValueError(f"the quote has no options (expected {'2-3' if scenario else '1-3'})")

    def text(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} needs an explanation")

    def strings(value, label, required=False):
        if not isinstance(value, list) or (required and not value):
            raise ValueError(f"{label} must be a list{' with at least one entry' if required else ''}")
        for entry in value:
            text(entry, label)

    for option in options:
        if not isinstance(option, dict):
            raise ValueError("each quote option must be an object")
        for field in ("title", "summary"):
            text(option.get(field), f"quote option {field}")
        for field in ("parts_printed", "cost_usd", "print_hours"):
            value = option.get(field)
            if scenario and field != "parts_printed" and field in option and value is None:
                text(option.get("cost_note" if field == "cost_usd" else "print_note"), field)
                continue
            try:
                valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"quote option '{option['title']}' needs a non-negative finite {field}")
            if field == "parts_printed" and int(value) != value:
                raise ValueError("parts_printed must be a whole number")
        for field in ("risks", "next_steps"):
            if scenario or field in option:
                strings(option.get(field), field, required=scenario)
        if "purchased" in option:
            if not isinstance(option["purchased"], list):
                raise ValueError("purchased parts must be a list")
            for part in option["purchased"]:
                if not isinstance(part, dict):
                    raise ValueError("each purchased part needs a catalog key and quantity")
                text(part.get("key"), "purchased part key")
                quantity = part.get("qty", 1)
                if type(quantity) is not int or quantity < 1:
                    raise ValueError("purchased part quantity must be a positive whole number")
        if scenario:
            if option.get("route") not in ("buy", "adapt", "build"):
                raise ValueError("scenario options need a buy, adapt or build route")
            for field in ("fit", "effort", "cost_note", "print_note"):
                text(option.get(field), field)
            if option["route"] == "buy" and (option["parts_printed"] != 0 or option["print_hours"] != 0):
                raise ValueError("a buy-only option cannot include printing; use adapt for a printed addition")
        sources = option.get("sources", [])
        if not isinstance(sources, list) or (scenario and not sources):
            raise ValueError("scenario options need research sources")
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("each source needs a title, URL and finding")
            for field in ("title", "url", "finding"):
                text(source.get(field), f"source {field}")
            try:
                parsed = urlsplit(source["url"])
                valid = parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password
            except ValueError:
                valid = False
            if not valid or any(ord(c) < 33 for c in source["url"]):
                raise ValueError("source URL must be an HTTP(S) page without credentials or whitespace")
    if scenario:
        routes = {option["route"] for option in options}
        if "buy" not in routes or not routes.intersection({"adapt", "build"}):
            raise ValueError("compare a buy option with an adapt or build option")
        text(quote.get("recommendation_reason"), "recommendation reason")
    if scenario or "recommended" in quote:
        recommended = quote.get("recommended")
        if type(recommended) is not int or not 0 <= recommended < len(options):
            raise ValueError("recommended must name an option by its zero-based index")
    for field in ("assumptions", "questions"):
        if field in quote:
            strings(quote[field], field)
    return quote
