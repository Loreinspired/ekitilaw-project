"""
Integration tests for the laws app.

Tests cover:
- Complete workflows (import → index → search)
- End-to-end user journeys
- Cross-module interactions
- Real-world scenarios
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from laws.models import Law, Part, Chapter, Section, Schedule, Appendix
from laws.admin import _run_import_logic, LawAdmin
from laws.meili_indexer import build_section_doc, rebuild_meili_index
from django.contrib.admin.sites import AdminSite


class ImportToSearchWorkflowTest(TestCase):
    """Test the complete workflow from importing a law to searching it."""

    def setUp(self):
        self.client = Client()
        self.law = Law.objects.create(
            title="Ekiti State Education Law",
            slug="ekiti-education-law"
        )

    def test_complete_import_to_search_workflow(self):
        """Test importing a law, indexing it, and searching for it."""
        # Step 1: Import AI-prepared text
        self.law.ai_prepared_text = """@PART PART I - PRELIMINARY
@CHAPTER CHAPTER 1 - INTERPRETATION
@SECTION S.1
@TITLE Citation
This Law may be cited as the Ekiti State Education Law, 2024.
@SECTION S.2
@TITLE Interpretation
In this Law, unless the context otherwise requires:
"Minister" means the Commissioner for Education."""

        _run_import_logic(self.law)

        # Verify import created correct structure
        self.assertEqual(Part.objects.count(), 1)
        self.assertEqual(Chapter.objects.count(), 1)
        self.assertEqual(Section.objects.count(), 2)

        section1 = Section.objects.get(number="S.1")
        self.assertEqual(section1.title, "Citation")

        # Step 2: Build search documents
        section1_doc = build_section_doc(section1)
        self.assertEqual(section1_doc['law_title'], "Ekiti State Education Law")
        self.assertEqual(section1_doc['section_title'], "Citation")

        # Step 3: Mock search and verify results can be found
        with patch('laws.views.meilisearch.Client') as mock_client:
            mock_index = MagicMock()
            mock_client.return_value.index.return_value = mock_index

            # Simulate finding the section in search
            mock_index.search.return_value = {
                'hits': [{
                    'id': f'section-{section1.id}',
                    'law': self.law.id,
                    'section_number': 'S.1',
                    'section_title': 'Citation',
                    '_formatted': {}
                }]
            }

            # Step 4: Perform search
            response = self.client.get(reverse('laws:search'), {'q': 'education'})

            self.assertEqual(response.status_code, 200)
            results = response.context['results']
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['law_title'], 'Ekiti State Education Law')

    @patch('laws.meili_indexer.meili_client')
    def test_import_then_rebuild_index(self, mock_client):
        """Test importing content then rebuilding search index."""
        # Import content
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Test Section
Test content."""

        _run_import_logic(self.law)

        # Rebuild index
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        count = rebuild_meili_index()

        # Verify index was rebuilt with new content
        self.assertEqual(count, 1)
        mock_index.add_documents.assert_called_once()

        docs = mock_index.add_documents.call_args[0][0]
        self.assertEqual(docs[0]['section_title'], 'Test Section')


