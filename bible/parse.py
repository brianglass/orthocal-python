import re

from xml.dom import pulldom

space_re = re.compile(r'\s+')

def parse_usfx(filename, language=None):
    book, chapter, verse = None, None, None
    paragraph_start = False
    is_valid_content = False
    content = ''
    language_override = bool(language)

    def finish_content():
        nonlocal book, chapter, verse, content, is_valid_content, paragraph_start
        result = {
            'language': language,
            'book': book,
            'chapter': chapter,
            'verse': verse,
            'content': space_re.sub(' ', content.strip()),
            'paragraph_start': paragraph_start,
        }
        is_valid_content = False
        paragraph_start = False
        content = ''
        return result

    for event, node in pulldom.parse(filename):
        match [event, node.nodeName]:
            # Language element
            case [pulldom.START_ELEMENT, 'languageCode']:
                is_valid_content = True
            case [pulldom.END_ELEMENT, 'languageCode']:
                if not language_override:
                    language = content

                content = ''
                is_valid_content = False

            # Book element
            case [pulldom.START_ELEMENT, 'book']:
                if is_valid_content:
                    yield finish_content()

                book = node.getAttribute('id')

            # Chapter element
            case [pulldom.START_ELEMENT, 'c']:
                if is_valid_content:
                    yield finish_content()

                chapter = node.getAttribute('id')

            # Verse elements
            case [pulldom.START_ELEMENT, 'v']:
                if is_valid_content:
                    yield finish_content()

                verse = node.getAttribute('id')
                is_valid_content = True
            case [pulldom.START_ELEMENT, 've']:
                yield finish_content()

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
                    if text := node.wholeText.replace('\n',' ').replace('¶',''):
                        content += text
