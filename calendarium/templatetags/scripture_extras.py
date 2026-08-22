import re

from django import template

register = template.Library()


@register.filter
def keep_numeral_with_book(value):
    """Bible references starting with a numeral (e.g. "1 Corinthians",
    "2 Kings") read badly if a line wraps right after that numeral,
    leaving it dangling alone -- joins it to the next word with a
    non-breaking space so only the reference's other spaces stay
    wrappable."""
    return re.sub(r'^(\d+)\s+', '\\1\N{NO-BREAK SPACE}', str(value), count=1)