class LawDetailAndSearchIntegrationTest(TestCase):
    """Test integration between law detail view and search."""

    def setUp(self):
        self.client = Client()
        self.law = Law.objects.create(
            title="Test Law",
            slug="test-law"
        )
        self.part = Part.objects.create(law=self.law, heading="Part I")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        self.section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Important Section",
            content="This section contains important information."
        )

    @patch('laws.views.meilisearch.Client')
    def test_search_result_links_to_law_detail(self, mock_client):
        """Test that search results can link to law detail page."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        # Mock search results
        mock_index.search.return_value = {
            'hits': [{
                'id': f'section-{self.section.id}',
                'law': self.law.id,
                '_formatted': {}
            }]
        }

        # Perform search
        search_response = self.client.get(reverse('laws:search'), {'q': 'important'})

        # Get hydrated result
        result = search_response.context['results'][0]
        law_slug = result['law_slug']

        # Navigate to law detail page
        detail_response = self.client.get(
            reverse('laws:law_detail', kwargs={'law_slug': law_slug})
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.context['law'], self.law)
        self.assertContains(detail_response, "Important Section")

    def test_law_detail_displays_searchable_content(self):
        """Test that law detail page displays content that should be searchable."""
        response = self.client.get(
            reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        )

        # Content that appears on detail page should be indexed for search
        self.assertContains(response, self.law.title)
        self.assertContains(response, self.section.title)
        self.assertContains(response, self.section.content)


class MultiLawSearchTest(TestCase):
    """Test searching across multiple laws."""

    def setUp(self):
        self.client = Client()

        # Create first law
        self.law1 = Law.objects.create(title="Education Law", slug="education-law")
        part1 = Part.objects.create(law=self.law1, heading="Part I")
        chapter1 = Chapter.objects.create(part=part1, heading="Chapter 1")
        self.section1 = Section.objects.create(
            chapter=chapter1,
            number="1",
            title="Schools",
            content="Provisions about schools."
        )

        # Create second law
        self.law2 = Law.objects.create(title="Health Law", slug="health-law")
        part2 = Part.objects.create(law=self.law2, heading="Part I")
        chapter2 = Chapter.objects.create(part=part2, heading="Chapter 1")
        self.section2 = Section.objects.create(
            chapter=chapter2,
            number="1",
            title="Hospitals",
            content="Provisions about hospitals."
        )

    @patch('laws.views.meilisearch.Client')
    def test_search_across_multiple_laws(self, mock_client):
        """Test searching returns results from multiple laws."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        # Mock results from both laws
        mock_index.search.return_value = {
            'hits': [
                {
                    'id': f'section-{self.section1.id}',
                    'law': self.law1.id,
                    '_formatted': {}
                },
                {
                    'id': f'section-{self.section2.id}',
                    'law': self.law2.id,
                    '_formatted': {}
                }
            ]
        }

        response = self.client.get(reverse('laws:search'), {'q': 'provisions'})

        results = response.context['results']
        self.assertEqual(len(results), 2)

        # Results should be from different laws
        law_titles = {r['law_title'] for r in results}
        self.assertEqual(law_titles, {'Education Law', 'Health Law'})

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_index_includes_all_laws(self, mock_client):
        """Test that rebuilding index includes sections from all laws."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        count = rebuild_meili_index()

        # Should index sections from both laws
        self.assertEqual(count, 2)

        docs = mock_index.add_documents.call_args[0][0]
        law_ids = {doc['law_id'] for doc in docs}
        self.assertEqual(law_ids, {self.law1.id, self.law2.id})


class ScheduleAndAppendixIntegrationTest(TestCase):
    """Test integration of schedules and appendices with main law content."""

    def setUp(self):
        self.client = Client()
        self.law = Law.objects.create(title="Complete Law", slug="complete-law")
        part = Part.objects.create(law=self.law, heading="Part I")
        chapter = Chapter.objects.create(part=part, heading="Chapter 1")
        self.section = Section.objects.create(
            chapter=chapter,
            number="1",
            title="Main Provisions"
        )
        self.schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule",
            title="Forms",
            content="Form A: Application Form"
        )
        self.appendix = Appendix.objects.create(
            law=self.law,
            appendix_number="Appendix A",
            title="Guidelines",
            content="Guideline 1: General guidelines"
        )

    def test_law_detail_includes_all_components(self):
        """Test law detail page includes sections, schedules, and appendices."""
        response = self.client.get(
            reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        )

        # Should include all components
        self.assertContains(response, "Main Provisions")
        self.assertContains(response, "First Schedule")
        self.assertContains(response, "Appendix A")

    @patch('laws.views.meilisearch.Client')
    def test_search_includes_all_content_types(self, mock_client):
        """Test search can return sections, schedules, and appendices."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        def mock_search_side_effect(query, options):
            call_count = mock_index.search.call_count
            if call_count == 1:  # sections
                return {'hits': [{'id': f'section-{self.section.id}', 'law': self.law.id, '_formatted': {}}]}
            elif call_count == 2:  # schedules
                return {'hits': [{'id': f'schedule-{self.schedule.id}', 'law': self.law.id, '_formatted': {}}]}
            else:  # appendices
                return {'hits': [{'id': f'appendix-{self.appendix.id}', 'law': self.law.id, '_formatted': {}}]}

        mock_index.search.side_effect = mock_search_side_effect

        response = self.client.get(reverse('laws:search'), {'q': 'test'})

        results = response.context['results']
        self.assertEqual(len(results), 3)

        result_types = {r['result_type'] for r in results}
        self.assertEqual(result_types, {'Section', 'Schedule', 'Appendix'})


