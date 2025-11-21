"""
Test cases for laws views.

Tests cover:
- Search view with MeiliSearch integration (mocked)
- Law detail view
- Query handling and edge cases
- Result hydration
- Error handling
"""

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from laws.models import Law, Part, Chapter, Section, Schedule, Appendix


class SearchViewTest(TestCase):
    """Tests for the search view with mocked MeiliSearch."""

    def setUp(self):
        self.client = Client()
        self.search_url = reverse('laws:search')

        # Create test data
        self.law = Law.objects.create(
            title="Test Law 2024",
            slug="test-law-2024"
        )
        self.part = Part.objects.create(law=self.law, heading="Part 1")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        self.section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Citation",
            content="This Act may be cited as the Test Act."
        )
        self.schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule",
            title="Authorities",
            content="List of authorities"
        )
        self.appendix = Appendix.objects.create(
            law=self.law,
            appendix_number="Appendix A",
            title="Forms",
            content="Application forms"
        )

    @patch('laws.views.meilisearch.Client')
    def test_search_with_empty_query(self, mock_client):
        """Test search view with empty query returns no results."""
        response = self.client.get(self.search_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'laws/search_results.html')
        self.assertEqual(response.context['query'], '')
        self.assertEqual(response.context['results'], [])

    @patch('laws.views.meilisearch.Client')
    def test_search_with_valid_query_sections(self, mock_client):
        """Test search with valid query returns section results."""
        # Mock MeiliSearch client
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        # Mock search results for sections
        mock_index.search.return_value = {
            'hits': [
                {
                    'id': f'section-{self.section.id}',
                    'law': self.law.id,
                    'section_number': '1',
                    'section_title': 'Citation',
                    'content': 'This Act may be cited as the Test Act.',
                    '_formatted': {
                        'content': 'This Act may be <b>cited</b> as the Test Act.'
                    }
                }
            ]
        }

        response = self.client.get(self.search_url, {'q': 'cited'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], 'cited')
        self.assertEqual(len(response.context['results']), 1)

        # Check result hydration
        result = response.context['results'][0]
        self.assertEqual(result['result_type'], 'Section')
        self.assertEqual(result['law_title'], 'Test Law 2024')
        self.assertEqual(result['law_slug'], 'test-law-2024')

    @patch('laws.views.meilisearch.Client')
    def test_search_with_valid_query_schedules(self, mock_client):
        """Test search returns schedule results."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        # Mock different responses for different indexes
        def mock_search_side_effect(query, options):
            index_name = mock_index.search.call_count
            if index_name == 1:  # sections
                return {'hits': []}
            elif index_name == 2:  # schedules
                return {
                    'hits': [
                        {
                            'id': f'schedule-{self.schedule.id}',
                            'law': self.law.id,
                            'schedule_number': 'First Schedule',
                            'title': 'Authorities',
                            'content': 'List of authorities',
                            '_formatted': {
                                'content': 'List of <b>authorities</b>'
                            }
                        }
                    ]
                }
            else:  # appendices
                return {'hits': []}

        mock_index.search.side_effect = mock_search_side_effect

        response = self.client.get(self.search_url, {'q': 'authorities'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['results']), 1)

        result = response.context['results'][0]
        self.assertEqual(result['result_type'], 'Schedule')
        self.assertEqual(result['law_title'], 'Test Law 2024')

    @patch('laws.views.meilisearch.Client')
    def test_search_with_valid_query_appendices(self, mock_client):
        """Test search returns appendix results."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        def mock_search_side_effect(query, options):
            index_name = mock_index.search.call_count
            if index_name <= 2:  # sections, schedules
                return {'hits': []}
            else:  # appendices
                return {
                    'hits': [
                        {
                            'id': f'appendix-{self.appendix.id}',
                            'law': self.law.id,
                            'appendix_number': 'Appendix A',
                            'title': 'Forms',
                            'content': 'Application forms',
                            '_formatted': {
                                'content': 'Application <b>forms</b>'
                            }
                        }
                    ]
                }

        mock_index.search.side_effect = mock_search_side_effect

        response = self.client.get(self.search_url, {'q': 'forms'})

        self.assertEqual(response.status_code, 200)
        result = response.context['results'][0]
        self.assertEqual(result['result_type'], 'Appendix')

    @patch('laws.views.meilisearch.Client')
    def test_search_with_multiple_results(self, mock_client):
        """Test search with results from multiple indexes."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        def mock_search_side_effect(query, options):
            index_name = mock_index.search.call_count
            if index_name == 1:  # sections
                return {
                    'hits': [
                        {
                            'id': f'section-{self.section.id}',
                            'law': self.law.id,
                            '_formatted': {}
                        }
                    ]
                }
            elif index_name == 2:  # schedules
                return {
                    'hits': [
                        {
                            'id': f'schedule-{self.schedule.id}',
                            'law': self.law.id,
                            '_formatted': {}
                        }
                    ]
                }
            else:  # appendices
                return {'hits': []}

        mock_index.search.side_effect = mock_search_side_effect

        response = self.client.get(self.search_url, {'q': 'test'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['results']), 2)

    @patch('laws.views.meilisearch.Client')
    def test_search_hydration_with_missing_law(self, mock_client):
        """Test search handles missing Law objects gracefully."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index

        # Mock result with non-existent law ID
        mock_index.search.return_value = {
            'hits': [
                {
                    'id': 'section-999',
                    'law': 99999,  # Non-existent law ID
                    '_formatted': {}
                }
            ]
        }

        response = self.client.get(self.search_url, {'q': 'test'})

        self.assertEqual(response.status_code, 200)
        result = response.context['results'][0]
        self.assertEqual(result['law_title'], 'Error: Law not found')
        self.assertEqual(result['law_slug'], '')

    @patch('laws.views.meilisearch.Client')
    def test_search_highlights_configured(self, mock_client):
        """Test that search configures highlighting options."""
        mock_index = MagicMock()
        mock_client.return_value.index.return_value = mock_index
        mock_index.search.return_value = {'hits': []}

        self.client.get(self.search_url, {'q': 'test'})

        # Verify search was called with highlight options
        call_args = mock_index.search.call_args
        self.assertIsNotNone(call_args)
        options = call_args[0][1]
        self.assertEqual(options['attributesToHighlight'], ['*'])
        self.assertEqual(options['highlightPreTag'], '<b>')
        self.assertEqual(options['highlightPostTag'], '</b>')


