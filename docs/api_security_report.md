# Building and Securing a REST API

**Urban Mobility Data Explorer — MoMo SMS Transactions API**
Enterprise Web Development · Team 7 · September 2026

## Contents

1. [Introduction to API Security](#1-introduction-to-api-security)
2. [Endpoint Documentation](#2-endpoint-documentation)
3. [Data Structures & Algorithms: Search Comparison](#3-data-structures--algorithms-search-comparison)
4. [Reflection: Basic Auth Limitations & Stronger Alternatives](#4-reflection-basic-auth-limitations--stronger-alternatives)

---

## 1. Introduction to API Security

This REST API exposes MoMo mobile-money transaction records — financial data tied to real people, amounts, and account identifiers — over HTTP. Any API surfacing data like this has to answer three questions before it's safe to run: who is allowed to call it (**authentication**), what are they allowed to do once they're in (**authorization**), and can the data be read or tampered with in transit (**transport security**). This report documents how the current implementation answers the first question, what its real limitations are, and what a production-grade answer would look like instead. The sections below cover the API's endpoints, a data-structure efficiency comparison for looking up a transaction by id, and a detailed security reflection on the authentication scheme actually implemented.

---

## 2. Endpoint Documentation

Base URL (local): `http://localhost:8000`. Every endpoint requires HTTP Basic Authentication; a request without valid credentials receives `401 Unauthorized`.

### `GET` /transactions

List all transactions.

```bash
curl -u <username>:<password> http://localhost:8000/transactions
```

**Response** (`200 OK`, truncated — real response has 1,682 records):

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

| Code | Meaning |
|------|---------|
| 401 | Missing/invalid Basic Auth credentials |

### `GET` /transactions/{id}

View a single transaction by its numeric `id`. Same response shape as above.

| Code | Meaning |
|------|---------|
| 401 | Missing/invalid Basic Auth credentials |
| 404 | No transaction with that id |

### `POST` /transactions

Add a new transaction.

```bash
curl -u <username>:<password> -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"type": "RECEIVE_MONEY", "amount": 5000.0, "sender": {"name": "Test Sender", "phone": "250780000000"}}'
```

**Response** (`201 Created`):

```json
{
  "id": 1683,
  "type": "RECEIVE_MONEY",
  "amount": 5000.0,
  "sender": { "name": "Test Sender", "phone": "250780000000" }
}
```

| Code | Meaning |
|------|---------|
| 400 | Body is not valid JSON |
| 401 | Missing/invalid Basic Auth credentials |

### `PUT` /transactions/{id}

Update an existing transaction. Returns the full updated record (`200 OK`), same shape as GET.

| Code | Meaning |
|------|---------|
| 400 | Body is not valid JSON |
| 401 | Missing/invalid Basic Auth credentials |
| 404 | No transaction with that id |

### `DELETE` /transactions/{id}

Delete a transaction. Returns `204 No Content` with an empty body.

| Code | Meaning |
|------|---------|
| 401 | Missing/invalid Basic Auth credentials |
| 404 | No transaction with that id |

---

## 3. Data Structures & Algorithms: Search Comparison

> **Pending.** This section — a timed comparison of linear search vs. dictionary lookup for finding a transaction by id, plus a written reflection on why one wins — has not been completed yet (`dsa/search_benchmark.py`). It will be added once that implementation and its benchmark results are in.

---

## 4. Reflection: Basic Auth Limitations & Stronger Alternatives

*Emmanuel Happy Rangira*

Our API protects every endpoint with HTTP Basic Authentication. The client sends an Authorization header containing `username:password` encoded in base64. This is encoding, not encryption. Base64 is a reversible format with no key, so anyone who can see the request can decode the credentials in one line of code. On plain HTTP, which is how our `http.server` implementation runs, an attacker on the same network can read the password straight off the wire.

Basic Auth has other weaknesses too. The full password is sent with every request, which multiplies the chances of interception or accidental logging. There is no built-in expiry, so a stolen credential works until the password is changed. The server cannot revoke one client without changing the shared password for everyone. And there are no scopes, so anyone with the password has full access.

Our implementation reduces some risks by comparing credentials in constant time (`hmac.compare_digest`) and returning 401 for any malformed header without crashing. It cannot fix the protocol's weaknesses. Basic Auth is only acceptable when used over HTTPS, and even then it suits little more than internal tools and prototypes.

JWT (JSON Web Tokens) and OAuth2 address these problems. With JWT, the client logs in once with its credentials and receives a signed token containing claims such as the user ID, roles, and an expiry time. On later requests it sends the token instead of the password. Tokens are short-lived, so a stolen one stops working quickly. The server verifies the signature without a database lookup for every request, and it can embed roles to restrict what each user may do. A JWT is signed but not encrypted, so its contents are readable and it still needs HTTPS.

OAuth2 is an authorization framework, not a single token format. It lets a user grant an application limited, revocable access to their data through an authorization server, without ever giving that application their password. Access tokens carry specific scopes (for example, read-only access to transactions), expire quickly, and can be renewed with refresh tokens.

For an API handling financial data like ours, a production system should use HTTPS with short-lived tokens (JWT or OAuth2), hashed passwords on the server, and scoped permissions. Basic Auth is a reasonable starting point for a coursework prototype but not a final design.

---

*Urban Mobility Data Explorer — Building and Securing a REST API · Team 7*