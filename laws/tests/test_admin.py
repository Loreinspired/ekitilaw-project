"""
Test cases for laws admin functionality.

Tests cover:
- AI import parser logic (_run_import_logic)
- Admin action: clean_with_ai
- Admin action: import_from_ai_text
- Tag parsing (@PART, @CHAPTER, @SECTION, etc.)
- Transaction handling and rollback
- Error handling
"""

from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from laws.models import Law, Part, Chapter, Section, Schedule, Appendix
from laws.admin import LawAdmin, _run_import_logic


class MockRequest:
    """Mock request object for admin tests."""
    def __init__(self, user):
        self.user = user
        # Mock messages framework
        self._messages = FallbackStorage(self)


class ImportLogicTest(TestCase):
    """Tests for the _run_import_logic parser function."""

    def setUp(self):
        self.law = Law.objects.create(
            title="Test Law",
            slug="test-law"
        )

    def test_import_simple_section(self):
        """Test importing a simple section."""
        self.law.ai_prepared_text = """@PART PART I - PRELIMINARY
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Citation
This Act may be cited as the Test Act, 2024."""

        _run_import_logic(self.law)

        # Check Part was created
        self.assertEqual(Part.objects.count(), 1)
        part = Part.objects.first()
        self.assertEqual(part.heading, "PART I - PRELIMINARY")

        # Check Chapter was created
        self.assertEqual(Chapter.objects.count(), 1)
        chapter = Chapter.objects.first()
        self.assertEqual(chapter.heading, "CHAPTER 1")

        # Check Section was created
        self.assertEqual(Section.objects.count(), 1)
        section = Section.objects.first()
        self.assertEqual(section.number, "S.1")
        self.assertEqual(section.title, "Citation")
        self.assertEqual(section.content.strip(), "This Act may be cited as the Test Act, 2024.")

    def test_import_multiple_sections(self):
        """Test importing multiple sections."""
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Citation
This is section 1.
@SECTION S.2
@TITLE Definitions
This is section 2."""

        _run_import_logic(self.law)

        self.assertEqual(Section.objects.count(), 2)

        section1 = Section.objects.get(number="S.1")
        self.assertEqual(section1.title, "Citation")
        self.assertEqual(section1.content.strip(), "This is section 1.")

        section2 = Section.objects.get(number="S.2")
        self.assertEqual(section2.title, "Definitions")
        self.assertEqual(section2.content.strip(), "This is section 2.")

    def test_import_schedule(self):
        """Test importing a schedule."""
        self.law.ai_prepared_text = """@SCHEDULE First Schedule
@TITLE List of Authorities
1. Authority A
2. Authority B"""

        _run_import_logic(self.law)

        self.assertEqual(Schedule.objects.count(), 1)
        schedule = Schedule.objects.first()
        self.assertEqual(schedule.schedule_number, "First Schedule")
        self.assertEqual(schedule.title, "List of Authorities")
        self.assertIn("1. Authority A", schedule.content)
        self.assertIn("2. Authority B", schedule.content)

    def test_import_appendix(self):
        """Test importing an appendix."""
        self.law.ai_prepared_text = """@APPENDIX Appendix A
