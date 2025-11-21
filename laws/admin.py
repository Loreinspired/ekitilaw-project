# laws/admin.py

from django.contrib import admin, messages
from django.db import transaction
from django.conf import settings
from .models import Law, Part, Chapter, Section, Schedule, Appendix

# Try to import Gemini AI (optional)
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
    # Configure the Gemini API
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

# --- This is the AI's "Brain" (Unchanged) ---
AI_SYSTEM_PROMPT = """You are a legal formatting assistant. Your ONLY job is to take raw, messy text from a PDF of a law and convert it into a clean, tagged text file.

You must follow these rules strictly:
1.  **DO NOT** change, rephrase, summarize, or alter ANY of the legal text. The output text must be 100% identical to the input text, character for character.
2.  **REMOVE** all page headers, page footers, and page numbers.
3.  **FIX** any weird encoding errors or broken characters (like '0x96').
4.  **ADD** the following tags on their own line to identify the structure:
    * `@PART [Part Title]` (e.g., @PART PART I - PRELIMINARY)
    * `@CHAPTER [Chapter Title]` (e.g., @CHAPTER CHAPTER 1)
    * `@SECTION [Section Number]` (e.g., @SECTION S.1)
    * `@TITLE [Section Title]` (e.g., @TITLE Citation)
    * `@SCHEDULE [Schedule Number/Title]` (e.g., @SCHEDULE FIRST SCHEDULE)
    * `@APPENDIX [Appendix Number/Title]` (e.g., @APPENDIX APPENDIX A)
5.  All text that is not a tag is considered the 'content' of the previous tag.
6.  Preserve all original line breaks and indentation of the legal text itself.

Your output must be ONLY the cleaned, tagged text. Do not add any conversational text like "Here is the cleaned text:"."""

# --- Helper functions for the importer ---

def _run_import_logic(law_object):
    """Parses the text and creates objects."""
    text_to_import = law_object.ai_prepared_text
    if not text_to_import:
        raise Exception("The 'AI-Prepared Text' field is empty. Cannot import.")

    lines = text_to_import.splitlines()
    
    current_part = None
    current_chapter = None
    current_item = None 
    content_buffer = []
    
    # Helper to get/create part/chapter
    def get_part(heading):
        # If heading is empty, we might want a default part or reuse the last one?
        # For now, let's create a part with the heading.
        # Note: This logic is simplified. In a real app, we might want to track order.
        # We'll use 'get_or_create' but we need to be careful about order.
        # Let's just create them as we encounter them.
        if not heading:
             heading = "Main"
        return Part.objects.get_or_create(law=law_object, heading=heading)[0]

    def get_chapter(part, heading):
        if not heading:
            heading = "Main"
        return Chapter.objects.get_or_create(part=part, heading=heading)[0]

    # Reset variables for the loop
    current_part_name = ""
    current_chapter_name = ""
    
    for line in lines:
        line_stripped = line.strip()
        
        new_tag_found = False
        new_item = None

        if line_stripped.startswith('@PART '):
            new_tag_found = True
            current_part_name = line_stripped.replace('@PART ', '', 1)
            current_chapter_name = "" 
        elif line_stripped.startswith('@CHAPTER '):
            new_tag_found = True
            current_chapter_name = line_stripped.replace('@CHAPTER ', '', 1)
        elif line_stripped.startswith('@SECTION '):
            new_tag_found = True
            new_item = {'type': 'section', 'part': current_part_name, 'chapter': current_chapter_name}
            new_item['number'] = line_stripped.replace('@SECTION ', '', 1)
        elif line_stripped.startswith('@TITLE '):
            if current_item:
                current_item['title'] = line_stripped.replace('@TITLE ', '', 1)
        elif line_stripped.startswith('@SCHEDULE '):
            new_tag_found = True
            new_item = {'type': 'schedule'}
            new_item['number'] = line_stripped.replace('@SCHEDULE ', '', 1)
        elif line_stripped.startswith('@APPENDIX '):
            new_tag_found = True
            new_item = {'type': 'appendix'}
            new_item['number'] = line_stripped.replace('@APPENDIX ', '', 1)
        
        if new_tag_found:
            if current_item:
                content = "\n".join(content_buffer).strip()
                item_type = current_item.get('type')
                
                if item_type == 'section':
                    part = get_part(current_item.get('part', ''))
                    chapter = get_chapter(part, current_item.get('chapter', ''))
                    Section.objects.create(
                        chapter=chapter,
                        number=current_item.get('number', ''),
                        title=current_item.get('title', ''),
                        content=content
                    )
                elif item_type == 'schedule':
                    Schedule.objects.create(
                        law=law_object,
                        schedule_number=current_item.get('number', ''),
                        title=current_item.get('title', ''),
                        content=content
                    )
                elif item_type == 'appendix':
                    Appendix.objects.create(
                        law=law_object,
                        appendix_number=current_item.get('number', ''),
                        title=current_item.get('title', ''),
                        content=content
                    )
            
            current_item = new_item
            content_buffer = []
        
        elif not line_stripped.startswith('@TITLE ') and current_item:
            content_buffer.append(line)

    # Save the last item
    if current_item:
        content = "\n".join(content_buffer).strip()
        item_type = current_item.get('type')
        if item_type == 'section':
            part = get_part(current_item.get('part', ''))
            chapter = get_chapter(part, current_item.get('chapter', ''))
            Section.objects.create(
                chapter=chapter,
                number=current_item.get('number', ''),
                title=current_item.get('title', ''),
                content=content
            )
        elif item_type == 'schedule':
            Schedule.objects.create(
                law=law_object,
                schedule_number=current_item.get('number', ''),
                title=current_item.get('title', ''),
                content=content
            )
        elif item_type == 'appendix':
            Appendix.objects.create(
                law=law_object,
                appendix_number=current_item.get('number', ''),
                title=current_item.get('title', ''),
                content=content
            )

