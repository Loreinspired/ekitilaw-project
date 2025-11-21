"""
Test cases for laws models.

Tests cover:
- Model creation and string representation
- Model relationships and cascade deletion
- Ordering behavior
- Helper methods (URL generation, anchor tags)
- Unique constraints
"""

from django.test import TestCase
from django.db import IntegrityError
from laws.models import Law, Part, Chapter, Section, Schedule, Appendix


class LawModelTest(TestCase):
    """Tests for the Law model."""

    def test_law_creation(self):
        """Test creating a Law instance."""
        law = Law.objects.create(
            title="Test Law 2024",
            slug="test-law-2024",
            description="A test law description"
        )
        self.assertEqual(law.title, "Test Law 2024")
        self.assertEqual(law.slug, "test-law-2024")
        self.assertEqual(str(law), "Test Law 2024")

    def test_law_get_absolute_url(self):
        """Test Law.get_absolute_url() method."""
        law = Law.objects.create(title="Test Law", slug="test-law")
        url = law.get_absolute_url()
        self.assertEqual(url, "/laws/test-law/")

    def test_law_unique_slug(self):
        """Test that Law slug must be unique."""
        Law.objects.create(title="Law 1", slug="duplicate-slug")
        with self.assertRaises(IntegrityError):
            Law.objects.create(title="Law 2", slug="duplicate-slug")

    def test_law_cascade_delete_to_parts(self):
        """Test that deleting a Law cascades to Parts."""
        law = Law.objects.create(title="Test Law", slug="test-law")
        part = Part.objects.create(law=law, heading="Part 1")
        part_id = part.id

        law.delete()

        # Part should be deleted
        self.assertFalse(Part.objects.filter(id=part_id).exists())

    def test_law_cascade_delete_to_schedules(self):
        """Test that deleting a Law cascades to Schedules."""
        law = Law.objects.create(title="Test Law", slug="test-law")
        schedule = Schedule.objects.create(
            law=law,
            schedule_number="First Schedule",
            title="Schedule Title"
        )
        schedule_id = schedule.id

        law.delete()

        # Schedule should be deleted
        self.assertFalse(Schedule.objects.filter(id=schedule_id).exists())

    def test_law_cascade_delete_to_appendices(self):
        """Test that deleting a Law cascades to Appendices."""
        law = Law.objects.create(title="Test Law", slug="test-law")
        appendix = Appendix.objects.create(
            law=law,
            appendix_number="Appendix A",
            title="Appendix Title"
        )
        appendix_id = appendix.id

        law.delete()

        # Appendix should be deleted
        self.assertFalse(Appendix.objects.filter(id=appendix_id).exists())


class PartModelTest(TestCase):
    """Tests for the Part model."""

    def setUp(self):
        self.law = Law.objects.create(title="Test Law", slug="test-law")

    def test_part_creation(self):
        """Test creating a Part instance."""
        part = Part.objects.create(law=self.law, heading="Part I - Preliminary")
        self.assertEqual(part.heading, "Part I - Preliminary")
        self.assertEqual(part.law, self.law)

    def test_part_ordering(self):
        """Test that Parts are ordered by the 'order' field."""
        part3 = Part.objects.create(law=self.law, heading="Part 3", order=3)
        part1 = Part.objects.create(law=self.law, heading="Part 1", order=1)
        part2 = Part.objects.create(law=self.law, heading="Part 2", order=2)

        parts = Part.objects.filter(law=self.law)
        self.assertEqual(list(parts), [part1, part2, part3])

    def test_part_cascade_delete_to_chapters(self):
        """Test that deleting a Part cascades to Chapters."""
        part = Part.objects.create(law=self.law, heading="Part 1")
        chapter = Chapter.objects.create(part=part, heading="Chapter 1")
        chapter_id = chapter.id

        part.delete()

        # Chapter should be deleted
        self.assertFalse(Chapter.objects.filter(id=chapter_id).exists())


