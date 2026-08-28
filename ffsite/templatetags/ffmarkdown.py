"""Template filter for rendering Markdown descriptions as sanitized HTML.

Replaces the ``django-markdownify`` package (and its ``bleach`` dependency) with
a small custom filter built on top of ``markdown`` + ``nh3``.
"""
import markdown as md
import nh3

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


ALLOWED_TAGS = {
    "a", "abbr", "acronym", "b", "blockquote", "br", "code",
    "em", "i", "li", "ol", "p", "strong", "ul",
    "h1", "h2", "h3", "h4", "h5", "h6", "pre", "hr",
}

ALLOWED_ATTRS = {"a": {"href", "title"}}


@register.filter
def ffmarkdown(value):
    """Render Markdown text as sanitized HTML."""
    if not value:
        return ""
    html = md.markdown(str(value), extensions=["fenced_code", "tables"])
    clean = nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    return mark_safe(clean)
