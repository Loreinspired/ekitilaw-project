# laws/admin.py

from django.contrib import admin
from .models import Law, Section, Schedule, Appendix

# --- 1. ADD 'classes' TO ALL INLINES ---
# This makes each inline section (Sections, Schedules, etc.)
# start as a collapsed bar.

class SectionInline(admin.StackedInline):
    model = Section
    extra = 1
    # --- ADD 'section_title' TO THIS LIST ---
    fields = ('part_heading', 'chapter_heading', 'section_number', 'section_title', 'content', 'history_notes')
    classes = ['collapse']

class ScheduleInline(admin.StackedInline):
    model = Schedule
    extra = 0
    classes = ['collapse']  # <-- ADD THIS LINE

class AppendixInline(admin.StackedInline):
    model = Appendix
    extra = 0
    classes = ['collapse']  # <-- ADD THIS LINE

# ---------------------------------------

@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display = ('title', 'enactment_date')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    
    # --- 2. USE 'fieldsets' TO MAKE THE TEXT FIELD COLLAPSIBLE ---
    # This replaces the simple 'readonly_fields' line to give us more control.
    
    fieldsets = (
        # This is the main, non-collapsible section for the Law's details
        (None, {
            'fields': ('title', 'slug', 'enactment_date', 'pdf_file', 'source_notes')
        }),
        # This is the new, collapsible section for your extracted text
        ('Extracted PDF Text (Click to expand)', {
            'classes': ('collapse',),  # <-- THIS MAKES IT COLLAPSIBLE
            'fields': ('extracted_text',),
        }),
    )
    
    # We must still define extracted_text as readonly
    readonly_fields = ('extracted_text',)
    
    # This part is unchanged
    inlines = [
        SectionInline,
        ScheduleInline,
        AppendixInline,
    ]

# --- (The rest of the file is unchanged) ---

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('section_number', 'law', 'part_heading', 'chapter_heading')
    search_fields = ('section_number', 'content', 'part_heading', 'chapter_heading')
    list_filter = ('law',)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_number', 'law', 'title')
    search_fields = ('schedule_number', 'title', 'content')
    list_filter = ('law',)

@admin.register(Appendix)
class AppendixAdmin(admin.ModelAdmin):
    list_display = ('appendix_number', 'law', 'title')
    search_fields = ('appendix_number', 'title', 'content')
    list_filter = ('law',)