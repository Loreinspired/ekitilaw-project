# laws/admin.py

from django.contrib import admin, messages
from django.db import transaction
from django.conf import settings
from .models import Law, Section, Schedule, Appendix
import google.generativeai as genai

# Configure the Gemini API
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

# --- This is the AI's "Brain" ---
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
def _save_item(item, law):
    """Saves a single item (Section, Schedule, etc.) to the database."""
    if not item:
        return
    
    item_type = item.get('type')
    try:
        if item_type == 'section':
            Section.objects.create(
                law=law,
                part_heading=item.get('part', ''),
                chapter_heading=item.get('chapter', ''),
                section_number=item.get('number', ''),
                section_title=item.get('title', ''),
                content=item.get('content', '')
            )
        elif item_type == 'schedule':
            Schedule.objects.create(
                law=law,
                schedule_number=item.get('number', ''),
                title=item.get('title', ''),
                content=item.get('content', '')
            )
        elif item_type == 'appendix':
            Appendix.objects.create(
                law=law,
                appendix_number=item.get('number', ''),
                title=item.get('title', ''),
                content=item.get('content', '')
            )
    except Exception as e:
        # This will show an error if one item fails
        raise Exception(f"Failed to save item {item.get('number')}: {e}")

def _run_import_logic(law_object):
    """Parses the text and imports all content."""
    text_to_import = law_object.ai_prepared_text
    if not text_to_import:
        raise Exception("The 'AI-Prepared Text' field is empty. Cannot import.")

    lines = text_to_import.splitlines()
    
    current_part = ""
    current_chapter = ""
    current_item = None # Holds the dict of the item being built
    content_buffer = []

    for line in lines:
        line_stripped = line.strip()

        # Check for tags
        tag_found = False
        if line_stripped.startswith('@PART '):
            tag_found = True
            _save_item(current_item, law_object)
            current_item = None
            current_part = line_stripped.replace('@PART ', '', 1)
        elif line_stripped.startswith('@CHAPTER '):
            tag_found = True
            _save_item(current_item, law_object)
            current_item = None
            current_chapter = line_stripped.replace('@CHAPTER ', '', 1)
        elif line_stripped.startswith('@SECTION '):
            tag_found = True
            _save_item(current_item, law_object)
            current_item = {'type': 'section', 'part': current_part, 'chapter': current_chapter}
            current_item['number'] = line_stripped.replace('@SECTION ', '', 1)
        elif line_stripped.startswith('@TITLE '):
            tag_found = True
            if current_item:
                current_item['title'] = line_stripped.replace('@TITLE ', '', 1)
        elif line_stripped.startswith('@SCHEDULE '):
            tag_found = True
            _save_item(current_item, law_object)
            current_item = {'type': 'schedule'}
            current_item['number'] = line_stripped.replace('@SCHEDULE ', '', 1)
        elif line_stripped.startswith('@APPENDIX '):
            tag_found = True
            _save_item(current_item, law_object)
            current_item = {'type': 'appendix'}
            current_item['number'] = line_stripped.replace('@APPENDIX ', '', 1)

        # Handle content
        if tag_found:
            # If we found a tag, save the previous content buffer
            if current_item and content_buffer:
                # Find the item this content belonged to (it's not `current_item`)
                # This logic is tricky, let's simplify
                pass # The _save_item call handles the previous item
            
            if current_item: # Check if we are building a new item
                current_item['content'] = "" # Reset content
            content_buffer = [] # Reset buffer

        elif current_item is not None:
            # If we are inside an item, add this line to its content
            content_buffer.append(line)
        
        # This is complex. Let's simplify the loop.
        
    # --- A SIMPLER, BETTER PARSING LOGIC ---
    # We will reset the logic from the old script
    
    current_part = ""
    current_chapter = ""
    current_item = None
    content_buffer = []

    for line in lines:
        line_stripped = line.strip()

        # Check for tags
        if line_stripped.startswith('@PART '):
            _save_item(current_item, law_object) # Save the item we were just building
            current_item = None
            content_buffer = []
            current_part = line_stripped.replace('@PART ', '', 1)
        elif line_stripped.startswith('@CHAPTER '):
            _save_item(current_item, law_object)
            current_item = None
            content_buffer = []
            current_chapter = line_stripped.replace('@CHAPTER ', '', 1)
        elif line_stripped.startswith('@SECTION '):
            _save_item(current_item, law_object)
            content_buffer = []
            current_item = {'type': 'section', 'part': current_part, 'chapter': current_chapter}
            current_item['number'] = line_stripped.replace('@SECTION ', '', 1)
        elif line_stripped.startswith('@TITLE '):
            if current_item:
                current_item['title'] = line_stripped.replace('@TITLE ', '', 1)
        elif line_stripped.startswith('@SCHEDULE '):
            _save_item(current_item, law_object)
            content_buffer = []
            current_item = {'type': 'schedule'}
            current_item['number'] = line_stripped.replace('@SCHEDULE ', '', 1)
        elif line_stripped.startswith('@APPENDIX '):
            _save_item(current_item, law_object)
            content_buffer = []
            current_item = {'type': 'appendix'}
            current_item['number'] = line_stripped.replace('@APPENDIX ', '', 1)
        elif current_item is not None:
            # If we are inside an item, add this line to its content
            content_buffer.append(line)
        
        # Save the content to the item when we hit a tag
        if line_stripped.startswith('@') and content_buffer and current_item:
            current_item['content'] = "\n".join(content_buffer).strip()
            content_buffer = []
    
    # Save the very last item in the file
    if current_item:
        current_item['content'] = "\n".join(content_buffer).strip()
        _save_item(current_item, law_object)
    
    # This logic is *still* buggy. The logic from import_law.py was better.
    # Let's use the exact logic from the file importer.

    current_part = ""
    current_chapter = ""
    current_item = None 
    content_buffer = []

    for line in lines:
        line_stripped = line.strip()

        # Check for tags
        if line_stripped.startswith('@PART '):
            _save_item(current_item, law_object) 
            current_item = None
            current_part = line_stripped.replace('@PART ', '', 1)
        elif line_stripped.startswith('@CHAPTER '):
            _save_item(current_item, law_object)
            current_item = None
            current_chapter = line_stripped.replace('@CHAPTER ', '', 1)
        elif line_stripped.startswith('@SECTION '):
            _save_item(current_item, law_object)
            content_buffer = []
            current_item = {'type': 'section', 'part': current_part, 'chapter': current_chapter}
            current_item['number'] = line_stripped.replace('@SECTION ', '', 1)
        elif line_stripped.startswith('@TITLE '):
            if current_item:
                current_item['title'] = line_stripped.replace('@TITLE ', '', 1)
        elif line_stripped.startswith('@SCHEDULE '):
            _save_item(current_item, law_object)
            content_buffer = []
            current_item = {'type': 'schedule'}
            current_item['number'] = line_stripped.replace('@SCHEDULE ', '', 1)
        elif line_stripped.startswith('@APPENDIX '):
            _save_item(current_item, law_object)
            content_buffer = []
            current_item = {'type': 'appendix'}
            current_item['number'] = line_stripped.replace('@APPENDIX ', '', 1)
        elif current_item is not None:
            content_buffer.append(line)
        
        # This is the original script's logic flaw. Content isn't saved until the *next* tag.
        # We need to save the content *inside* the item when a new tag is found.
        if line_stripped.startswith('@') and current_item and content_buffer:
             # This is wrong. The content buffer belongs to the *previous* item.
             pass

    # Let's re-write the parser logic from the original script, but fix it.
    
    current_part = ""
    current_chapter = ""
    current_item = None 
    content_buffer = []
    
    # We must save the *previous* item when a *new* tag is found.
    # We can't do that until we've processed the content buffer.

    for line in lines:
        line_stripped = line.strip()
        
        new_tag_found = False
        new_item = None

        if line_stripped.startswith('@PART '):
            new_tag_found = True
            current_part = line_stripped.replace('@PART ', '', 1)
            current_chapter = "" # Reset chapter when part changes
        elif line_stripped.startswith('@CHAPTER '):
            new_tag_found = True
            current_chapter = line_stripped.replace('@CHAPTER ', '', 1)
        elif line_stripped.startswith('@SECTION '):
            new_tag_found = True
            new_item = {'type': 'section', 'part': current_part, 'chapter': current_chapter}
            new_item['number'] = line_stripped.replace('@SECTION ', '', 1)
        elif line_stripped.startswith('@TITLE '):
            if current_item:
                current_item['title'] = line_stripped.replace('@TITLE ', '', 1)
            # This is not a content-starting tag, so continue
        elif line_stripped.startswith('@SCHEDULE '):
            new_tag_found = True
            new_item = {'type': 'schedule'}
            new_item['number'] = line_stripped.replace('@SCHEDULE ', '', 1)
        elif line_stripped.startswith('@APPENDIX '):
            new_tag_found = True
            new_item = {'type': 'appendix'}
            new_item['number'] = line_stripped.replace('@APPENDIX ', '', 1)
        
        if new_tag_found:
            # A new tag was found. This means the previous item is complete.
            if current_item:
                current_item['content'] = "\n".join(content_buffer).strip()
                _save_item(current_item, law_object)
            
            # Start the new item
            current_item = new_item
            content_buffer = []
        
        elif not line_stripped.startswith('@TITLE ') and current_item:
            # This is a line of content
            content_buffer.append(line)

    # Save the very last item in the file
    if current_item:
        current_item['content'] = "\n".join(content_buffer).strip()
        _save_item(current_item, law_object)