class ErrorHandlingIntegrationTest(TestCase):
    """Test error handling across the application."""

    def setUp(self):
        self.client = Client()

    def test_search_with_invalid_query(self):
        """Test that invalid search queries are handled gracefully."""
        response = self.client.get(reverse('laws:search'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results'], [])

    def test_law_detail_with_invalid_slug(self):
        """Test accessing non-existent law returns 404."""
        response = self.client.get(
            reverse('laws:law_detail', kwargs={'law_slug': 'non-existent'})
        )
        self.assertEqual(response.status_code, 404)

    @patch('laws.views.meilisearch.Client')
    def test_search_with_ghost_data_in_index(self, mock_client):
        """Test search handles indexed data for deleted laws."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        # Mock search result pointing to non-existent law
        mock_index.search.return_value = {
            'hits': [{
                'id': 'section-99999',
                'law': 99999,  # Non-existent law ID
                '_formatted': {}
            }]
        }

        response = self.client.get(reverse('laws:search'), {'q': 'test'})

        # Should handle gracefully
        self.assertEqual(response.status_code, 200)
        results = response.context['results']
        self.assertEqual(results[0]['law_title'], 'Error: Law not found')


class ComplexHierarchyIntegrationTest(TestCase):
    """Test handling of complex law hierarchies."""

    def setUp(self):
        self.law = Law.objects.create(title="Complex Law", slug="complex-law")

        # Create multiple parts
        self.part1 = Part.objects.create(law=self.law, heading="Part I", order=1)
        self.part2 = Part.objects.create(law=self.law, heading="Part II", order=2)

        # Create multiple chapters in each part
        self.chapter1a = Chapter.objects.create(part=self.part1, heading="Chapter 1", order=1)
        self.chapter1b = Chapter.objects.create(part=self.part1, heading="Chapter 2", order=2)
        self.chapter2a = Chapter.objects.create(part=self.part2, heading="Chapter 1", order=1)

        # Create sections in each chapter
        self.section1a1 = Section.objects.create(
            chapter=self.chapter1a, number="1", title="S1", order=1
        )
        self.section1a2 = Section.objects.create(
            chapter=self.chapter1a, number="2", title="S2", order=2
        )
        self.section1b1 = Section.objects.create(
            chapter=self.chapter1b, number="3", title="S3", order=1
        )
        self.section2a1 = Section.objects.create(
            chapter=self.chapter2a, number="4", title="S4", order=1
        )

    def test_law_detail_displays_hierarchy_in_order(self):
        """Test law detail displays complex hierarchy in correct order."""
        response = self.client.get(
            reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        )

        sections = list(response.context['sections'])

        # Verify ordering: Part 1 Ch 1, Part 1 Ch 2, Part 2 Ch 1
        self.assertEqual(sections[0], self.section1a1)
        self.assertEqual(sections[1], self.section1a2)
        self.assertEqual(sections[2], self.section1b1)
        self.assertEqual(sections[3], self.section2a1)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_index_preserves_hierarchy(self, mock_client):
        """Test that indexing preserves hierarchy information."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        rebuild_meili_index()

        docs = mock_index.add_documents.call_args[0][0]

        # Find document for section in Part I, Chapter 1
        doc1 = next(d for d in docs if d['section_number'] == '1')
        self.assertEqual(doc1['part_heading'], 'Part I')
        self.assertEqual(doc1['chapter_heading'], 'Chapter 1')

        # Find document for section in Part II, Chapter 1
        doc4 = next(d for d in docs if d['section_number'] == '4')
        self.assertEqual(doc4['part_heading'], 'Part II')
        self.assertEqual(doc4['chapter_heading'], 'Chapter 1')

    def test_cascade_delete_entire_hierarchy(self):
        """Test deleting law cascades through entire complex hierarchy."""
        law_id = self.law.id
        section_ids = [
            self.section1a1.id, self.section1a2.id,
            self.section1b1.id, self.section2a1.id
        ]

        self.law.delete()

        # Verify everything was deleted
        self.assertFalse(Law.objects.filter(id=law_id).exists())
        for section_id in section_ids:
            self.assertFalse(Section.objects.filter(id=section_id).exists())