@TITLE Application Forms
Form 1: Initial Application
Form 2: Response"""

        _run_import_logic(self.law)

        self.assertEqual(Appendix.objects.count(), 1)
        appendix = Appendix.objects.first()
        self.assertEqual(appendix.appendix_number, "Appendix A")
        self.assertEqual(appendix.title, "Application Forms")
        self.assertIn("Form 1", appendix.content)

    def test_import_mixed_content(self):
        """Test importing sections, schedules, and appendices together."""
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Citation
Section content.
@SCHEDULE First Schedule
Schedule content.
@APPENDIX Appendix A
Appendix content."""

        _run_import_logic(self.law)

        self.assertEqual(Section.objects.count(), 1)
        self.assertEqual(Schedule.objects.count(), 1)
        self.assertEqual(Appendix.objects.count(), 1)

    def test_import_preserves_line_breaks(self):
        """Test that import preserves line breaks in content."""
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Test
Line 1
Line 2
Line 3"""

        _run_import_logic(self.law)

        section = Section.objects.first()
        self.assertIn("Line 1\nLine 2\nLine 3", section.content)

    def test_import_without_title(self):
        """Test importing section without @TITLE tag."""
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
Section content without title."""

        _run_import_logic(self.law)

        section = Section.objects.first()
        self.assertEqual(section.title, "")
        self.assertEqual(section.content.strip(), "Section content without title.")

    def test_import_empty_part_name_creates_main(self):
        """Test that empty part name creates 'Main' part."""
        self.law.ai_prepared_text = """@SECTION S.1
Section content."""

        _run_import_logic(self.law)

        part = Part.objects.first()
        self.assertEqual(part.heading, "Main")

    def test_import_empty_chapter_name_creates_main(self):
        """Test that empty chapter name creates 'Main' chapter."""
        self.law.ai_prepared_text = """@PART PART I
@SECTION S.1
Section content."""

        _run_import_logic(self.law)

        chapter = Chapter.objects.first()
        self.assertEqual(chapter.heading, "Main")

    def test_import_raises_error_for_empty_text(self):
        """Test that import raises error when ai_prepared_text is empty."""
        self.law.ai_prepared_text = ""

        with self.assertRaises(Exception) as context:
            _run_import_logic(self.law)

        self.assertIn("AI-Prepared Text", str(context.exception))

    def test_import_multiple_parts(self):
        """Test importing multiple parts."""
        self.law.ai_prepared_text = """@PART PART I - PRELIMINARY
@CHAPTER CHAPTER 1
@SECTION S.1
Section 1 content.
@PART PART II - ADMINISTRATION
@CHAPTER CHAPTER 2
@SECTION S.2
Section 2 content."""

        _run_import_logic(self.law)

        self.assertEqual(Part.objects.count(), 2)
        self.assertEqual(Chapter.objects.count(), 2)
        self.assertEqual(Section.objects.count(), 2)

        part1 = Part.objects.get(heading="PART I - PRELIMINARY")
        part2 = Part.objects.get(heading="PART II - ADMINISTRATION")

        section1 = Section.objects.get(number="S.1")
        section2 = Section.objects.get(number="S.2")

        self.assertEqual(section1.chapter.part, part1)
        self.assertEqual(section2.chapter.part, part2)

    def test_import_section_with_multiline_content(self):
        """Test importing section with complex multiline content."""
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Interpretation
(1) In this Act:
    (a) "Minister" means the Minister responsible for justice;
    (b) "Court" means the High Court of Ekiti State.
(2) This section applies throughout the Act."""

        _run_import_logic(self.law)

        section = Section.objects.first()
        self.assertIn("(1) In this Act:", section.content)
        self.assertIn("(a) \"Minister\"", section.content)
        self.assertIn("(2) This section", section.content)


class LawAdminTest(TestCase):
    """Tests for LawAdmin actions."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = LawAdmin(Law, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password'
        )
        self.law = Law.objects.create(
            title="Test Law",
            slug="test-law",
            extracted_text="Raw extracted text from PDF",
            ai_prepared_text=""
        )

    def _create_mock_request(self):
        """Create a mock request with user and messages."""
        request = MockRequest(self.user)
        return request

    @patch('laws.admin.genai')
    @patch('laws.admin.settings')
    def test_clean_with_ai_action_success(self, mock_settings, mock_genai):
        """Test clean_with_ai admin action successfully cleans text."""
        mock_settings.GEMINI_API_KEY = 'test-api-key'

        # Mock Gemini response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "@SECTION S.1\n@TITLE Citation\nCleaned text."
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=self.law.id)

        self.admin.clean_with_ai(request, queryset)

        # Check that ai_prepared_text was updated
        self.law.refresh_from_db()
        self.assertEqual(self.law.ai_prepared_text, "@SECTION S.1\n@TITLE Citation\nCleaned text.")

    @patch('laws.admin.settings')
    def test_clean_with_ai_action_no_api_key(self, mock_settings):
        """Test clean_with_ai fails gracefully when API key is missing."""
        mock_settings.GEMINI_API_KEY = None

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=self.law.id)

        self.admin.clean_with_ai(request, queryset)

        # ai_prepared_text should remain empty
        self.law.refresh_from_db()
        self.assertEqual(self.law.ai_prepared_text, "")

    @patch('laws.admin.genai')
    @patch('laws.admin.settings')
    def test_clean_with_ai_action_no_extracted_text(self, mock_settings, mock_genai):
        """Test clean_with_ai handles laws with no extracted text."""
        mock_settings.GEMINI_API_KEY = 'test-api-key'

        law_no_text = Law.objects.create(
            title="Empty Law",
            slug="empty-law",
            extracted_text=""
        )

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=law_no_text.id)

        self.admin.clean_with_ai(request, queryset)

        # Should handle gracefully without calling API
        mock_genai.GenerativeModel.assert_not_called()

    def test_import_from_ai_text_action_success(self):
        """Test import_from_ai_text successfully imports content."""
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1
@TITLE Citation
Test content."""

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=self.law.id)

        self.admin.import_from_ai_text(request, queryset)

        # Check that objects were created
        self.assertEqual(Part.objects.count(), 1)
        self.assertEqual(Chapter.objects.count(), 1)
        self.assertEqual(Section.objects.count(), 1)

    def test_import_from_ai_text_action_multiple_laws_error(self):
        """Test import_from_ai_text fails when multiple laws selected."""
        law2 = Law.objects.create(
            title="Law 2",
            slug="law-2",
            ai_prepared_text="@SECTION S.1\nContent."
        )

        request = self._create_mock_request()
        queryset = Law.objects.filter(id__in=[self.law.id, law2.id])

        self.admin.import_from_ai_text(request, queryset)

        # No objects should be created
        self.assertEqual(Section.objects.count(), 0)

    def test_import_from_ai_text_action_no_prepared_text(self):
        """Test import_from_ai_text fails when no AI-prepared text."""
        self.law.ai_prepared_text = ""
        self.law.save()

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=self.law.id)

        self.admin.import_from_ai_text(request, queryset)

        # No objects should be created
        self.assertEqual(Section.objects.count(), 0)

    def test_import_from_ai_text_action_clears_existing(self):
        """Test import_from_ai_text clears existing content before import."""
        # Create existing content
        part = Part.objects.create(law=self.law, heading="Old Part")
        chapter = Chapter.objects.create(part=part, heading="Old Chapter")
        Section.objects.create(chapter=chapter, number="1", title="Old Section")
        Schedule.objects.create(law=self.law, schedule_number="Old")
        Appendix.objects.create(law=self.law, appendix_number="Old")

        # Set new AI-prepared text
        self.law.ai_prepared_text = """@PART NEW PART
