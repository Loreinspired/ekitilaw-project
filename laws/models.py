# laws/models.py

from django.db import models
from django.utils.text import slugify
from django_meili.models import IndexMixin
import fitz
import io

class Law(models.Model):
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(max_length=500, blank=True, unique=True)
    enactment_date = models.DateField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='law_pdfs/', null=True, blank=True)
    source_notes = models.TextField(blank=True, null=True)
    extracted_text = models.TextField(blank=True, null=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        try:
            this_instance = Law.objects.get(id=self.id)
            if this_instance.pdf_file != self.pdf_file and self.pdf_file:
                self.extract_text_from_pdf()
        except Law.DoesNotExist:
            if self.pdf_file:
                pass

        super().save(*args, **kwargs)

        if self.pdf_file and not self.extracted_text:
            self.extract_text_from_pdf()
            super().save(update_fields=['extracted_text'])
            
    def extract_text_from_pdf(self):
        try:
            file_bytes = self.pdf_file.read()
            file_stream = io.BytesIO(file_bytes)
            with fitz.open(stream=file_stream, filetype="pdf") as doc:
                full_text = ""
                for page in doc:
                    full_text += page.get_text()
            self.extracted_text = full_text
        except Exception as e:
            self.extracted_text = f"Error extracting text: {e}"

    def __str__(self):
        return self.title

ai_prepared_text = models.TextField(blank=True, null=True, help_text="Cleaned, tagged text from the AI assistant.")

#
# --- SECTION MODEL (Corrected) ---
#
class Section(IndexMixin, models.Model):
    law = models.ForeignKey(Law, related_name='sections', on_delete=models.CASCADE)
    part_heading = models.CharField(max_length=500, blank=True, null=True, help_text="e.g., PART I - PRELIMINARY")
    chapter_heading = models.CharField(max_length=500, blank=True, null=True, help_text="e.g., Chapter 1: Offences")
    section_number = models.CharField(max_length=100)
    section_title = models.CharField(max_length=1000, blank=True, null=True, help_text="e.g., Definition")
    content = models.TextField()
    history_notes = models.TextField(blank=True, null=True)

    class MeiliMeta:
        index_name = 'sections'
        # --- THIS IS THE FIX ---
        searchable_fields = ['*'] # Index everything
        displayed_fields = ['*']  # Return everything
        # -----------------------

    @property
    def law_title(self):
        return self.law.title

    @property
    def law_slug(self):
        return self.law.slug

    def __str__(self):
        if self.section_title:
            return f"{self.law.title} - S.{self.section_number} ({self.section_title})"
        return f"{self.law.title} - S.{self.section_number}"

#
# --- SCHEDULE MODEL (Corrected) ---
#
class Schedule(IndexMixin, models.Model):
    law = models.ForeignKey(Law, related_name='schedules', on_delete=models.CASCADE)
    schedule_number = models.CharField(max_length=100, help_text="e.g., First Schedule")
    title = models.CharField(max_length=500, blank=True, null=True)
    content = models.TextField()

    class MeiliMeta:
        index_name = 'schedules'
        # --- THIS IS THE FIX ---
        searchable_fields = ['*'] # Index everything
        displayed_fields = ['*']  # Return everything
        # -----------------------

    @property
    def law_title(self):
        return self.law.title
        
    @property
    def law_slug(self):
        return self.law.slug

    def __str__(self):
        return f"{self.law.title} - {self.schedule_number}"

#
# --- APPENDIX MODEL (Corrected) ---
#
class Appendix(IndexMixin, models.Model):
    law = models.ForeignKey(Law, related_name='appendices', on_delete=models.CASCADE)
    appendix_number = models.CharField(max_length=100, help_text="e.g., Appendix A")
    title = models.CharField(max_length=500, blank=True, null=True)
    content = models.TextField()

    class MeiliMeta:
        index_name = 'appendices'
        # --- THIS IS THE FIX ---
        searchable_fields = ['*'] # Index everything
        displayed_fields = ['*']  # Return everything
        # -----------------------

    @property
    def law_title(self):
        return self.law.title

    @property
    def law_slug(self):
        return self.law.slug

    def __str__(self):
        return f"{self.law.title} - {self.appendix_number}"