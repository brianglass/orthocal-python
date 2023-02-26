import string

from xml.dom import pulldom


def parse_usfx(filename):
    language, book, chapter, verse = None, None, None, None
    is_valid_content = False
    content = ''

    for event, node in pulldom.parse(filename):
        match [event, node.nodeName]:
            # Language element
            case [pulldom.START_ELEMENT, 'languageCode']:
                is_valid_content = True
            case [pulldom.END_ELEMENT, 'languageCode']:
                language = content
                content = ''
                is_valid_content = False

            # Book element
            case [pulldom.START_ELEMENT, 'book']:
                book = node.getAttribute('id')

            # Chapter element
            case [pulldom.START_ELEMENT, 'c']:
                chapter = node.getAttribute('id')

            # Verse elements
            case [pulldom.START_ELEMENT, 'v']:
                verse = node.getAttribute('id')
                is_valid_content = True
            case [pulldom.START_ELEMENT, 've']:
                yield {
                    'language': language,
                    'book': book,
                    'chapter': chapter,
                    'verse': verse,
                    'content': content,
                }
                is_valid_content = False
                content = ''

            # Footnote Element
            case [pulldom.START_ELEMENT, 'f']:
                is_valid_content = False
            case [pulldom.END_ELEMENT, 'f']:
                is_valid_content = True

            # Character content
            case [pulldom.CHARACTERS, _]:
                if is_valid_content:
                    if text := node.wholeText.replace('¶','').strip():
                        if text[0] in string.punctuation or content.endswith('(') or not content:
                            content += text
                        else:
                            content += ' ' + text