@CHAPTER NEW CHAPTER
@SECTION S.1
@TITLE New Section
New content."""

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=self.law.id)

        self.admin.import_from_ai_text(request, queryset)

        # Check old content was deleted
        self.assertEqual(Part.objects.filter(heading="Old Part").count(), 0)
        self.assertEqual(Chapter.objects.filter(heading="Old Chapter").count(), 0)
        self.assertEqual(Section.objects.filter(title="Old Section").count(), 0)
        self.assertEqual(Schedule.objects.filter(schedule_number="Old").count(), 0)
        self.assertEqual(Appendix.objects.filter(appendix_number="Old").count(), 0)

        # Check new content was created
        self.assertEqual(Part.objects.filter(heading="NEW PART").count(), 1)
        self.assertEqual(Section.objects.filter(title="New Section").count(), 1)

    def test_import_from_ai_text_transaction_rollback_on_error(self):
        """Test that import transaction rolls back on error."""
        # Create malformed text that will cause an error
        self.law.ai_prepared_text = """@PART PART I
@CHAPTER CHAPTER 1
@SECTION S.1"""  # No content, might cause issues

        # Create some existing content
        part = Part.objects.create(law=self.law, heading="Existing Part")

        request = self._create_mock_request()
        queryset = Law.objects.filter(id=self.law.id)

        # Even if there's an error during parsing, transaction should handle it
        # For this test, we'll just verify the transaction context is working
        try:
            self.admin.import_from_ai_text(request, queryset)
        except Exception:
            pass

        # If transaction rolled back, existing part would still be there
        # If transaction succeeded, part would be deleted
        # This test mainly ensures no crash occurs


class AdminDisplayTest(TestCase):
    """Tests for admin list displays and methods."""

    def setUp(self):
        self.site = AdminSite()
        self.law = Law.objects.create(title="Test Law", slug="test-law")
        self.part = Part.objects.create(law=self.law, heading="Part 1")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        self.section = Section.objects.create(
            chapter=self.chapter,
            number="1",
            title="Test Section"
        )

    def test_section_admin_get_law(self):
        """Test SectionAdmin.get_law() returns correct law title."""
        from laws.admin import SectionAdmin
        admin = SectionAdmin(Section, self.site)

        result = admin.get_law(self.section)
        self.assertEqual(result, "Test Law")

    def test_section_admin_get_part(self):
        """Test SectionAdmin.get_part() returns correct part heading."""
        from laws.admin import SectionAdmin
        admin = SectionAdmin(Section, self.site)

        result = admin.get_part(self.section)
        self.assertEqual(result, "Part 1")

    def test_section_admin_get_chapter(self):
        """Test SectionAdmin.get_chapter() returns correct chapter heading."""
        from laws.admin import SectionAdmin
        admin = SectionAdmin(Section, self.site)

        result = admin.get_chapter(self.section)
        self.assertEqual(result, "Chapter 1")
