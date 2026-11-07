import re

from xml.parsers import expat

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

    # Driven by expat directly. pulldom, which this used before, builds a DOM
    # node and attribute objects for every element and text run, and that was
    # most of the time the image build spends loading the scriptures.
    verses = []

    def start_element(name, attributes):
        nonlocal book, chapter, verse, is_valid_content, was_valid_content, paragraph_start

        match name:
            # Book element
            case 'book':
                if is_valid_content:
                    verses.append(make_verse())

                book = attributes.get('id', '')

            # Chapter element
            case 'c':
                if is_valid_content:
                    verses.append(make_verse())

                chapter = attributes.get('id', '')

            # Verse elements
            case 'v':
                if is_valid_content:
                    verses.append(make_verse())

                verse = attributes.get('id', '')
                if verse and '-' in verse:
                    # A verse bridge (e.g. "1-2"), where the source merges
                    # two verses into one printed unit -- store it under the
                    # first number rather than failing to parse an int; the
                    # combined text is already all in this one entry.
                    verse = verse.split('-')[0]
                is_valid_content = True
            case 've':
                verses.append(make_verse())

            # paragraph element
            case 'p':
                paragraph_start = True

            # Footnote and cross-reference elements -- <x> (cross-reference,
            # e.g. WEB's "11:33 Daniel 6:22-23" pointing back to an OT
            # parallel) is structurally the same kind of aside as <f>
            # (footnote), so it needs the same is_valid_content suppression;
            # without it, the reference text gets appended straight into the
            # verse content.
            case 'f' | 'x':
                was_valid_content = is_valid_content
                is_valid_content = False

    def end_element(name):
        nonlocal is_valid_content

        if name in ('f', 'x'):
            # Restore whatever was in effect before the aside rather than
            # assuming True -- these can appear in content (like Psalm
            # title <d> blocks) that isn't part of a verse.
            is_valid_content = was_valid_content

    # Character content
    def character_data(data):
        if is_valid_content:
            strings.append(data)

    parser = expat.ParserCreate()
    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.CharacterDataHandler = character_data

    with open(filename, 'rb') as f:
        while chunk := f.read(1 << 16):
            parser.Parse(chunk, False)
            yield from verses
            verses.clear()

    parser.Parse(b'', True)
    yield from verses
