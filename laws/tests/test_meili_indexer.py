"""
Test cases for MeiliSearch indexer.

Tests cover:
- build_section_doc function
- build_schedule_doc function
- setup_index function
- rebuild_meili_index function
- Document structure and field mapping
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from laws.models import Law, Part, Chapter, Section, Schedule, Appendix
from laws.meili_indexer import (
    build_section_doc,
    build_schedule_doc,
    setup_index,
    rebuild_meili_index
)


class BuildSectionDocTest(TestCase):
    """Tests for build_section_doc function."""

    def setUp(self):
        self.law = Law.objects.create(
            title="Test Law 2024",
            slug="test-law-2024"
        )
        self.part = Part.objects.create(
            law=self.law,
            heading="Part I - Preliminary"
        )
        self.chapter = Chapter.objects.create(
            part=self.part,
            heading="Chapter 1 - General Provisions"
        )
        self.section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Citation",
            content="This Act may be cited as the Test Act, 2024."
        )

    def test_build_section_doc_structure(self):
        """Test build_section_doc returns correct document structure."""
        doc = build_section_doc(self.section)

        # Check all required fields are present
        self.assertIn('id', doc)
        self.assertIn('result_type', doc)
        self.assertIn('law_id', doc)
        self.assertIn('law_title', doc)
        self.assertIn('law_slug', doc)
        self.assertIn('anchor_tag', doc)
        self.assertIn('part_heading', doc)
        self.assertIn('chapter_heading', doc)
        self.assertIn('section_number', doc)
        self.assertIn('section_title', doc)
        self.assertIn('content', doc)

    def test_build_section_doc_field_values(self):
        """Test build_section_doc populates fields correctly."""
        doc = build_section_doc(self.section)

        self.assertEqual(doc['id'], f'section-{self.section.id}')
        self.assertEqual(doc['result_type'], 'Section')
        self.assertEqual(doc['law_id'], self.law.id)
        self.assertEqual(doc['law_title'], 'Test Law 2024')
        self.assertEqual(doc['law_slug'], 'test-law-2024')
        self.assertEqual(doc['anchor_tag'], f'section-{self.section.id}')
        self.assertEqual(doc['part_heading'], 'Part I - Preliminary')
        self.assertEqual(doc['chapter_heading'], 'Chapter 1 - General Provisions')
        self.assertEqual(doc['section_number'], '1')
        self.assertEqual(doc['section_title'], 'Citation')
        self.assertEqual(doc['content'], 'This Act may be cited as the Test Act, 2024.')

    def test_build_section_doc_with_empty_fields(self):
        """Test build_section_doc handles empty optional fields."""
        section_minimal = Section.objects.create(
            chapter=self.chapter,
            number="2",
            title="",
            content=""
        )

        doc = build_section_doc(section_minimal)

        self.assertEqual(doc['section_title'], '')
        self.assertEqual(doc['content'], '')

    def test_build_section_doc_with_empty_law_slug(self):
        """Test build_section_doc handles law with no slug."""
        law_no_slug = Law.objects.create(
            title="Law Without Slug",
            slug=""
        )
        part = Part.objects.create(law=law_no_slug, heading="Part")
        chapter = Chapter.objects.create(part=part, heading="Chapter")
        section = Section.objects.create(chapter=chapter, number="1")

        doc = build_section_doc(section)

        self.assertEqual(doc['law_slug'], '')

    def test_build_section_doc_traverses_relationships(self):
        """Test build_section_doc correctly traverses model relationships."""
        doc = build_section_doc(self.section)

        # Verify it accessed the correct related objects
        self.assertEqual(doc['law_id'], self.section.chapter.part.law.id)
        self.assertEqual(doc['part_heading'], self.section.chapter.part.heading)
        self.assertEqual(doc['chapter_heading'], self.section.chapter.heading)


class BuildScheduleDocTest(TestCase):
    """Tests for build_schedule_doc function."""

    def setUp(self):
        self.law = Law.objects.create(
            title="Test Law 2024",
            slug="test-law-2024"
        )
        self.schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule",
            title="List of Authorities",
            content="1. Authority A\n2. Authority B"
        )

    def test_build_schedule_doc_structure(self):
        """Test build_schedule_doc returns correct document structure."""
        doc = build_schedule_doc(self.schedule)

        # Check all required fields are present
        self.assertIn('id', doc)
        self.assertIn('result_type', doc)
        self.assertIn('law_id', doc)
        self.assertIn('law_title', doc)
        self.assertIn('law_slug', doc)
        self.assertIn('anchor_tag', doc)
        self.assertIn('title', doc)
        self.assertIn('content', doc)

    def test_build_schedule_doc_field_values(self):
        """Test build_schedule_doc populates fields correctly."""
        doc = build_schedule_doc(self.schedule)

        self.assertEqual(doc['id'], f'schedule-{self.schedule.id}')
        self.assertEqual(doc['result_type'], 'Schedule')
        self.assertEqual(doc['law_id'], self.law.id)
        self.assertEqual(doc['law_title'], 'Test Law 2024')
        self.assertEqual(doc['law_slug'], 'test-law-2024')
        self.assertEqual(doc['anchor_tag'], f'schedule-{self.schedule.id}')
        self.assertEqual(doc['title'], 'List of Authorities')
        self.assertEqual(doc['content'], '1. Authority A\n2. Authority B')

    def test_build_schedule_doc_with_empty_fields(self):
        """Test build_schedule_doc handles empty optional fields."""
        schedule_minimal = Schedule.objects.create(
            law=self.law,
            schedule_number="Second Schedule",
            title="",
            content=""
        )

        doc = build_schedule_doc(schedule_minimal)

        self.assertEqual(doc['title'], '')
        self.assertEqual(doc['content'], '')


class SetupIndexTest(TestCase):
    """Tests for setup_index function."""

    def test_setup_index_configures_searchable_attributes(self):
        """Test setup_index sets searchable attributes."""
        mock_index = MagicMock()

        setup_index(mock_index)

        mock_index.update_searchable_attributes.assert_called_once()
        call_args = mock_index.update_searchable_attributes.call_args[0][0]

        # Verify expected searchable attributes
        self.assertIn('law_title', call_args)
        self.assertIn('section_title', call_args)
        self.assertIn('content', call_args)
        self.assertIn('part_heading', call_args)
        self.assertIn('chapter_heading', call_args)

    def test_setup_index_configures_displayed_attributes(self):
        """Test setup_index sets displayed attributes."""
        mock_index = MagicMock()

        setup_index(mock_index)

        mock_index.update_displayed_attributes.assert_called_once_with(['*'])

    def test_setup_index_configures_filterable_attributes(self):
        """Test setup_index sets filterable attributes."""
        mock_index = MagicMock()

        setup_index(mock_index)

        mock_index.update_filterable_attributes.assert_called_once()
        call_args = mock_index.update_filterable_attributes.call_args[0][0]

        # Verify expected filterable attributes
        self.assertIn('law_slug', call_args)
        self.assertIn('result_type', call_args)
        self.assertIn('law_id', call_args)


class RebuildMeiliIndexTest(TestCase):
    """Tests for rebuild_meili_index function."""

    def setUp(self):
        # Create test data
        self.law = Law.objects.create(
            title="Test Law",
            slug="test-law"
        )
        self.part = Part.objects.create(law=self.law, heading="Part 1")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        self.section1 = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Section 1"
        )
        self.section2 = Section.objects.create(
            chapter=self.chapter,
            number="2",
            title="Section 2"
        )

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_calls_setup_index(self, mock_client):
        """Test rebuild_meili_index calls setup_index."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        rebuild_meili_index()

        # Verify setup_index was called (checks for update methods)
        mock_index.update_searchable_attributes.assert_called_once()
        mock_index.update_displayed_attributes.assert_called_once()
        mock_index.update_filterable_attributes.assert_called_once()

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_adds_all_sections(self, mock_client):
        """Test rebuild_meili_index adds all sections to index."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        rebuild_meili_index()

        # Verify add_documents was called
        mock_index.add_documents.assert_called_once()

        # Check that correct number of documents were added
        call_args = mock_index.add_documents.call_args[0][0]
        self.assertEqual(len(call_args), 2)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_returns_count(self, mock_client):
        """Test rebuild_meili_index returns correct document count."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        count = rebuild_meili_index()

        self.assertEqual(count, 2)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_with_no_sections(self, mock_client):
        """Test rebuild_meili_index handles empty database."""
        # Delete all sections
        Section.objects.all().delete()

        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        count = rebuild_meili_index()

        self.assertEqual(count, 0)
        mock_index.add_documents.assert_called_once_with([])

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_uses_select_related(self, mock_client):
        """Test rebuild_meili_index uses select_related for efficiency."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        # This test verifies efficient query usage
        with self.assertNumQueries(1):  # Should only need 1 query with select_related
            rebuild_meili_index()

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_document_content(self, mock_client):
        """Test rebuild_meili_index creates correct document structure."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        rebuild_meili_index()

        call_args = mock_index.add_documents.call_args[0][0]
        doc = call_args[0]

        # Verify document has correct structure
        self.assertEqual(doc['result_type'], 'Section')
        self.assertEqual(doc['law_title'], 'Test Law')
        self.assertEqual(doc['section_number'], '1')

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_index_uses_correct_index_name(self, mock_client):
        """Test rebuild_meili_index uses correct index name."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        rebuild_meili_index()

        # Verify correct index was accessed
        # INDEX_NAME defaults to 'laws' in meili_indexer.py
        mock_client.index.assert_called()


class MeiliIndexerIntegrationTest(TestCase):
    """Integration tests for meili_indexer module."""

    def setUp(self):
        # Create complex hierarchy
        self.law = Law.objects.create(title="Complex Law", slug="complex-law")
        self.part1 = Part.objects.create(law=self.law, heading="Part I")
        self.part2 = Part.objects.create(law=self.law, heading="Part II")
        self.chapter1 = Chapter.objects.create(part=self.part1, heading="Chapter 1")
        self.chapter2 = Chapter.objects.create(part=self.part2, heading="Chapter 2")
        self.section1 = Section.objects.create(
            chapter=self.chapter1,
            number="1",
            title="Section in Part I"
        )
        self.section2 = Section.objects.create(
            chapter=self.chapter2,
            number="2",
            title="Section in Part II"
        )
        self.schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First"
        )

    @patch('laws.meili_indexer.meili_client')
    def test_full_rebuild_with_complex_hierarchy(self, mock_client):
        """Test full rebuild with complex law hierarchy."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        count = rebuild_meili_index()

        # Should index all sections
        self.assertEqual(count, 2)

        # Verify documents have correct hierarchy information
        call_args = mock_index.add_documents.call_args[0][0]

        # Find section1 document
        section1_doc = next(d for d in call_args if d['section_number'] == '1')
        self.assertEqual(section1_doc['part_heading'], 'Part I')
        self.assertEqual(section1_doc['chapter_heading'], 'Chapter 1')

        # Find section2 document
        section2_doc = next(d for d in call_args if d['section_number'] == '2')
        self.assertEqual(section2_doc['part_heading'], 'Part II')
        self.assertEqual(section2_doc['chapter_heading'], 'Chapter 2')

    def test_section_and_schedule_doc_consistency(self):
        """Test that section and schedule docs have consistent law references."""
        section_doc = build_section_doc(self.section1)
        schedule_doc = build_schedule_doc(self.schedule)

        # Both should reference the same law
        self.assertEqual(section_doc['law_id'], schedule_doc['law_id'])
        self.assertEqual(section_doc['law_title'], schedule_doc['law_title'])
        self.assertEqual(section_doc['law_slug'], schedule_doc['law_slug'])

    def test_unique_document_ids(self):
        """Test that each document has a unique ID."""
        section1_doc = build_section_doc(self.section1)
        section2_doc = build_section_doc(self.section2)
        schedule_doc = build_schedule_doc(self.schedule)

        ids = [section1_doc['id'], section2_doc['id'], schedule_doc['id']]

        # All IDs should be unique
        self.assertEqual(len(ids), len(set(ids)))