class ChapterModelTest(TestCase):
    """Tests for the Chapter model."""

    def setUp(self):
        self.law = Law.objects.create(title="Test Law", slug="test-law")
        self.part = Part.objects.create(law=self.law, heading="Part 1")

    def test_chapter_creation(self):
        """Test creating a Chapter instance."""
        chapter = Chapter.objects.create(
            part=self.part,
            heading="Chapter 1 - General Provisions"
        )
        self.assertEqual(chapter.heading, "Chapter 1 - General Provisions")
        self.assertEqual(chapter.part, self.part)

    def test_chapter_ordering(self):
        """Test that Chapters are ordered by the 'order' field."""
        chapter3 = Chapter.objects.create(part=self.part, heading="Chapter 3", order=3)
        chapter1 = Chapter.objects.create(part=self.part, heading="Chapter 1", order=1)
        chapter2 = Chapter.objects.create(part=self.part, heading="Chapter 2", order=2)

        chapters = Chapter.objects.filter(part=self.part)
        self.assertEqual(list(chapters), [chapter1, chapter2, chapter3])

    def test_chapter_cascade_delete_to_sections(self):
        """Test that deleting a Chapter cascades to Sections."""
        chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        section = Section.objects.create(
            chapter=chapter,
            number="1",
            title="Test Section"
        )
        section_id = section.id

        chapter.delete()

        # Section should be deleted
        self.assertFalse(Section.objects.filter(id=section_id).exists())


class SectionModelTest(TestCase):
    """Tests for the Section model."""

    def setUp(self):
        self.law = Law.objects.create(title="Test Law", slug="test-law")
        self.part = Part.objects.create(law=self.law, heading="Part 1")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")

    def test_section_creation(self):
        """Test creating a Section instance."""
        section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Citation",
            content="This Act may be cited as the Test Act."
        )
        self.assertEqual(section.number, "1")
        self.assertEqual(section.title, "Citation")
        self.assertEqual(section.chapter, self.chapter)

    def test_section_str_representation(self):
        """Test Section string representation."""
        section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Citation"
        )
        self.assertEqual(str(section), "S.1 — Citation")

        # Test section without title
        section_no_title = Section.objects.create(
            chapter=self.chapter,
            number="2"
        )
        self.assertEqual(str(section_no_title), "S.2 — [No Title]")

    def test_section_ordering(self):
        """Test that Sections are ordered by the 'order' field."""
        section3 = Section.objects.create(
            chapter=self.chapter,
            number="3",
            order=3
        )
        section1 = Section.objects.create(
            chapter=self.chapter,
            number="1",
            order=1
        )
        section2 = Section.objects.create(
            chapter=self.chapter,
            number="2",
            order=2
        )

        sections = Section.objects.filter(chapter=self.chapter)
        self.assertEqual(list(sections), [section1, section2, section3])

    def test_section_unique_together_constraint(self):
        """Test that Section (chapter, number) must be unique."""
        Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="First Section"
        )

        # Creating another section with same chapter and number should fail
        with self.assertRaises(IntegrityError):
            Section.objects.create(
                chapter=self.chapter,
                number="1",
                title="Duplicate Section"
            )

    def test_section_law_helper_method(self):
        """Test Section.law() helper method returns parent Law."""
        section = Section.objects.create(
            chapter=self.chapter,
            number="1"
        )
        self.assertEqual(section.law(), self.law)

    def test_section_anchor_tag(self):
        """Test Section.anchor_tag() method."""
        section = Section.objects.create(
            chapter=self.chapter,
            number="1"
        )
        expected_anchor = f"section-{section.id}"
        self.assertEqual(section.anchor_tag(), expected_anchor)

    def test_section_get_absolute_url(self):
        """Test Section.get_absolute_url() includes anchor."""
        section = Section.objects.create(
            chapter=self.chapter,
            number="1"
        )
        expected_url = f"/laws/test-law/#section-{section.id}"
        self.assertEqual(section.get_absolute_url(), expected_url)