class LawDetailViewTest(TestCase):
    """Tests for the law detail view."""

    def setUp(self):
        self.client = Client()
        self.law = Law.objects.create(
            title="Test Law 2024",
            slug="test-law-2024",
            description="A test law for testing purposes"
        )
        self.part = Part.objects.create(law=self.law, heading="Part 1", order=1)
        self.chapter = Chapter.objects.create(
            part=self.part,
            heading="Chapter 1",
            order=1
        )
        self.section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Citation",
            content="This Act may be cited as the Test Act.",
            order=1
        )
        self.schedule = Schedule.objects.create(
            law=self.law,
            schedule_number="First Schedule",
            title="Authorities"
        )
        self.appendix = Appendix.objects.create(
            law=self.law,
            appendix_number="Appendix A",
            title="Forms"
        )

    def test_law_detail_view_success(self):
        """Test law detail view returns 200 and displays law."""
        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'laws/law_detail.html')
        self.assertEqual(response.context['law'], self.law)

    def test_law_detail_view_contains_sections(self):
        """Test law detail view includes sections in context."""
        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        response = self.client.get(url)

        self.assertIn('sections', response.context)
        sections = response.context['sections']
        self.assertEqual(sections.count(), 1)
        self.assertEqual(sections[0], self.section)

    def test_law_detail_view_contains_schedules(self):
        """Test law detail view includes schedules in context."""
        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        response = self.client.get(url)

        self.assertIn('schedules', response.context)
        schedules = response.context['schedules']
        self.assertEqual(schedules.count(), 1)
        self.assertEqual(schedules[0], self.schedule)

    def test_law_detail_view_contains_appendices(self):
        """Test law detail view includes appendices in context."""
        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        response = self.client.get(url)

        self.assertIn('appendices', response.context)
        appendices = response.context['appendices']
        self.assertEqual(appendices.count(), 1)
        self.assertEqual(appendices[0], self.appendix)

    def test_law_detail_view_404_for_invalid_slug(self):
        """Test law detail view returns 404 for non-existent slug."""
        url = reverse('laws:law_detail', kwargs={'law_slug': 'non-existent'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_law_detail_view_sections_ordered_correctly(self):
        """Test sections are ordered by hierarchy."""
        # Create additional sections in different order
        part2 = Part.objects.create(law=self.law, heading="Part 2", order=2)
        chapter2 = Chapter.objects.create(part=part2, heading="Chapter 2", order=2)
        section2 = Section.objects.create(
            chapter=chapter2,
            number="2",
            title="Definitions",
            order=1
        )
        section3 = Section.objects.create(
            chapter=self.chapter,
            number="1A",
            title="Application",
            order=2
        )

        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        response = self.client.get(url)

        sections = list(response.context['sections'])
        # Should be ordered by part order, chapter order, section order
        self.assertEqual(sections[0], self.section)  # Part 1, Chapter 1, order 1
        self.assertEqual(sections[1], section3)      # Part 1, Chapter 1, order 2
        self.assertEqual(sections[2], section2)      # Part 2, Chapter 2, order 1

    def test_law_detail_view_with_no_sections(self):
        """Test law detail view works with no sections."""
        # Create law with no sections
        empty_law = Law.objects.create(
            title="Empty Law",
            slug="empty-law"
        )

        url = reverse('laws:law_detail', kwargs={'law_slug': empty_law.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sections'].count(), 0)
        self.assertEqual(response.context['schedules'].count(), 0)
        self.assertEqual(response.context['appendices'].count(), 0)

    def test_law_detail_view_sections_use_select_related(self):
        """Test that the view uses select_related for efficient queries."""
        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})

        # This test verifies the query optimization
        with self.assertNumQueries(4):  # law, sections, schedules, appendices
            response = self.client.get(url)
            # Access the sections to ensure they're evaluated
            list(response.context['sections'])

    def test_law_detail_view_content_display(self):
        """Test that law detail view displays all content."""
        url = reverse('laws:law_detail', kwargs={'law_slug': self.law.slug})
        response = self.client.get(url)

        # Check that key content is present in response
        self.assertContains(response, "Test Law 2024")
        self.assertContains(response, "Part 1")
        self.assertContains(response, "Chapter 1")
        self.assertContains(response, "Citation")
        self.assertContains(response, "This Act may be cited as the Test Act.")
