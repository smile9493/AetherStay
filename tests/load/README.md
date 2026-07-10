# Locust Load Tests

## Prerequisites

- Backend running at `http://localhost:8000`
- MySQL running with seed data
- `pip install -r tests/requirements-dev.txt`

## Run

Interactive UI:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Open http://localhost:8089

## Scenarios

### S1 — Oversell protection (contention)

30 users concurrently book the **same** room and date range.

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --headless -u 30 -r 10 -t 30s --tags s1
```

**Expected:** exactly 1× `201 Created`, remainder `423` or `409`.

### S2 — Mixed search + booking

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --headless -u 30 -r 5 -t 60s --tags s2
```

## Post-run verification

```bash
docker exec -i aetherstay-mysql mysql -uaetherstay -paetherstay aetherstay \
  < tests/load/verify_no_oversell.sql
```

## Result template (for PROJECT_NOTES.md)

| Metric | Value |
|--------|-------|
| Users | 30 |
| Duration | 30s |
| 201 success_hold | 1 |
| 423/409 conflicts | 29 |
| Oversell SQL check | 0 rows |