# --- End of helper functions ---

# SectionInline removed as it is not compatible with normalized models in LawAdmin

class ScheduleInline(admin.StackedInline):
    model = Schedule
    extra = 0
    classes = ['collapse']

class AppendixInline(admin.StackedInline):
    model = Appendix
    extra = 0
    classes = ['collapse']

@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display = ('title', 'enactment_date', 'slug')
    search_fields = ('title',)
    
    fieldsets = (
        ('Law Details', {
            'fields': ('title', 'enactment_date', 'pdf_file', 'source_notes')
        }),
        ('PDF Extractor (Step 1)', {
            'classes': ('collapse',),
            'fields': ('extracted_text',),
        }),
        ('AI Cleaning (Step 2 & 3)', {
            'classes': ('collapse', 'wide'),
            'fields': ('ai_prepared_text',),
            'description': 'Click "Clean with AI" action to populate this. Review text, then run "Import from AI text" action.'
        }),
    )
    readonly_fields = ('extracted_text',)
    inlines = [] 
    
    actions = ['clean_with_ai', 'import_from_ai_text']

    @admin.action(description='Step 1: Clean selected laws with AI')
    def clean_with_ai(self, request, queryset):
        if not GENAI_AVAILABLE:
            self.message_user(request, "Google Generative AI is not installed. Install it with: pip install google-generativeai", level=messages.ERROR)
            return

        if not settings.GEMINI_API_KEY:
            self.message_user(request, "GEMINI_API_KEY is not configured in settings.", level=messages.ERROR)
            return

        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        
        updated_count = 0
        for law in queryset:
            if not law.extracted_text:
                self.message_user(request, f"Law '{law.title}' has no extracted text to clean.", level=messages.WARNING)
                continue
            
            try:
                response = model.generate_content([AI_SYSTEM_PROMPT, law.extracted_text])
                law.ai_prepared_text = response.text
                law.save(update_fields=['ai_prepared_text'])
                updated_count += 1
            except Exception as e:
                self.message_user(request, f"Error cleaning '{law.title}': {e}", level=messages.ERROR)
        
        if updated_count > 0:
            self.message_user(request, f"Successfully cleaned and prepared text for {updated_count} law(s). Please review the text, then run Step 2.", level=messages.SUCCESS)

    @admin.action(description='Step 2: Import from AI-prepared text')
    def import_from_ai_text(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "This action can only be run on one law at a time.", level=messages.ERROR)
            return

        law = queryset.first()
        
        if not law.ai_prepared_text:
            self.message_user(request, f"'{law.title}' has no AI-prepared text. Please run Step 1 first.", level=messages.ERROR)
            return

        try:
            with transaction.atomic():
                # SAFETY SWITCH: Clear all existing content
                law.parts.all().delete() # Cascades to chapters and sections
                law.schedules.all().delete()
                law.appendices.all().delete()
                
                # Run the new bulk import logic
                _run_import_logic(law)
            
            self.message_user(request, f"Successfully imported all content for '{law.title}'.", level=messages.SUCCESS)
            self.message_user(request, "You must now run syncindex in your terminal to make this new data searchable.", level=messages.WARNING)
        
        except Exception as e:
            self.message_user(request, f"An error occurred: {e}. Transaction has been rolled back.", level=messages.ERROR)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('number', 'get_law', 'get_part', 'get_chapter')
    list_filter = ('chapter__part__law',)
    search_fields = ['number', 'title', 'content', 'chapter__part__law__title']

    def get_law(self, obj):
        return obj.chapter.part.law.title
    get_law.short_description = 'Law'

    def get_part(self, obj):
        return obj.chapter.part.heading
    get_part.short_description = 'Part'

    def get_chapter(self, obj):
        return obj.chapter.heading
    get_chapter.short_description = 'Chapter'

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_number', 'law', 'title')
    list_filter = ('law',)
    search_fields = ['schedule_number', 'title', 'content', 'law__title']

@admin.register(Appendix)
class AppendixAdmin(admin.ModelAdmin):
    list_display = ('appendix_number', 'law', 'title')
    list_filter = ('law',)
    search_fields = ['appendix_number', 'title', 'content', 'law__title']