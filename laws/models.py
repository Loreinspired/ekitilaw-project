from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class Law(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    enactment_date = models.DateField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='pdfs/', blank=True, null=True)
    source_notes = models.TextField(blank=True, default='')
    extracted_text = models.TextField(blank=True, default='')
    ai_prepared_text = models.TextField(blank=True, default='')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("laws:law_detail", kwargs={"law_slug": self.slug})


class Part(models.Model):
    law = models.ForeignKey(Law, related_name="parts", on_delete=models.CASCADE)
    heading = models.CharField(max_length=255, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order",)


class Chapter(models.Model):
    part = models.ForeignKey(Part, related_name="chapters", on_delete=models.CASCADE)
    heading = models.CharField(max_length=255, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order",)


class Section(models.Model):
    chapter = models.ForeignKey(Chapter, related_name="sections", on_delete=models.CASCADE)
    number = models.CharField(max_length=50)  # "1", "2A", etc
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("chapter", "number")
        ordering = ("order",)

    def law(self):
        # helper property to reach parent law object
        return self.chapter.part.law

    def anchor_tag(self):
        return f"section-{self.id}"

    def get_absolute_url(self):
        return f"{self.law().get_absolute_url()}#section-{self.id}"

    def __str__(self):
        return f"S.{self.number} — {self.title or '[No Title]'}"


class Schedule(models.Model):
    law = models.ForeignKey(Law, related_name="schedules", on_delete=models.CASCADE)
    schedule_number = models.CharField(max_length=50)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)

    def __str__(self):
        return f"{self.schedule_number} - {self.title}"

    def anchor_tag(self):
        return f"schedule-{self.id}"


class Appendix(models.Model):
    law = models.ForeignKey(Law, related_name="appendices", on_delete=models.CASCADE)
    appendix_number = models.CharField(max_length=50)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)

    def __str__(self):
        return f"{self.appendix_number} - {self.title}"

    def anchor_tag(self):
        return f"appendix-{self.id}"
