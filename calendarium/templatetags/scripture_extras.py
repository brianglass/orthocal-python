import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def keep_numeral_with_book(value):
    """Bible references starting with a numeral (e.g. "1 Corinthians",
    "2 Kings") read badly if a line wraps right after that numeral,
    leaving it dangling alone -- joins it to the next word with a
    non-breaking space so only the reference's other spaces stay
    wrappable."""
    return re.sub(r'^(\d+)\s+', '\\1\N{NO-BREAK SPACE}', str(value), count=1)


PLURAL_YOU_MARKER = '\N{UP ARROWHEAD}'


@register.filter
def mark_plural_you(value):
    """LXX2012's own front matter documents that it marks 2nd-person
    *plural* "you" (translating "ye") with a trailing U+2303 (UP
    ARROWHEAD) -- modern English has no distinct plural "you", and this
    is the translator's deliberate substitute, not a stray artifact. The
    bare glyph reads as a rendering bug to anyone who doesn't already
    know the convention, so render it as a small, legible superscript
    instead. Escapes first so only our own hardcoded replacement HTML is
    ever trusted -- the source text itself never contains markup."""
    escaped = escape(str(value))
    marked = escaped.replace(
        PLURAL_YOU_MARKER,
        '<sup class="plural-you" title="plural &ldquo;you&rdquo; (translates &ldquo;ye&rdquo;)">pl</sup>',
    )
    return mark_safe(marked)
