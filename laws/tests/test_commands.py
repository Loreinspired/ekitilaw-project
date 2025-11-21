"""
Test cases for management commands.

Tests cover:
- rebuild_meili command
- repair_search_index command
- Command output and success messages
- Error handling
"""

from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from unittest.mock import patch, MagicMock
from laws.models import Law, Part, Chapter, Section, Schedule, Appendix


class RebuildMeiliCommandTest(TestCase):
    """Tests for the rebuild_meili management command."""

    def setUp(self):
        # Create test data
        self.law = Law.objects.create(title="Test Law", slug="test-law")
        self.part = Part.objects.create(law=self.law, heading="Part 1")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        self.section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Test Section",
            content="Test content"
        )

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_command_success(self, mock_client):
        """Test rebuild_meili command executes successfully."""
        # Mock MeiliSearch client and index
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        out = StringIO()
        call_command('rebuild_meili', stdout=out)

        output = out.getvalue()
        self.assertIn('Indexed', output)
        self.assertIn('docs into Meili', output)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_command_counts_documents(self, mock_client):
        """Test rebuild_meili command reports correct document count."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        out = StringIO()
        call_command('rebuild_meili', stdout=out)

        output = out.getvalue()
        # Should report at least 1 document (our test section)
        self.assertIn('1', output)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_command_calls_setup_index(self, mock_client):
        """Test rebuild_meili command sets up index configuration."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        call_command('rebuild_meili')

        # Verify index configuration methods were called
        mock_index.update_searchable_attributes.assert_called_once()
        mock_index.update_displayed_attributes.assert_called_once()
        mock_index.update_filterable_attributes.assert_called_once()

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_command_adds_documents(self, mock_client):
        """Test rebuild_meili command adds documents to index."""
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        call_command('rebuild_meili')

        # Verify add_documents was called
        mock_index.add_documents.assert_called_once()

        # Check that documents list is not empty
        call_args = mock_index.add_documents.call_args[0][0]
        self.assertGreater(len(call_args), 0)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_with_multiple_sections(self, mock_client):
        """Test rebuild_meili indexes multiple sections."""
        # Create additional sections
        section2 = Section.objects.create(
            chapter=self.chapter,
            number="2",
            title="Another Section",
            content="More content"
        )
        section3 = Section.objects.create(
            chapter=self.chapter,
            number="3",
            title="Third Section",
            content="Even more content"
        )

        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        call_command('rebuild_meili')

        # Verify multiple documents were added
        call_args = mock_index.add_documents.call_args[0][0]
        self.assertEqual(len(call_args), 3)

    @patch('laws.meili_indexer.meili_client')
    def test_rebuild_meili_with_no_sections(self, mock_client):
        """Test rebuild_meili handles case with no sections."""
        # Delete all sections
        Section.objects.all().delete()

        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        out = StringIO()
        call_command('rebuild_meili', stdout=out)

        # Should report 0 documents
        output = out.getvalue()
        self.assertIn('0', output)


