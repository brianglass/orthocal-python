import functools
import operator
import re

from django.db import models
from django.db.models import Q

from . import books

ref_re   = re.compile('(?:([\w\s]+)\s+)?(\d.*)')
# matches patterns like 26:40-27:2. In this example, group 1 is 26, group 2 is
# 40, group 3 is 27, and group 4 is 2.
range_re = re.compile('(?:(\d+)[\.:])?(\d+)(?:-(?:(\d+)[\.:])?(\d+))?')


class ReferenceParseError(Exception):
    pass


class VerseManager(models.Manager):
    def lookup_reference(self, reference):
        conditionals = []
        book = ''

        for passage in re.split('\s*;\s*', reference):
            m = ref_re.match(passage)
            book_abbreviation, specification = m.groups()
            if book_abbreviation:
                book = books.normalize_book_name(book_abbreviation)

            previous_chapter = ''
            for verse_range in re.split(',\s*', specification):
                chapter = ''

                m = range_re.match(verse_range)

                first_chapter, first_verse, last_chapter, last_verse = m.groups()

                if books.is_chapterless(book):
                    first_chapter = 1

                if not first_chapter:
                    first_chapter = previous_chapter

                if not first_chapter:
                    # If we specify a full chapter, the regex puts the chapter
                    # in group 2 instead of group 1.
                    first_chapter, first_verse = first_verse, first_chapter

                if last_verse:
                    if last_chapter and last_chapter != first_chapter:
                        # Handle ranges that span chapters
                        conditional = Q(book=book) & (
                                (Q(chapter=first_chapter) & Q(verse__gte=first_verse)) |
                                (Q(chapter__gt=first_chapter) & Q(chapter__lt=last_chapter)) |
                                (Q(chapter=last_chapter) & Q(verse__lte=last_verse))
                        )
                    else:
                        # Handle ranges that are contained within a single chapter
                        conditional = Q(book=book) & Q(chapter=first_chapter) & Q(verse__gte=first_verse) & Q(verse__lte=last_verse)

                elif first_verse:
                    # Handle a single verse
                    conditional = Q(book=book) & Q(chapter=first_chapter) & Q(verse=first_verse)
                else:
                    # Handle full chapters
                    conditional = Q(book=book) & Q(chapter=first_chapter)

                conditionals.append(conditional)

                # Remember the most recently used chapter, unless it was a full chapter.
                # If it was a full chapter, it can't be reused in a subsequent range.
                if last_chapter:
                    previous_chapter = last_chapter
                elif first_verse:
                    previous_chapter = first_chapter

        expression = functools.reduce(operator.or_, conditionals)
        return self.filter(expression)


class Verse(models.Model):
    book = models.CharField(max_length=3)
    chapter = models.IntegerField()
    verse = models.IntegerField()
    content = models.TextField()
    language = models.CharField(max_length=10)

    objects = VerseManager()

    class Meta:
        unique_together = 'book', 'chapter', 'verse', 'language'
        index_together = 'book', 'chapter', 'verse', 'language'

    def __str__(self):
        return f'{self.book} {self.chapter}:{self.verse}'
