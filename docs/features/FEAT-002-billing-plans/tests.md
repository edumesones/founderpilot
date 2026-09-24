# FEAT-XXX: Test Plan

## Overview

Test strategy and cases for this feature.

---

## Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| Unit | Test individual functions/methods | `tests/unit/` |
| Integration | Test API endpoints | `tests/integration/` |
| E2E | Test full user flows | `tests/e2e/` |

---

## Unit Tests

### Models

| Test Case | Input | Expected | Status |
|-----------|-------|----------|--------|
| `test_model_create_valid` | Valid data | Model created | ⬜ |
| `test_model_create_invalid` | Invalid data | Validation error | ⬜ |
| `test_model_relationships` | Related entities | Correct relations | ⬜ |

### Services

| Test Case | Scenario | Expected | Status |
|-----------|----------|----------|--------|
| `test_service_create` | Create resource | Success | ⬜ |
| `test_service_get_exists` | Get existing | Returns resource | ⬜ |
| `test_service_get_not_found` | Get missing | Raises NotFound | ⬜ |
| `test_service_list_empty` | List empty | Returns [] | ⬜ |
| `test_service_list_filtered` | List with filter | Filtered results | ⬜ |

### Utils/Helpers

| Test Case | Input | Expected | Status |
|-----------|-------|----------|--------|
| `test_helper_function` | Sample input | Expected output | ⬜ |

---

## Integration Tests

### API Endpoints

| Test Case | Method | Endpoint | Status Code | Status |
|-----------|--------|----------|-------------|--------|
| `test_create_resource` | POST | `/api/resource` | 201 | ⬜ |
| `test_create_invalid` | POST | `/api/resource` | 422 | ⬜ |
| `test_get_resource` | GET | `/api/resource/{id}` | 200 | ⬜ |
| `test_get_not_found` | GET | `/api/resource/{id}` | 404 | ⬜ |
| `test_list_resources` | GET | `/api/resource` | 200 | ⬜ |
| `test_update_resource` | PUT | `/api/resource/{id}` | 200 | ⬜ |
| `test_delete_resource` | DELETE | `/api/resource/{id}` | 204 | ⬜ |
| `test_unauthorized` | GET | `/api/resource` | 401 | ⬜ |

---

## E2E Tests

### User Flows

| Flow | Steps | Expected Outcome | Status |
|------|-------|------------------|--------|
| Happy path | 1. Create → 2. Read → 3. Update | Success at each step | ⬜ |
| Error recovery | 1. Invalid input → 2. Correct → 3. Success | Handles error gracefully | ⬜ |

---

## Edge Cases

| Scenario | Test Case | Expected Behavior | Status |
|----------|-----------|-------------------|--------|
| Empty input | `test_empty_input` | Validation error | ⬜ |
| Max length exceeded | `test_max_length` | Validation error | ⬜ |
| Special characters | `test_special_chars` | Handled correctly | ⬜ |
| Concurrent requests | `test_concurrent` | No race conditions | ⬜ |
| Large payload | `test_large_payload` | Handled or rejected gracefully | ⬜ |

---

## Test Data

### Fixtures Needed

```python
# conftest.py fixtures
@pytest.fixture
def sample_resource():
    return {
        "name": "Test Resource",
        "data": {"key": "value"}
    }

@pytest.fixture
def authenticated_client():
    # Return client with auth token
    pass
```

---

## Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_service.py -v

# Run specific test
pytest tests/unit/test_service.py::test_create -v

# Run with markers
pytest -m "not slow" -v
```

---

## Coverage Requirements

| Module | Target | Actual |
|--------|--------|--------|
| `src/models/` | 80% | ⬜ |
| `src/services/` | 80% | ⬜ |
| `src/api/` | 70% | ⬜ |
| **Overall** | **75%** | **⬜** |

---

## Test Results

_[Fill after running tests]_

### Latest Run

```
Date: {date}
Total: 0 tests
Passed: 0
Failed: 0
Skipped: 0
Coverage: 0%
```

### History

| Date | Passed | Failed | Coverage |
|------|--------|--------|----------|
| - | - | - | - |

---

## Known Issues

_[Document any test-related issues]_

- None currently

---

*Last updated: {date}*
