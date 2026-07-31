import re

from xml.dom import pulldom

space_re = re.compile(r'\s+', flags=re.DOTALL)

def parse_usfx(filename):
    book, chapter, verse = None, None, None
    paragraph_start = False
    is_valid_content = False
    was_valid_content = False
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
                if verse and '-' in verse:
                    # A verse bridge (e.g. "1-2"), where the source merges
                    # two verses into one printed unit -- store it under the
                    # first number rather than failing to parse an int; the
                    # combined text is already all in this one entry.
                    verse = verse.split('-')[0]
                is_valid_content = True
            case [pulldom.START_ELEMENT, 've']:
                yield make_verse()

            # paragraph element
            case [pulldom.START_ELEMENT, 'p']:
                paragraph_start = True

            # Footnote and cross-reference elements -- <x> (cross-reference,
            # e.g. WEB's "11:33 Daniel 6:22-23" pointing back to an OT
            # parallel) is structurally the same kind of aside as <f>
            # (footnote), so it needs the same is_valid_content suppression;
            # without it, the reference text gets appended straight into the
            # verse content.
            case [pulldom.START_ELEMENT, 'f' | 'x']:
                was_valid_content = is_valid_content
                is_valid_content = False
            case [pulldom.END_ELEMENT, 'f' | 'x']:
                # Restore whatever was in effect before the aside rather than
                # assuming True -- these can appear in content (like Psalm
                # title <d> blocks) that isn't part of a verse.
                is_valid_content = was_valid_content

            # Character content
            case [pulldom.CHARACTERS, _]:
                if is_valid_content:
                    strings.append(node.wholeText)
