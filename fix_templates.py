import os
from pathlib import Path

# Define the base directory (assuming this script is next to manage.py)
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / 'templates'
BASE_HTML_PATH = TEMPLATES_DIR / 'base.html'

# HTML Content
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ekitilaw - {% block title %}Search{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body { font-family: 'Inter', sans-serif; background-color: #f4f7f9; }</style>
</head>
<body>
    <nav class="bg-white shadow-sm p-4 sticky top-0 z-10">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/" class="text-2xl font-bold text-gray-900 hover:text-blue-600 transition duration-150">Ekitilaw</a>
            <div class="space-x-4"><a href="/search" class="text-gray-600 hover:text-blue-600">Search</a></div>
        </div>
    </nav>
    <main class="min-h-screen">
        {% block content %}
        {% endblock content %}
    </main>
    <footer class="bg-gray-800 text-white p-4 text-center mt-8">
        <p>&copy; {% now "Y" %} Ekitilaw Project</p>
    </footer>
</body>
</html>"""

# Create directory if it doesn't exist
if not TEMPLATES_DIR.exists():
    print(f"Creating directory: {TEMPLATES_DIR}")
    os.makedirs(TEMPLATES_DIR)

# Write the file
print(f"Writing file to: {BASE_HTML_PATH}")
with open(BASE_HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Done! Base template created successfully.")