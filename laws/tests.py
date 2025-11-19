from django.test import TestCase, Client
from django.urls import reverse
from .models import Law, Part, Chapter, Section

class LawDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.law = Law.objects.create(title="Test Law", slug="test-law")
        self.part = Part.objects.create(law=self.law, heading="Part 1")
        self.chapter = Chapter.objects.create(part=self.part, heading="Chapter 1")
        self.section = Section.objects.create(chapter=self.chapter, number="1", title="Section 1", content="Content 1")

    def test_law_detail_view(self):
        url = reverse("laws:law_detail", kwargs={"law_slug": self.law.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Law")
        self.assertContains(response, "Part 1")
        self.assertContains(response, "Chapter 1")
        self.assertContains(response, "Section 1")
        self.assertContains(response, "Content 1")