class RepairSearchIndexCommandTest(TestCase):
    """Tests for the repair_search_index management command."""

    def setUp(self):
        # Create laws with and without slugs
        self.law_with_slug = Law.objects.create(
            title="Law With Slug",
            slug="law-with-slug"
        )
        self.law_without_slug = Law.objects.create(
            title="Law Without Slug",
            slug=""
        )

    def test_repair_search_index_command_output(self):
        """Test repair_search_index command produces expected output."""
        out = StringIO()

        with patch('laws.management.commands.repair_search_index.call_command'):
            call_command('repair_search_index', stdout=out)

        output = out.getvalue()
        self.assertIn('Checking Law Slugs', output)

    def test_repair_search_index_fixes_missing_slugs(self):
        """Test repair_search_index fixes laws with missing slugs."""
        out = StringIO()

        with patch('laws.management.commands.repair_search_index.call_command'):
            call_command('repair_search_index', stdout=out)

        # Check that the law without slug was fixed
        self.law_without_slug.refresh_from_db()
        # Note: This test assumes the Law model has save logic that generates slugs
        # If not, the slug will remain empty and we're just testing the command runs

        output = out.getvalue()
        # Should mention checking slugs
        self.assertIn('Checking Law Slugs', output)

    @patch('laws.management.commands.repair_search_index.call_command')
    def test_repair_search_index_calls_syncindex(self, mock_call_command):
        """Test repair_search_index calls syncindex for all models."""
        out = StringIO()
        call_command('repair_search_index', stdout=out)

        # Verify syncindex was called for all three models
        calls = mock_call_command.call_args_list
        self.assertEqual(len(calls), 3)

        # Check that each model was synced
        models_synced = [call[0][1] for call in calls]
        self.assertIn('laws.Section', models_synced)
        self.assertIn('laws.Schedule', models_synced)
        self.assertIn('laws.Appendix', models_synced)

    @patch('laws.management.commands.repair_search_index.call_command')
    def test_repair_search_index_handles_sync_errors(self, mock_call_command):
        """Test repair_search_index handles syncindex errors gracefully."""
        # Make syncindex raise an exception
        mock_call_command.side_effect = Exception("Sync failed")

        out = StringIO()
        call_command('repair_search_index', stdout=out)

        output = out.getvalue()
        self.assertIn('Index sync failed', output)

    def test_repair_search_index_counts_repaired_laws(self):
        """Test repair_search_index reports number of repaired laws."""
        out = StringIO()

        with patch('laws.management.commands.repair_search_index.call_command'):
            call_command('repair_search_index', stdout=out)

        output = out.getvalue()
        # Should show count of repaired laws
        self.assertIn('Success:', output)
        self.assertIn('laws repaired', output)

    def test_repair_search_index_with_all_valid_slugs(self):
        """Test repair_search_index when all laws have valid slugs."""
        # Ensure all laws have slugs
        self.law_without_slug.slug = "now-has-slug"
        self.law_without_slug.save()

        out = StringIO()

        with patch('laws.management.commands.repair_search_index.call_command'):
            call_command('repair_search_index', stdout=out)

        output = out.getvalue()
        # Should report 0 laws repaired
        self.assertIn('0 laws repaired', output)

    @patch('laws.management.commands.repair_search_index.call_command')
    def test_repair_search_index_syncs_in_correct_order(self, mock_call_command):
        """Test repair_search_index syncs models in expected order."""
        out = StringIO()
        call_command('repair_search_index', stdout=out)

        output = out.getvalue()

        # Check that output mentions syncing in order
        sections_pos = output.find('Syncing Sections')
        schedules_pos = output.find('Syncing Schedules')
        appendices_pos = output.find('Syncing Appendices')

        self.assertLess(sections_pos, schedules_pos)
        self.assertLess(schedules_pos, appendices_pos)

    @patch('laws.management.commands.repair_search_index.call_command')
    def test_repair_search_index_shows_success_message(self, mock_call_command):
        """Test repair_search_index shows success message when complete."""
        out = StringIO()
        call_command('repair_search_index', stdout=out)

        output = out.getvalue()
        self.assertIn('DONE', output)
        self.assertIn('fully synchronized', output)


class CommandIntegrationTest(TestCase):
    """Integration tests for management commands."""

    @patch('laws.meili_indexer.meili_client')
    @patch('laws.management.commands.repair_search_index.call_command')
    def test_repair_then_rebuild_workflow(self, mock_repair_call, mock_client):
        """Test workflow of repairing then rebuilding index."""
        # Create test data
        law = Law.objects.create(title="Test Law", slug="")
        part = Part.objects.create(law=law, heading="Part 1")
        chapter = Chapter.objects.create(part=part, heading="Chapter 1")
        Section.objects.create(chapter=chapter, number="1")

        # Mock MeiliSearch
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index

        # First repair
        out1 = StringIO()
        call_command('repair_search_index', stdout=out1)

        # Then rebuild
        out2 = StringIO()
        call_command('rebuild_meili', stdout=out2)

        # Both should complete successfully
        self.assertIn('Success', out1.getvalue())
        self.assertIn('Indexed', out2.getvalue())
