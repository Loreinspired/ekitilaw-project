# laws/views.py

from django.shortcuts import render, get_object_or_404
from .models import Law, Section, Schedule, Appendix # Make sure Law is imported
import meilisearch
from django.conf import settings

def search(request):
    """
    This is our main search view.
    """
    
    url = f"http://{settings.MEILISEARCH['HOST']}:{settings.MEILISEARCH['PORT']}"
    key = settings.MEILISEARCH['MASTER_KEY']
    client = meilisearch.Client(url, key)

    query = request.GET.get('q', '') 
    
    search_results = []
    
    if query:
        search_options = {
            'attributesToHighlight': ['*'],
            'highlightPreTag': '<b>',
            'highlightPostTag': '</b>',
        }
        
        # --- 1. Get all search hits ---
        section_hits = client.index('sections').search(query, search_options).get('hits', [])
        for hit in section_hits:
            hit['result_type'] = 'Section'
            hit['highlight'] = hit.get('_formatted', {}) # <-- Fix for _formatted
            search_results.append(hit)
            
        schedule_hits = client.index('schedules').search(query, search_options).get('hits', [])
        for hit in schedule_hits:
            hit['result_type'] = 'Schedule'
            hit['highlight'] = hit.get('_formatted', {}) # <-- Fix for _formatted
            search_results.append(hit)

        appendix_hits = client.index('appendices').search(query, search_options).get('hits', [])
        for hit in appendix_hits:
            hit['result_type'] = 'Appendix'
            hit['highlight'] = hit.get('_formatted', {}) # <-- Fix for _formatted
            search_results.append(hit)
            
        # --- 2. THIS IS THE HYDRATION FIX ---
        # Get all unique Law IDs from the search results
        law_ids = {hit['law'] for hit in search_results if 'law' in hit}

        # Fetch all those Law objects from the database in one efficient query
        laws = Law.objects.in_bulk(law_ids)

        # 3. Hydrate the search results with the data they are missing
        for hit in search_results:
            law_object = laws.get(hit.get('law'))
            if law_object:
                # Add the missing data to the 'hit' dictionary
                hit['law_title'] = law_object.title
                hit['law_slug'] = law_object.slug
            else:
                hit['law_title'] = "Error: Law not found"
                hit['law_slug'] = "" # This will be blank and still fail
        # ---------------------------

    context = {
        'query': query,
        'results': search_results,
    }
    
    return render(request, 'laws/search_results.html', context)


# --- LAW DETAIL VIEW (UNCHANGED) ---
def law_detail(request, law_slug):
    law = get_object_or_404(Law, slug=law_slug)
    sections = law.sections.all().order_by('id')
    schedules = law.schedules.all().order_by('id')
    appendices = law.appendices.all().order_by('id')
    
    context = {
        'law': law,
        'sections': sections,
        'schedules': schedules,
        'appendices': appendices,
    }
    
    return render(request, 'laws/law_detail.html', context)