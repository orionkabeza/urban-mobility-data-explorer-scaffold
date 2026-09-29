# Screenshots — Task 6 (Testing & Validation)

Owner: Aubin.

The assignment requires exactly these 4 screenshots (curl or Postman,
either is fine) once Emmanuel's `api/auth.py` is finished:

1. **`01_get_success.png`** — a successful `GET /transactions` (or
   `/transactions/{id}`) with valid Basic Auth credentials, showing `200 OK`
   and a JSON body.
2. **`02_unauthorized.png`** — the same request with wrong/missing
   credentials, showing `401 Unauthorized`.
3. **`03_post_success.png`** — a successful `POST /transactions` showing
   `201 Created` and the new record.
4. **`04_put_delete_success.png`** — a successful `PUT /transactions/{id}`
   (`200 OK`) and `DELETE /transactions/{id}` (`204 No Content`); one
   screenshot each, or combined if your tool supports it.

## How to run the API locally

```bash
cd urban-mobility-data-explorer-scaffold
python3 -m api.app
# serves on http://localhost:8000
```

Postman: import the base URL above, set Basic Auth on each request under
the Authorization tab, and use the request bodies from `docs/api_docs.md`.