class ScheduleModelTest(TestCase):
    """Tests for the Schedule model."""

    def setUp(self):
        self.law = Law.objects.create(title="Test Law", slug="test-law")

    def test_schedule_creation(self):
        """Test creating a Schedule instance."""
        schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule",
            title="List of Authorities",
            content="1. Authority A\n2. Authority B"
        )
        self.assertEqual(schedule.schedule_number, "First Schedule")
        self.assertEqual(schedule.title, "List of Authorities")
        self.assertEqual(schedule.law, self.law)

    def test_schedule_str_representation(self):
        """Test Schedule string representation."""
        schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule",
            title="List of Authorities"
        )
        self.assertEqual(str(schedule), "First Schedule - List of Authorities")

    def test_schedule_anchor_tag(self):
        """Test Schedule.anchor_tag() method."""
        schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule"
        )
        expected_anchor = f"schedule-{schedule.id}"
        self.assertEqual(schedule.anchor_tag(), expected_anchor)


class AppendixModelTest(TestCase):
    """Tests for the Appendix model."""

    def setUp(self):
        self.law = Law.objects.create(title="Test Law", slug="test-law")

    def test_appendix_creation(self):
        """Test creating an Appendix instance."""
        appendix = Appendix.objects.create(
            law=self.law,
            appendix_number="Appendix A",
            title="Forms",
            content="Form 1: Application\nForm 2: Response"
        )
        self.assertEqual(appendix.appendix_number, "Appendix A")
        self.assertEqual(appendix.title, "Forms")
        self.assertEqual(appendix.law, self.law)

    def test_appendix_str_representation(self):
        """Test Appendix string representation."""
        appendix = Appendix.objects.create(
            law=self.law,
            appendix_number="Appendix A",
            title="Forms"
        )
        self.assertEqual(str(appendix), "Appendix A - Forms")

    def test_appendix_anchor_tag(self):
        """Test Appendix.anchor_tag() method."""
        appendix = Appendix.objects.create(
            law=self.law,
            appendix_number="Appendix A"
        )
        expected_anchor = f"appendix-{appendix.id}"
        self.assertEqual(appendix.anchor_tag(), expected_anchor)


class ModelRelationshipsTest(TestCase):
    """Integration tests for model relationships."""

    def test_complete_hierarchy_cascade_delete(self):
        """Test that deleting a Law cascades through entire hierarchy."""
        # Create complete hierarchy
        law = Law.objects.create(title="Test Law", slug="test-law")
        part = Part.objects.create(law=law, heading="Part 1")
        chapter = Chapter.objects.create(part=part, heading="Chapter 1")
        section = Section.objects.create(chapter=chapter, number="1")

        # Store IDs
        part_id = part.id
        chapter_id = chapter.id
        section_id = section.id

        # Delete law
        law.delete()

        # All related objects should be deleted
        self.assertFalse(Part.objects.filter(id=part_id).exists())
        self.assertFalse(Chapter.objects.filter(id=chapter_id).exists())
        self.assertFalse(Section.objects.filter(id=section_id).exists())

    def test_law_related_names(self):
        """Test that related_name queries work correctly."""
        law = Law.objects.create(title="Test Law", slug="test-law")
        part1 = Part.objects.create(law=law, heading="Part 1")
        part2 = Part.objects.create(law=law, heading="Part 2")
        schedule = Schedule.objects.create(law=law, schedule_number="First")
        appendix = Appendix.objects.create(law=law, appendix_number="A")

        # Test reverse relationships
        self.assertEqual(law.parts.count(), 2)
        self.assertIn(part1, law.parts.all())
        self.assertIn(part2, law.parts.all())
        self.assertEqual(law.schedules.count(), 1)
        self.assertEqual(law.appendices.count(), 1)

    def test_section_reaches_law_through_hierarchy(self):
        """Test that Section can reach Law through chapter.part.law."""
        law = Law.objects.create(title="Test Law", slug="test-law")
        part = Part.objects.create(law=law, heading="Part 1")
        chapter = Chapter.objects.create(part=part, heading="Chapter 1")
        section = Section.objects.create(chapter=chapter, number="1")

        # Test traversing up the hierarchy
        self.assertEqual(section.chapter.part.law, law)
        self.assertEqual(section.law(), law)
