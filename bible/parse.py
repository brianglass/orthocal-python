import re

from xml.dom import pulldom

space_re = re.compile(r'\s+', flags=re.DOTALL)

def parse_usfx(filename):
    book, chapter, verse = None, None, None
    paragraph_start = False
    is_valid_content = False
    strings = []

    def make_verse():
        nonlocal is_valid_content, paragraph_start

        content = ''.join(strings)
        content = space_re.sub(' ', content)

        # Older printings of the KJV started each verse on a new
        # line and used a paragraph symbol to indicate the
        # paragraph breaks. The <p> elements don't seem to quite
        # line up with them. We strip the paragraph symbols since
        # we are using the <p> elements.
        content = content.replace('¶','').strip()

        result = {
            'book': book,
            'chapter': chapter,
            'verse': verse,
            'content': content,
            'paragraph_start': paragraph_start,
        }

        strings.clear()
        is_valid_content = False
        paragraph_start = False

        return result

    for event, node in pulldom.parse(filename):
        match [event, node.nodeName]:
            # Book element
            case [pulldom.START_ELEMENT, 'book']:
                if is_valid_content:
                    yield make_verse()

                book = node.getAttribute('id')

            # Chapter element
            case [pulldom.START_ELEMENT, 'c']:
                if is_valid_content:
                    yield make_verse()

                chapter = node.getAttribute('id')

            # Verse elements
            case [pulldom.START_ELEMENT, 'v']:
                if is_valid_content:
                    yield make_verse()

                verse = node.getAttribute('id')
                is_valid_content = True
            case [pulldom.START_ELEMENT, 've']:
                yield make_verse()

            # paragraph element
            case [pulldom.START_ELEMENT, 'p']:
                paragraph_start = True

            # Footnote Element
            case [pulldom.START_ELEMENT, 'f']:
                is_valid_content = False
            case [pulldom.END_ELEMENT, 'f']:
                is_valid_content = True

            # Character content
            case [pulldom.CHARACTERS, _]:
                if is_valid_content:
                    strings.append(node.wholeText)