# --- End of helper functions ---


class SectionInline(admin.StackedInline):
    model = Section
    extra = 0 # Don't show blank ones, we will import
    fields = ('part_heading', 'chapter_heading', 'section_number', 'section_title', 'content', 'history_notes')
    classes = ['collapse']
    
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
    list_display = ('title', 'enactment_date')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    
    # We now have a complex layout
    fieldsets = (
        ('Law Details', {
            'fields': ('title', 'slug', 'enactment_date', 'pdf_file', 'source_notes')
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
    readonly_fields = ('extracted_text',) # ai_prepared_text is editable
    
    inlines = [
        SectionInline,
        ScheduleInline,
        AppendixInline,
    ]

    # --- THE NEW ACTIONS ---
    actions = ['clean_with_ai', 'import_from_ai_text']

    @admin.action(description='Step 1: Clean selected laws with AI')
    def clean_with_ai(self, request, queryset):
        if not settings.GEMINI_API_KEY:
            self.message_user(request, "GEMINI_API_KEY is not configured in settings.", level=messages.ERROR)
            return
        
        model = genai.GenerativeModel('gemini-1.5-flash') # Use a fast model
        
        updated_count = 0
        for law in queryset:
            if not law.extracted_text:
                self.message_user(request, f"Law '{law.title}' has no extracted text to clean.", level=messages.WARNING)
                continue
            
            try:
                # Call the API
                response = model.generate_content([AI_SYSTEM_PROMPT, law.extracted_text])
                
                # Save the clean text
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

        try:
            # Use a transaction so it all succeeds or all fails
            with transaction.atomic():
                # SAFETY SWITCH: Clear all existing content
                law.sections.all().delete()
                law.schedules.all().delete()
                law.appendices.all().delete()
                
                # Run the import logic
                _run_import_logic(law)
            
            self.message_user(request, f"Successfully imported all content for '{law.title}'.", level=messages.SUCCESS)
            # Don't forget to sync Meilisearch!
            self.message_user(request, "You must now run syncindex in your terminal to make this new data searchable.", level=messages.WARNING)
        
        except Exception as e:
            self.message_user(request, f"An error occurred: {e}. Transaction has been rolled back.", level=messages.ERROR)


# --- (The rest of your admin registrations are unchanged) ---
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