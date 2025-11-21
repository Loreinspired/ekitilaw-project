# Laws App Test Suite

This directory contains comprehensive tests for the laws application.

## Test Structure

```
laws/tests/
├── __init__.py
├── test_models.py          # Model tests
├── test_views.py           # View tests (search, law detail)
├── test_admin.py           # Admin and AI import parser tests
├── test_commands.py        # Management command tests
├── test_meili_indexer.py   # MeiliSearch indexer tests
└── test_integration.py     # End-to-end integration tests
```

## Running Tests

### Run all tests
```bash
python manage.py test laws
```

### Run specific test file
```bash
python manage.py test laws.tests.test_models
```

### Run specific test class
```bash
python manage.py test laws.tests.test_models.LawModelTest
```

### Run specific test method
```bash
python manage.py test laws.tests.test_models.LawModelTest.test_law_creation
```

### Run tests with coverage
```bash
# Install coverage if not already installed
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test laws

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
# Open htmlcov/index.html in your browser
```

## Test Coverage

### test_models.py
- Model creation and validation
- String representations
- URL generation
- Cascade deletion behavior
- Ordering
- Unique constraints
- Helper methods (law(), anchor_tag())
- Model relationships

### test_views.py
- Search view with MeiliSearch (mocked)
- Query handling and empty queries
- Result hydration with Law objects
- Multi-index search (sections, schedules, appendices)
- Highlighting configuration
- Law detail view
- Section ordering
- 404 handling
- Query optimization

### test_admin.py
- AI import parser (_run_import_logic)
- Tag parsing (@PART, @CHAPTER, @SECTION, @SCHEDULE, @APPENDIX)
- Content preservation and line breaks
- Edge cases (empty headings, no title)
- Admin actions (clean_with_ai, import_from_ai_text)
- Transaction handling and rollback
- Error handling
- Admin display methods

### test_commands.py
- rebuild_meili command
- repair_search_index command
- Index configuration
- Document counting
- Slug repair
- Error handling

### test_meili_indexer.py
- build_section_doc function
- build_schedule_doc function
- setup_index function
- rebuild_meili_index function
- Document structure validation
- Relationship traversal
- Query optimization

### test_integration.py
- Complete import → index → search workflow
- Multi-law search
- Search result to law detail navigation
- Schedules and appendices integration
- Complex hierarchy handling
- Error handling (ghost data, missing laws)
- Cascade deletion across hierarchy

## Mocking Strategy

Tests use Python's `unittest.mock` to mock external dependencies:

- **MeiliSearch client**: Mocked to avoid requiring a running MeiliSearch instance
- **Gemini API**: Mocked to avoid API calls during tests
- **Django management commands**: Mocked where appropriate to isolate tests

## Test Data

Tests create minimal test data in `setUp()` methods and clean up automatically after each test using Django's TestCase transaction handling.

## Best Practices

1. **Isolation**: Each test is independent and doesn't rely on other tests
2. **Mocking**: External services are mocked to avoid dependencies
3. **Coverage**: Tests cover happy paths, edge cases, and error conditions
4. **Documentation**: Each test has a clear docstring explaining what it tests
5. **Naming**: Test names clearly describe what they're testing

## CI/CD Integration

To integrate with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    python manage.py test laws --verbosity=2

- name: Run tests with coverage
  run: |
    coverage run --source='.' manage.py test laws
    coverage report --fail-under=80
    coverage xml
```

## Known Limitations

- MeiliSearch integration is mocked; for true integration tests, a test MeiliSearch instance would be needed
- Gemini API calls are mocked; actual API responses are not tested
- File upload tests are not included (PDF processing)

## Future Improvements

- Add performance/load tests
- Add browser-based UI tests (Selenium/Playwright)
- Add API tests if REST API is added
- Add security tests (XSS, CSRF, etc.)
- Add accessibility tests
