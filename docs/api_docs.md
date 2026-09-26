# API Documentation — MoMo SMS Transactions REST API

Base URL (local): `http://localhost:8000`
Auth: HTTP Basic Auth on every endpoint (see `api/auth.py`; credentials
default to `admin` / `changeme` until the real check is implemented).

<!-- TODO: once auth is implemented, replace the response examples below
     with actual curl/Postman output. -->

## GET /transactions

List all transactions.

**Request Example**
```bash
curl -u admin:changeme http://localhost:8000/transactions
```

**Response Example** (`200 OK`, truncated — real response has 1,682 records)
```json
[
  {
    "id": 1,
    "type": "RECEIVE_MONEY",
    "sms_timestamp": "2024-05-10T14:30:58.724000+00:00",
    "amount": 2000.0,
    "sender": { "name": "Jane Smith", "phone": "*********013" },
    "receiver": null,
    "transaction_datetime": "2024-05-10T16:30:51",
    "balance_after": 2000.0,
    "direction": "CREDIT",
    "transaction_id": "76662021700",
    "fee": 0.0
  }
]
```

**Error Codes**
| Code | Meaning |
|---|---|
| 401 | Missing/invalid Basic Auth credentials |
| 501 | Auth check not implemented yet (dev-only state) |

## GET /transactions/{id}

View a single transaction by its numeric `id`.

**Request Example**
```bash
curl -u admin:changeme http://localhost:8000/transactions/1
```

**Response Example** (`200 OK`) — same shape as one item from the list above.

**Error Codes**
| Code | Meaning |
|---|---|
| 401 | Missing/invalid Basic Auth credentials |
| 404 | No transaction with that id |

## POST /transactions

Add a new transaction.

**Request Example**
```bash
curl -u admin:changeme -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"type": "RECEIVE_MONEY", "amount": 5000.0, "sender": {"name": "Test Sender", "phone": "250780000000"}}'
```

**Response Example** (`201 Created`)
```json
{
  "id": 1683,
  "type": "RECEIVE_MONEY",
  "amount": 5000.0,
  "sender": { "name": "Test Sender", "phone": "250780000000" }
}
```
<!-- TODO: once field validation is added to POST, document the required
     fields here and add a 400 example for a request missing them. -->

**Error Codes**
| Code | Meaning |
|---|---|
| 400 | Body is not valid JSON |
| 401 | Missing/invalid Basic Auth credentials |

## PUT /transactions/{id}

Update an existing transaction.

**Request Example**
```bash
curl -u admin:changeme -X PUT http://localhost:8000/transactions/1 \
  -H "Content-Type: application/json" \
  -d '{"amount": 6000.0}'
```

**Response Example** (`200 OK`) — the full updated record, same shape as GET.

**Error Codes**
| Code | Meaning |
|---|---|
| 400 | Body is not valid JSON |
| 401 | Missing/invalid Basic Auth credentials |
| 404 | No transaction with that id |

## DELETE /transactions/{id}

Delete a transaction.

**Request Example**
```bash
curl -u admin:changeme -X DELETE http://localhost:8000/transactions/1
```

**Response Example**: `204 No Content` (empty body)

**Error Codes**
| Code | Meaning |
|---|---|
| 401 | Missing/invalid Basic Auth credentials |
| 404 | No transaction with that id |

## Security notes

<!-- TODO: include this in the written report alongside the Basic Auth
     weakness explanation. -->

Basic Auth sends credentials base64-encoded (not encrypted) on every
request — anyone who can see the traffic (no HTTPS, a shared proxy, browser
history in some clients) can read them directly. Stronger alternatives:
**JWT** (short-lived signed tokens, no credentials sent after login) or
**OAuth2** (delegated, revocable, scoped access without ever sharing a
password with this API directly).
