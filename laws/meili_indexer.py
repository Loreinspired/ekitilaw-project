from django_meili.meili import meili_client
from laws.models import Section, Schedule, Appendix, Law
from django.conf import settings

INDEX_NAME = getattr(settings, "MEILI_INDEX_NAME", "laws")

def build_section_doc(section):
    law = section.chapter.part.law
    return {
        "id": f"section-{section.id}",
        "result_type": "Section",
        "law_id": law.id,
        "law_title": law.title,
        "law_slug": law.slug or "",
        "anchor_tag": f"section-{section.id}",
        "part_heading": section.chapter.part.heading or "",
        "chapter_heading": section.chapter.heading or "",
        "section_number": section.number,
        "section_title": section.title or "",
        "content": section.content or "",
    }

def build_schedule_doc(schedule):  # example
    law = schedule.law  # adapt to your model
    return {
        "id": f"schedule-{schedule.id}",
        "result_type": "Schedule",
        "law_id": law.id,
        "law_title": law.title,
        "law_slug": law.slug or "",
        "anchor_tag": f"schedule-{schedule.id}",
        "title": schedule.title or "",
        "content": schedule.content or "",
    }

def setup_index(index):
    index.update_searchable_attributes([
        "law_title", "section_title", "content", "part_heading", "chapter_heading"
    ])
    index.update_displayed_attributes(["*"])
    index.update_filterable_attributes(["law_slug", "result_type", "law_id"])

def rebuild_meili_index():
    client = meili_client
    index = client.index(INDEX_NAME)
    # optionally delete and recreate index if needed:
    # client.delete_index(INDEX_NAME)
    setup_index(index)

    docs = []
    for s in Section.objects.select_related("chapter", "chapter__part", "chapter__part__law").all():
        docs.append(build_section_doc(s))

    # add schedules/appendices similarly
    index.add_documents(docs)
    return len(docs)
