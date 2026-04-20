# ScouterFRC — API Strategy & Documentation

> **Version:** 1.0  
> **Status:** Planning  
> **Scope:** Complete API design, versioning, authentication, and documentation strategy for ScouterFRC  
> **Audience:** Backend engineers, frontend engineers, SDK consumers, third-party integrators

---

## Table of Contents

1. [Overview & Goals](#1-overview--goals)
2. [API Architecture](#2-api-architecture)
3. [REST Design Principles](#3-rest-design-principles)
4. [Core API Resources & Endpoints](#4-core-api-resources--endpoints)
5. [API Versioning Strategy](#5-api-versioning-strategy)
6. [Request/Response Format](#6-requestresponse-format)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [API Rate Limiting](#8-api-rate-limiting)
9. [Pagination & Filtering](#9-pagination--filtering)
10. [Data Serialization](#10-data-serialization)
11. [Documentation (Swagger/OpenAPI)](#11-documentation-swaggeropenapi)
12. [SDKs & Client Libraries](#12-sdks--client-libraries)
13. [Webhooks (Phase 2+)](#13-webhooks-phase-2)
14. [Real-time Updates (Phase 2+)](#14-real-time-updates-phase-2)
15. [Deprecation Policy](#15-deprecation-policy)
16. [Breaking Changes Policy](#16-breaking-changes-policy)
17. [Security Best Practices](#17-security-best-practices)
18. [Performance Considerations](#18-performance-considerations)
19. [Monitoring & Analytics](#19-monitoring--analytics)
20. [API Client Examples](#20-api-client-examples)
21. [Phase-Specific API Additions](#21-phase-specific-api-additions)
22. [Backward Compatibility](#22-backward-compatibility)
23. [Testing & Validation](#23-testing--validation)
24. [Rate Limit Scenarios & Examples](#24-rate-limit-scenarios--examples)
25. [Future Considerations](#25-future-considerations)

---

## 1. Overview & Goals

### API Design Philosophy

The ScouterFRC API is designed as a first-class product. Every endpoint is treated as a public contract — predictable, stable, and well-documented. The goal is to enable mobile clients, web clients, and third-party integrations to build confidently on top of ScouterFRC data without needing to understand the internal system architecture.

### Design Principles

| Principle | Description |
|-----------|-------------|
| **RESTful** | Resources are nouns; HTTP methods convey intent. No RPC-style verb endpoints. |
| **Consistency** | Uniform naming conventions, response envelopes, and error formats across all endpoints. |
| **Scalability** | Stateless requests, pagination on all list endpoints, and cache-friendly response headers. |
| **Predictability** | Consumers should be able to guess new endpoints based on patterns already established. |
| **Explicit versioning** | Breaking changes are introduced only through a new major version prefix (e.g., `/v2/`). |

### Target Audiences

- **Mobile clients** — React Native / iOS / Android apps used by scouts at competition venues.
- **Web clients** — The ScouterFRC dashboard (React) and any community-built frontends.
- **Server-to-server** — Automation scripts and data pipelines that push or pull scouting data.
- **Third-party integrations** — Tools built by the FRC community (Tableau dashboards, custom analytics).

### Evolution Strategy

The API evolves through additive versioning. New fields, resources, and optional parameters are added to the current version without incrementing the version number. Removals, renames, and behavioral changes are deferred to the next major version with a minimum 6-month deprecation window.

---

## 2. API Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Clients                                   │
│   Mobile App   │   Web Dashboard   │   Third-Party Integrations │
└──────┬─────────┴────────┬──────────┴────────────┬───────────────┘
       │                  │                        │
       └──────────────────┼────────────────────────┘
                          │ HTTPS (TLS 1.2+)
                          ▼
              ┌───────────────────────┐
              │      API Gateway      │
              │  Rate Limiting        │
              │  Auth Token Check     │
              │  Request Routing      │
              │  Response Compression │
              └───────────┬───────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  Events &   │ │  Scouting   │ │  Analytics  │
   │  Teams API  │ │  Data API   │ │     API     │
   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     Data Layer        │
              │  PostgreSQL (primary) │
              │  Redis (cache)        │
              └───────────────────────┘
```

### Service Boundaries

| Service | Responsibility |
|---------|----------------|
| **API Gateway** | Auth enforcement, rate limiting, request routing, compression |
| **Events & Teams API** | CRUD for events, teams, and match data |
| **Scouting Data API** | Scout submission ingestion, retrieval, and aggregation |
| **Analytics API** | Derived statistics, rankings, and AI recommendations |
| **Alliance Builder API** | Alliance configuration and AI-powered recommendations |
| **Video Tracking API** | Robot trajectory, heatmap, and tracking data endpoints |

### API Gateway Considerations

- All requests pass through the gateway before reaching internal services.
- The gateway is responsible for JWT validation, rate limit enforcement, and request logging.
- Internal service-to-service calls bypass the gateway and use mTLS with service accounts.
- Gateway enforces a maximum request body size of **5 MB** to prevent abuse.

### Request/Response Flow

```
Client → TLS Handshake → API Gateway
  → Validate Authorization header (JWT / API Key)
  → Check rate limit bucket (Redis)
  → Route to appropriate service
  → Service processes request
  → Service returns response
→ Gateway adds rate limit headers
→ Gateway compresses response (gzip)
→ Client receives response
```

---

## 3. REST Design Principles

### Resource-Oriented Design

Resources are things (events, teams, matches), not actions. All endpoints are structured around nouns.

```
✅ GET /v1/events/2024cmptx/matches
❌ GET /v1/getMatchesForEvent?eventId=2024cmptx

✅ POST /v1/scouting
❌ POST /v1/submitScoutingData
```

### Standard HTTP Methods

| Method | Meaning | Idempotent | Safe |
|--------|---------|-----------|------|
| `GET` | Retrieve a resource or collection | Yes | Yes |
| `POST` | Create a new resource | No | No |
| `PUT` | Replace a resource entirely | Yes | No |
| `PATCH` | Partially update a resource | No | No |
| `DELETE` | Remove a resource | Yes | No |

### Resource Naming Conventions

- Use **plural nouns** for collections: `/events`, `/teams`, `/matches`
- Use **kebab-case** for multi-word resource names: `/alliance-builder`, `/video-tracking`
- Avoid verbs in URLs: use `POST /scouting` not `POST /submitScouting`
- Sub-resources represent relationships: `/events/{eventId}/teams` (teams within an event)

### Hierarchical Resource Structure

```
/v1/
  events/
    {eventId}/
      teams/
      matches/
      scouting/
  teams/
    {teamId}/
      stats/
  matches/
    {matchId}/
      robots/
  scouting/
    {scoutingId}/
  analytics/
    team/{teamId}
    match/{matchId}
    events/{eventId}/rankings
  alliance-builder/
    {allianceId}/
    recommendations/
  videos/
    {matchId}/
      tracking/
      heatmap/
      trajectory/
```

### Query Parameters vs Path Parameters

| Use | When |
|-----|------|
| **Path parameter** `/{id}` | Identifying a specific resource |
| **Query parameter** `?filter=` | Filtering, sorting, pagination, optional context |

```
✅ GET /v1/teams/254             (identity — team 254)
✅ GET /v1/teams?event_id=2024cmptx  (filter — teams in event)
❌ GET /v1/teams/2024cmptx/254   (ambiguous hierarchy)
```

---

## 4. Core API Resources & Endpoints

### Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/events` | List all events (paginated) |
| `GET` | `/v1/events/{eventId}` | Get event details |
| `POST` | `/v1/events` | Create a new event |
| `PUT` | `/v1/events/{eventId}` | Replace event data |
| `DELETE` | `/v1/events/{eventId}` | Delete an event |

### Teams

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/events/{eventId}/teams` | List teams participating in an event |
| `GET` | `/v1/teams/{teamId}` | Get team details |
| `GET` | `/v1/teams/{teamId}/stats` | Get team statistics (aggregated) |

### Matches

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/events/{eventId}/matches` | List all matches in an event |
| `GET` | `/v1/matches/{matchId}` | Get match details |
| `GET` | `/v1/matches/{matchId}/robots` | Get robots (and their teams) in a match |

### Scouting Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/scouting` | Submit a scouting entry |
| `GET` | `/v1/scouting/{scoutingId}` | Get a single scouting entry |
| `PUT` | `/v1/scouting/{scoutingId}` | Replace a scouting entry |
| `PATCH` | `/v1/scouting/{scoutingId}` | Partially update a scouting entry |
| `GET` | `/v1/events/{eventId}/scouting` | List all scouting entries for an event |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/analytics/team/{teamId}` | Aggregated performance analytics for a team |
| `GET` | `/v1/analytics/match/{matchId}` | Match-level analytics breakdown |
| `GET` | `/v1/analytics/events/{eventId}/rankings` | Computed rankings for all teams in an event |

### Alliance Builder

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/alliance-builder` | Create a new alliance configuration |
| `GET` | `/v1/alliance-builder/{allianceId}` | Retrieve an alliance configuration |
| `GET` | `/v1/alliance-builder/recommendations` | Get AI-powered alliance recommendations |

### Video Tracking

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/videos/{matchId}/tracking` | Robot position tracking data for a match |
| `GET` | `/v1/videos/{matchId}/heatmap` | Field heatmap data for a match |
| `GET` | `/v1/videos/{matchId}/trajectory` | Robot trajectory path data for a match |

---

## 5. API Versioning Strategy

### Version in URL Path

The major API version is embedded in the URL path:

```
https://api.scouterfrc.com/v1/events
https://api.scouterfrc.com/v2/events  ← future breaking changes
```

This approach makes the version explicit and visible in logs, curl commands, and documentation.

### Backward Compatibility Guarantees

Within a major version (e.g., `v1`):

- ✅ New optional fields may be added to responses
- ✅ New optional query parameters may be added
- ✅ New endpoints may be added
- ❌ Existing fields will not be renamed or removed
- ❌ Field types will not change (e.g., string → integer)
- ❌ Endpoint behavior will not change in a breaking way

### Version Lifecycle

| Stage | Duration | Description |
|-------|----------|-------------|
| **Active** | Until successor reaches GA | Fully supported; new features may be added |
| **Deprecated** | Minimum 6 months | Supported but no new features; migration guide published |
| **Sunset** | End of deprecation period | Endpoint returns `410 Gone`; clients must migrate |

### Migration Guides

When a new major version is released, a migration guide is published at `docs/API_MIGRATION_v{N}_to_v{N+1}.md`. The guide covers:

- Summary of breaking changes
- Mapping of old endpoints to new endpoints
- Code examples for common migration patterns
- Timeline for `v{N}` sunset

### Deprecation Timeline

```
Day 0:   New major version (v2) released in GA
Day 0:   v1 enters "Deprecated" state; Deprecation header added to all v1 responses
Day 180: v1 enters "Sunset" state; endpoints return 410 Gone
Day 180: v1 removed from API gateway routing
```

The `Deprecation` and `Sunset` response headers are set on deprecated endpoints:

```
Deprecation: true
Sunset: Sat, 01 Jan 2026 00:00:00 GMT
Link: <https://docs.scouterfrc.com/api/migration/v1-to-v2>; rel="deprecation"
```

---

## 6. Request/Response Format

### Standard Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes (most endpoints) | `Bearer <access_token>` or `ApiKey <key>` |
| `Content-Type` | Required on POST/PUT/PATCH | `application/json` |
| `Accept` | Recommended | `application/json` |
| `X-Request-ID` | Optional | Client-provided idempotency/trace ID |

### Request Body Structure

```json
{
  "team_id": 254,
  "match_id": "2024cmptx_qm12",
  "data": {
    "auto_mobility": true,
    "auto_game_pieces": 3,
    "teleop_game_pieces": 8,
    "endgame_position": "stage"
  },
  "notes": "Very fast auto cycle"
}
```

### Success Response Format

**200 OK — Resource retrieved:**
```json
{
  "data": {
    "id": "2024cmptx",
    "name": "2024 FIRST Championship - Tesla Division",
    "start_date": "2024-04-17",
    "end_date": "2024-04-20",
    "location": "Houston, TX"
  },
  "meta": {
    "api_version": "1.0",
    "request_id": "req_01HZXYZ123",
    "timestamp": "2024-04-20T15:30:00Z"
  }
}
```

**201 Created — Resource created:**
```json
{
  "data": {
    "id": "scout_01HZABC456",
    "team_id": 254,
    "match_id": "2024cmptx_qm12",
    "created_at": "2024-04-20T15:31:00Z"
  },
  "meta": {
    "api_version": "1.0",
    "request_id": "req_01HZXYZ124",
    "timestamp": "2024-04-20T15:31:00Z"
  }
}
```

**204 No Content — Resource deleted:**  
_(No response body)_

### Error Response Format

All errors use a consistent envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request body is invalid.",
    "details": [
      {
        "field": "team_id",
        "issue": "must be a positive integer"
      }
    ],
    "request_id": "req_01HZXYZ125",
    "timestamp": "2024-04-20T15:32:00Z",
    "docs_url": "https://docs.scouterfrc.com/api/errors#VALIDATION_ERROR"
  }
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| `200` | OK | Successful GET, PUT, PATCH |
| `201` | Created | Successful POST that creates a resource |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Invalid request body or query parameters |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | Authenticated but lacks required permission |
| `404` | Not Found | Resource does not exist |
| `409` | Conflict | Resource already exists (duplicate) |
| `422` | Unprocessable Entity | Validation errors on semantic content |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server-side failure |
| `503` | Service Unavailable | Temporary maintenance or overload |

### Response Envelope

Every response (success or error) uses a consistent envelope:

```json
{
  "data": { ... },        // present on success
  "meta": { ... },        // always present
  "errors": [ ... ],      // present on error
  "pagination": { ... }   // present on list endpoints
}
```

### Pagination Response

```json
{
  "data": [ ... ],
  "pagination": {
    "total": 147,
    "limit": 20,
    "offset": 0,
    "has_next": true,
    "has_previous": false,
    "next": "/v1/events?limit=20&offset=20",
    "previous": null
  },
  "meta": {
    "api_version": "1.0",
    "request_id": "req_01HZXYZ126",
    "timestamp": "2024-04-20T15:33:00Z"
  }
}
```

### Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | One or more request fields failed validation |
| `INVALID_JSON` | 400 | Request body is not valid JSON |
| `MISSING_REQUIRED_FIELD` | 400 | Required field absent from request body |
| `UNAUTHENTICATED` | 401 | No valid authentication credentials provided |
| `TOKEN_EXPIRED` | 401 | Bearer token has expired |
| `FORBIDDEN` | 403 | Insufficient permissions for this resource |
| `NOT_FOUND` | 404 | Requested resource does not exist |
| `DUPLICATE_RESOURCE` | 409 | Resource with this identifier already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests; see `Retry-After` header |
| `INTERNAL_ERROR` | 500 | Unexpected server error; report to support |

---

## 7. Authentication & Authorization

### Authentication Methods

#### OAuth 2.0 (User-Facing Apps)

OAuth 2.0 Authorization Code flow is used for web and mobile clients where a user is present.

```
1. Client redirects user to: https://auth.scouterfrc.com/oauth/authorize
   ?client_id=CLIENT_ID
   &response_type=code
   &redirect_uri=https://app.scouterfrc.com/callback
   &scope=read:events write:scouting
   &state=RANDOM_STATE

2. User logs in and grants consent.

3. Auth server redirects to redirect_uri with ?code=AUTH_CODE

4. Client exchanges code for tokens:
   POST /oauth/token
   { grant_type: "authorization_code", code: AUTH_CODE, ... }

5. Auth server returns:
   { access_token, refresh_token, expires_in: 3600 }
```

**Token expiration:**

| Token | Expiration |
|-------|-----------|
| Access token | 1 hour |
| Refresh token | 30 days (sliding) |

**Token refresh:**

```http
POST /oauth/token
Content-Type: application/json

{
  "grant_type": "refresh_token",
  "refresh_token": "REFRESH_TOKEN",
  "client_id": "CLIENT_ID"
}
```

#### API Keys (Server-to-Server)

API keys are used for automated integrations and scripts that run without a user present.

- Keys are prefixed with `sfrc_` for easy identification in logs and secret scanners.
- Keys are generated via the ScouterFRC developer portal.
- Keys can be scoped to specific permissions (e.g., `read:scouting` only).
- Keys support per-key rate limiting independent of user quotas.
- Keys should be rotated at least annually or immediately if suspected compromised.

```http
Authorization: ApiKey sfrc_live_a1b2c3d4e5f6...
```

#### Session-Based (Web App)

The ScouterFRC web dashboard uses HTTP-only session cookies for authentication. Sessions are managed server-side with a 24-hour TTL and automatic renewal on activity.

### Authorization: Role-Based Access Control (RBAC)

| Role | Description |
|------|-------------|
| `scout` | Can submit and view scouting data for their organization's events |
| `lead_scout` | Can review and edit all scouting data within their organization |
| `analyst` | Read-only access to all data and analytics within their organization |
| `admin` | Full access to organization settings, users, and data |
| `super_admin` | Platform-wide access; ScouterFRC team only |

### OAuth 2.0 Scopes

| Scope | Description |
|-------|-------------|
| `read:events` | Read event and match data |
| `write:events` | Create and update events |
| `read:scouting` | Read scouting entries |
| `write:scouting` | Submit and update scouting entries |
| `read:analytics` | Access analytics and rankings |
| `read:users` | Read user profile data |
| `admin:users` | Manage organization users |
| `admin:org` | Manage organization settings |

### Bearer Token (JWT Structure)

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-2024-01"
  },
  "payload": {
    "sub": "user_01HZABC",
    "user_id": "user_01HZABC",
    "org_id": "org_01HZDEF",
    "roles": ["lead_scout"],
    "scopes": ["read:events", "write:scouting", "read:analytics"],
    "iat": 1713625800,
    "exp": 1713629400
  }
}
```

**Token validation process:**

1. Verify token signature using ScouterFRC public key (JWKS endpoint: `/oauth/.well-known/jwks.json`)
2. Check `exp` claim is in the future
3. Verify `iss` claim matches `https://auth.scouterfrc.com`
4. Check required scopes against token `scopes` claim
5. Resolve `org_id` and `user_id` for resource-level permission checks

---

## 8. API Rate Limiting

### Rate Limit Strategy

Rate limiting is applied at three levels and enforced in Redis with sliding window counters.

| Client Type | Limit | Window |
|-------------|-------|--------|
| Authenticated user | 1,000 requests | per hour |
| API key | 5,000 requests | per hour |
| Unauthenticated (IP-based) | 100 requests | per hour |
| Burst (any authenticated) | 20 requests | per minute |

### Rate Limit Response Headers

Every API response includes the following headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1713629400
X-RateLimit-Window: 3600
```

When a rate limit is exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1713629400
Retry-After: 1247

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You have exceeded the request rate limit. Retry after the specified time.",
    "request_id": "req_01HZXYZ127",
    "timestamp": "2024-04-20T15:34:00Z"
  }
}
```

### Exponential Backoff Guidance

Clients that receive a `429` response should implement exponential backoff:

```javascript
async function requestWithRetry(url, options, maxRetries = 5) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const response = await fetch(url, options);
    if (response.status !== 429) return response;

    const retryAfter = parseInt(response.headers.get('Retry-After') || '60', 10);
    const delay = Math.min(retryAfter * 1000, (2 ** attempt) * 1000 + Math.random() * 1000);
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  throw new Error('Rate limit exceeded after max retries');
}
```

### Quota Management

API key holders can view current quota usage and reset times via:

```
GET /v1/me/rate-limits
```

```json
{
  "data": {
    "limit": 5000,
    "used": 1532,
    "remaining": 3468,
    "reset_at": "2024-04-20T16:00:00Z"
  }
}
```

---

## 9. Pagination & Filtering

### Limit/Offset Pagination

All list endpoints support `limit` and `offset` query parameters:

| Parameter | Default | Maximum | Description |
|-----------|---------|---------|-------------|
| `limit` | 20 | 100 | Number of items per page |
| `offset` | 0 | — | Number of items to skip |

```
GET /v1/events?limit=50&offset=100
```

### Cursor-Based Pagination (Large Datasets)

For high-volume endpoints (e.g., scouting submissions during a live event), cursor-based pagination is available to ensure consistent results across pages even as data is being written:

```
GET /v1/events/{eventId}/scouting?limit=20&cursor=eyJpZCI6IjEyMzQ1In0
```

The response includes a `next_cursor` value:

```json
{
  "data": [ ... ],
  "pagination": {
    "limit": 20,
    "next_cursor": "eyJpZCI6IjEyMzY1In0",
    "has_next": true
  }
}
```

### Filtering

Filters are expressed as query parameters using a bracket notation for operators:

```
GET /v1/teams?filter[rating]=gt:80
GET /v1/matches?filter[match_number]=gte:10&filter[match_number]=lte:20
GET /v1/events?filter[year]=eq:2024
```

#### Supported Filter Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` | Equals | `filter[year]=eq:2024` |
| `neq` | Not equals | `filter[status]=neq:cancelled` |
| `gt` | Greater than | `filter[rating]=gt:80` |
| `lt` | Less than | `filter[rating]=lt:50` |
| `gte` | Greater than or equal | `filter[match_number]=gte:1` |
| `lte` | Less than or equal | `filter[match_number]=lte:12` |
| `in` | In list (comma-separated) | `filter[team_id]=in:254,1114,2056` |
| `contains` | String contains (case-insensitive) | `filter[name]=contains:Chezy` |

### Sorting

```
GET /v1/matches?sort_by=match_number&order=asc
GET /v1/teams?sort_by=rating&order=desc
```

| Parameter | Values | Default |
|-----------|--------|---------|
| `sort_by` | Any sortable field name | `created_at` |
| `order` | `asc`, `desc` | `asc` |

### Filtering Examples

```
# Teams in a specific event with high rating, sorted by score
GET /v1/teams?event_id=2024cmptx&filter[rating]=gt:80&sort_by=score&order=desc

# Matches in qualification rounds
GET /v1/events/2024cmptx/matches?filter[match_type]=eq:qm&sort_by=match_number&order=asc

# Scouting entries submitted today
GET /v1/events/2024cmptx/scouting?filter[created_at]=gte:2024-04-20T00:00:00Z
```

---

## 10. Data Serialization

### JSON as Primary Format

All request and response bodies use JSON (`application/json`). No XML or form-encoded bodies are accepted on resource endpoints.

### Field Naming: snake_case

All JSON field names use `snake_case`:

```json
{
  "team_id": 254,
  "match_id": "2024cmptx_qm12",
  "auto_game_pieces": 3,
  "teleop_game_pieces": 8,
  "created_at": "2024-04-20T15:30:00Z"
}
```

### Date/Time Format

All timestamps use ISO 8601 with UTC timezone indicator:

```
2024-04-20T15:30:00Z          ← UTC datetime
2024-04-20                    ← Date only (no time component needed)
```

Date-only fields (e.g., `start_date`) use the `YYYY-MM-DD` format. Never return Unix timestamps or locale-specific date strings.

### Null Handling

- Fields with no value are represented as JSON `null`, not omitted from the response.
- This ensures clients can reliably check field presence without guessing.
- Optional request fields that are omitted default to their specified defaults; `null` explicitly sets the field to null.

### Timezone Information

All stored timestamps are UTC. The API always returns UTC. Clients are responsible for converting to local time.

### Nested Objects

Nested resources are inlined when they are part of the primary resource and the nesting depth is ≤ 2:

```json
{
  "id": "2024cmptx_qm12",
  "match_number": 12,
  "event": {
    "id": "2024cmptx",
    "name": "2024 FIRST Championship - Tesla Division"
  },
  "alliances": {
    "red": { "team_keys": ["frc254", "frc1114", "frc2056"] },
    "blue": { "team_keys": ["frc118", "frc148", "frc971"] }
  }
}
```

Deep nesting (>2 levels) should be avoided; use separate resource endpoints instead.

---

## 11. Documentation (Swagger/OpenAPI)

### OpenAPI 3.0 Specification

The canonical API definition is maintained in `docs/openapi.yaml`, following the OpenAPI 3.0 specification. This file is the source of truth for:

- All endpoint definitions (path, method, parameters, request/response schemas)
- Authentication scheme definitions
- Reusable component schemas (Team, Event, Match, ScoutingEntry, etc.)
- Example requests and responses

### Auto-Generated Documentation

The OpenAPI spec is used to auto-generate:

- **Swagger UI** — Interactive browser-based API explorer at `https://docs.scouterfrc.com/api/`
- **ReDoc** — Read-only documentation at `https://docs.scouterfrc.com/api/reference`
- **SDK stubs** — TypeScript types and Python dataclasses generated from schemas

### Interactive API Explorer

The Swagger UI instance at `https://docs.scouterfrc.com/api/`:

- Allows developers to authenticate with their API key
- Shows all endpoints with collapsible descriptions
- Allows live request execution from the browser
- Shows example responses for each endpoint

### Schema Definitions

All reusable schemas are defined in `docs/openapi.yaml` under `components/schemas`. Key schemas:

| Schema | Description |
|--------|-------------|
| `Event` | FRC competition event |
| `Team` | FRC team profile |
| `Match` | Match details including alliance assignments |
| `ScoutingEntry` | Single scout's data submission for one team in one match |
| `TeamStats` | Aggregated statistics for a team |
| `AnalyticsResult` | Computed analytics including weighted OPR |
| `AllianceConfig` | Alliance builder configuration |
| `TrackingData` | Robot position tracking data from video processing |
| `ErrorResponse` | Standard error envelope |
| `PaginatedResponse` | Paginated list wrapper |

### OpenAPI Spec Excerpt

```yaml
openapi: 3.0.3
info:
  title: ScouterFRC API
  version: 1.0.0
  description: REST API for the ScouterFRC scouting platform

servers:
  - url: https://api.scouterfrc.com/v1
    description: Production
  - url: https://api-staging.scouterfrc.com/v1
    description: Staging

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: Authorization

paths:
  /events:
    get:
      summary: List all events
      parameters:
        - name: limit
          in: query
          schema: { type: integer, default: 20, maximum: 100 }
        - name: offset
          in: query
          schema: { type: integer, default: 0 }
      responses:
        '200':
          description: Paginated list of events
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedEventResponse'
```

---

## 12. SDKs & Client Libraries

### Official SDKs

| Language | Package | Repository |
|----------|---------|------------|
| Python | `pip install scouterfrc-api` | `github.com/dburcat/ScouterFRC-python-sdk` |
| JavaScript/TypeScript | `npm install @scouterfrc/api` | `github.com/dburcat/ScouterFRC-js-sdk` |
| Go | `go get github.com/dburcat/scouterfrc-go` | `github.com/dburcat/ScouterFRC-go-sdk` (optional) |

### SDK Features

| Feature | Python | JavaScript/TypeScript | Go |
|---------|--------|----------------------|-----|
| Type safety | Pydantic models | Full TypeScript types | Struct types |
| Automatic retry | ✅ | ✅ | ✅ |
| Request/response validation | ✅ | ✅ | ✅ |
| Pagination helpers | ✅ | ✅ | ✅ |
| WebSocket client | ✅ | ✅ | ✅ |
| Offline caching | ❌ | ✅ (LocalStorage) | ❌ |

### JavaScript/TypeScript SDK

**Installation:**

```bash
npm install @scouterfrc/api
```

**Quick start:**

```typescript
import { ScouterFRCClient } from '@scouterfrc/api';

const client = new ScouterFRCClient({
  apiKey: process.env.SCOUTERFRC_API_KEY,
  // or: accessToken: 'your-oauth-token'
});

// List events
const events = await client.events.list({ limit: 50 });

// Get team details
const team = await client.teams.get('254');

// Submit scouting data
const entry = await client.scouting.submit({
  team_id: 254,
  match_id: '2024cmptx_qm12',
  data: {
    auto_mobility: true,
    auto_game_pieces: 3,
    teleop_game_pieces: 8,
    endgame_position: 'stage'
  }
});
```

**Pagination helper:**

```typescript
// Automatically iterate through all pages
for await (const event of client.events.listAll()) {
  console.log(event.name);
}
```

### Python SDK

**Installation:**

```bash
pip install scouterfrc-api
```

**Quick start:**

```python
from scouterfrc_api import ScouterFRCClient

client = ScouterFRCClient(api_key='your-key')

# List events
events = client.events.list(limit=50)

# Get team details
team = client.teams.get('254')

# Submit scouting data
entry = client.scouting.submit(
    team_id=254,
    match_id='2024cmptx_qm12',
    data={
        'auto_mobility': True,
        'auto_game_pieces': 3,
        'teleop_game_pieces': 8,
        'endgame_position': 'stage',
    }
)
```

**Pagination helper:**

```python
# Automatically paginate through all results
for event in client.events.list_all():
    print(event.name)
```

### Error Handling Patterns

```python
from scouterfrc_api import ScouterFRCClient
from scouterfrc_api.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

client = ScouterFRCClient(api_key='your-key')

try:
    team = client.teams.get('99999')
except NotFoundError:
    print('Team not found')
except RateLimitError as e:
    print(f'Rate limited. Retry after {e.retry_after} seconds.')
except AuthenticationError:
    print('Invalid API key')
except ValidationError as e:
    print(f'Validation failed: {e.details}')
```

---

## 13. Webhooks (Phase 2+)

### Event Subscriptions

Webhooks allow external systems to receive push notifications when events occur in ScouterFRC, rather than polling the API.

Webhooks are configured via the developer portal or the API:

```http
POST /v1/webhooks
{
  "url": "https://your-app.com/webhooks/scouterfrc",
  "events": ["scouting.submitted", "match.completed"],
  "secret": "your-webhook-secret"
}
```

### Supported Event Types

| Event | Trigger |
|-------|---------|
| `scouting.submitted` | A new scouting entry is submitted |
| `scouting.updated` | An existing scouting entry is modified |
| `alliance.recommended` | AI alliance recommendations are generated |
| `match.started` | A match begins (based on field schedule) |
| `match.completed` | Match results are available |
| `video.processing_complete` | Video analysis (tracking/heatmap) finishes |

### Webhook Payload Format

```json
{
  "id": "evt_01HZWEBOOK",
  "type": "scouting.submitted",
  "created_at": "2024-04-20T15:35:00Z",
  "data": {
    "scouting_id": "scout_01HZABC456",
    "team_id": 254,
    "match_id": "2024cmptx_qm12",
    "event_id": "2024cmptx"
  }
}
```

### Signature Verification

Every webhook request includes an `X-ScouterFRC-Signature` header containing an HMAC-SHA256 signature of the raw request body, signed with the webhook secret.

```python
import hmac
import hashlib

def verify_webhook(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

### Retry Logic

If the destination URL returns a non-2xx status or times out (10-second timeout), ScouterFRC retries with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1 (initial) | Immediately |
| 2 | 1 minute |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |

After 5 failed attempts, the webhook delivery is marked as failed. No further retries occur.

---

## 14. Real-time Updates (Phase 2+)

### WebSocket Connection

For live event data, clients can subscribe to a WebSocket connection at:

```
wss://ws.scouterfrc.com/v1/stream?token=ACCESS_TOKEN
```

### Message Format

```json
{
  "type": "scouting.submitted",
  "channel": "event:2024cmptx",
  "data": {
    "scouting_id": "scout_01HZABC456",
    "team_id": 254,
    "match_id": "2024cmptx_qm12"
  },
  "timestamp": "2024-04-20T15:35:01Z"
}
```

### Subscription/Unsubscription

```json
// Subscribe to a channel
{ "action": "subscribe", "channel": "event:2024cmptx" }
{ "action": "subscribe", "channel": "match:2024cmptx_qm12" }

// Unsubscribe from a channel
{ "action": "unsubscribe", "channel": "event:2024cmptx" }
```

### Available Channels

| Channel Pattern | Description |
|----------------|-------------|
| `event:{eventId}` | All updates for a specific event |
| `match:{matchId}` | Live updates for a specific match |
| `analytics:{eventId}` | Real-time ranking updates for an event |

### Heartbeat Mechanism

The server sends a heartbeat ping every 30 seconds. Clients must respond with a pong within 10 seconds or the connection is closed. Clients should treat any absence of heartbeat for >60 seconds as a dropped connection.

```json
// Server → Client ping
{ "type": "ping", "timestamp": "2024-04-20T15:36:00Z" }

// Client → Server pong
{ "type": "pong", "timestamp": "2024-04-20T15:36:00Z" }
```

### Auto-Reconnect Logic

```javascript
class ScouterFRCWebSocket {
  connect() {
    this.ws = new WebSocket(`wss://ws.scouterfrc.com/v1/stream?token=${this.token}`);
    this.ws.onclose = (event) => {
      if (!event.wasClean) {
        const delay = Math.min(30000, (2 ** this.reconnectAttempts) * 1000);
        setTimeout(() => this.connect(), delay);
        this.reconnectAttempts++;
      }
    };
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.resubscribeAll();
    };
  }
}
```

---

## 15. Deprecation Policy

### Minimum 6-Month Deprecation Window

No endpoint, field, or behavior change that would break existing clients is made without a minimum 6-month advance notice period. The deprecation window begins when the announcement is published and the `Deprecation` response header is added to affected responses.

### Announcement Process

| Step | Action |
|------|--------|
| 1 | Publish deprecation notice at `https://docs.scouterfrc.com/api/changelog` |
| 2 | Add `Deprecation` and `Sunset` headers to affected endpoints |
| 3 | Send email notification to registered API key holders |
| 4 | Add deprecation warning to Swagger UI for affected endpoints |
| 5 | Add migration guide at `docs/API_MIGRATION_v{N}_to_v{N+1}.md` |

### Migration Timeline

```
Month 0:   Deprecation announced; new replacement endpoint/behavior available
Month 1-5: Migration guide available; support team available for migration questions
Month 6:   Sunset; deprecated endpoint returns 410 Gone
```

### Support During Transition

- The deprecated version remains fully functional and supported during the deprecation window.
- Bug fixes and security patches are applied to deprecated endpoints until sunset.
- No new features are added to deprecated endpoints.

### Endpoint Sunset Process

On the sunset date, affected endpoints return:

```http
HTTP/1.1 410 Gone
Content-Type: application/json

{
  "error": {
    "code": "ENDPOINT_RETIRED",
    "message": "This endpoint was retired on 2026-01-01. Please migrate to /v2/events.",
    "docs_url": "https://docs.scouterfrc.com/api/migration/v1-to-v2"
  }
}
```

---

## 16. Breaking Changes Policy

### What Constitutes a Breaking Change

A **breaking change** is any modification that could cause a correctly implemented client to fail or behave incorrectly:

| Change Type | Breaking? |
|-------------|-----------|
| Removing an endpoint | ✅ Yes |
| Renaming a field | ✅ Yes |
| Changing a field's data type | ✅ Yes |
| Changing HTTP method for an endpoint | ✅ Yes |
| Removing a field from a response | ✅ Yes |
| Changing required field to optional | ❌ No |
| Adding a new optional field to a response | ❌ No |
| Adding a new endpoint | ❌ No |
| Adding a new optional request parameter | ❌ No |
| Changing default value of optional parameter | ✅ Yes |

### Versioning Strategy (Semantic Versioning)

The URL version follows semantic versioning principles:

- **Major version** (e.g., `v1` → `v2`): Breaking changes
- **Minor/patch changes**: Backward-compatible additions (no URL increment)

### Announcement Requirements

Breaking changes require:

1. A GitHub issue labeled `breaking-change` documenting the change and rationale.
2. Entry in the API changelog at `docs/API_CHANGELOG.md`.
3. Email notification to all API key holders at least 6 months before the change takes effect.
4. `Deprecation` and `Sunset` headers on affected endpoints.

### Multiple Version Support

ScouterFRC supports at most **two major API versions** simultaneously. When `v3` is released, `v1` is immediately sunset (with its 6-month window having already elapsed).

| Version Status | Supported Simultaneously |
|----------------|--------------------------|
| `v1` (current) + `v2` (deprecated) | ✅ |
| `v1` (deprecated) + `v2` (current) + `v3` (current) | ❌ v1 must be sunset |

---

## 17. Security Best Practices

### HTTPS Only (TLS 1.2+)

All API traffic is encrypted in transit. HTTP requests are rejected with a `301 Moved Permanently` redirect to HTTPS. TLS 1.0 and 1.1 are disabled. TLS 1.3 is preferred.

### CORS Configuration

CORS is configured to allow only registered origins:

```python
CORS_ALLOWED_ORIGINS = [
    "https://app.scouterfrc.com",
    "https://staging.scouterfrc.com",
]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type", "X-Request-ID"]
CORS_MAX_AGE = 86400  # 24 hours preflight cache
```

### CSRF Protection

CSRF protection is applied to session-based (cookie) authentication endpoints. API key and Bearer token endpoints are exempt (not vulnerable to CSRF by nature).

### Input Validation

All incoming request bodies and query parameters are validated against JSON Schema / Pydantic models before reaching business logic. Requests with invalid input return `400 Bad Request` immediately, before any database interaction.

### Output Encoding

All string data is treated as untrusted. Responses are always `Content-Type: application/json`, which prevents injection into HTML contexts. The API never returns raw user input in HTML context.

### SQL Injection Prevention

- All database queries use parameterized queries or ORM query builders. Raw string interpolation into SQL is prohibited.
- Database user has minimum required privileges (no `DROP`, `TRUNCATE`, or schema changes in production).

### API Key Rotation

- API keys should be rotated at least annually.
- Immediate rotation is required if a key is suspected to be compromised.
- Multiple keys can be active simultaneously to allow for zero-downtime rotation.
- Revoked keys are stored (hashed) to detect attempted use after revocation.

### Secret Management

- API keys, JWT signing keys, and OAuth secrets are stored in the platform's secrets manager (e.g., AWS Secrets Manager).
- Secrets are never committed to source code or stored in environment variables directly in production.
- Secrets are rotated using the process documented in `docs/SECURITY_COMPLIANCE_PLAN.md`.

---

## 18. Performance Considerations

### HTTP Caching

Cache-friendly headers are set on `GET` responses where appropriate:

```http
# Immutable event data (data won't change for this event ID)
Cache-Control: public, max-age=300, stale-while-revalidate=60
ETag: "abc123hash"

# Frequently updated data (live match scouting)
Cache-Control: no-cache
```

Clients should store `ETag` and send `If-None-Match` headers to benefit from 304 Not Modified responses.

### Response Compression

All API responses larger than 1 KB are compressed with gzip or brotli:

```http
Accept-Encoding: gzip, br
Content-Encoding: gzip
```

The API gateway handles compression transparently; services return uncompressed responses internally.

### Payload Optimization

- List endpoints return only essential fields by default; clients can use `fields` to specify additional fields: `GET /v1/teams?fields=id,name,team_number,rating`
- Large embedded objects are returned as references by default and can be expanded via `expand`: `GET /v1/matches/2024cmptx_qm12?expand=alliances.teams`

### Performance Targets

| Metric | Target |
|--------|--------|
| p50 latency | < 100 ms |
| p95 latency | < 500 ms |
| p99 latency | < 1,000 ms |
| Availability | 99.9% uptime |
| Error rate | < 0.1% 5xx errors |

### Connection Pooling

Backend services maintain connection pools to PostgreSQL and Redis. The pool size is tuned to the number of worker processes and the database connection limit:

```python
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
DATABASE_POOL_TIMEOUT = 30
```

### Timeout Settings

| Timeout | Value | Description |
|---------|-------|-------------|
| Request timeout | 30 seconds | Maximum time to process any single request |
| Database query | 10 seconds | Maximum time for any single query |
| External API (TBA) | 5 seconds | Timeout on calls to The Blue Alliance API |
| WebSocket idle | 60 seconds | Connection closed if no ping/pong |

---

## 19. Monitoring & Analytics

### API Usage Metrics

The following metrics are collected for every API request and exported to the observability platform:

- `api.request.count` — tagged by endpoint, method, and status code
- `api.request.latency` — histogram (p50/p95/p99) by endpoint
- `api.error.count` — tagged by error code
- `api.rate_limit.hit` — count of rate-limited requests by client type

### Error Rate Tracking

Alerts are triggered when:

- 5xx error rate exceeds 0.5% over a 5-minute window
- Any single endpoint has a 5xx error rate > 1% over 5 minutes
- Authentication failure rate exceeds 5% (potential credential stuffing)

### Latency Monitoring

p95 latency is tracked per endpoint. Alerts trigger when:

- p95 latency for any endpoint exceeds 1,000 ms for 5 consecutive minutes
- p99 latency for any endpoint exceeds 3,000 ms

### Endpoint Popularity

Usage is tracked per endpoint to inform prioritization of optimization efforts and SDK helper methods. The top 10 most-called endpoints are reviewed monthly.

### SDK Usage Statistics

SDK versions are tracked via the `User-Agent` header:

```
User-Agent: ScouterFRC-Python-SDK/1.2.0 Python/3.11
User-Agent: ScouterFRC-JS-SDK/2.1.0 Node/20.0
```

This allows the team to identify which SDK versions are in active use and when it is safe to drop support for old versions.

### Client Tracking

The `X-Request-ID` header (client-generated) is logged alongside every request for end-to-end tracing. If a client does not provide `X-Request-ID`, the API gateway generates one and returns it in the response.

---

## 20. API Client Examples

### cURL Examples

```bash
# Authenticate and store token
export TOKEN="your_access_token_here"

# List all events
curl -H "Authorization: Bearer $TOKEN" \
  https://api.scouterfrc.com/v1/events

# Get specific event details
curl -H "Authorization: Bearer $TOKEN" \
  https://api.scouterfrc.com/v1/events/2024cmptx

# List teams in an event (with pagination)
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.scouterfrc.com/v1/events/2024cmptx/teams?limit=50&offset=0"

# Get team statistics
curl -H "Authorization: Bearer $TOKEN" \
  https://api.scouterfrc.com/v1/teams/254/stats

# Submit scouting data
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 254,
    "match_id": "2024cmptx_qm12",
    "data": {
      "auto_mobility": true,
      "auto_game_pieces": 3,
      "teleop_game_pieces": 8,
      "endgame_position": "stage"
    },
    "notes": "Very fast auto cycle"
  }' \
  https://api.scouterfrc.com/v1/scouting

# Get analytics rankings for an event
curl -H "Authorization: Bearer $TOKEN" \
  https://api.scouterfrc.com/v1/analytics/events/2024cmptx/rankings

# Get AI alliance recommendations
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.scouterfrc.com/v1/alliance-builder/recommendations?event_id=2024cmptx"
```

### JavaScript/TypeScript Examples

```typescript
import { ScouterFRCClient } from '@scouterfrc/api';

const client = new ScouterFRCClient({
  apiKey: process.env.SCOUTERFRC_API_KEY,
});

// List all events
const events = await client.events.list({ limit: 50 });
console.log(`Found ${events.pagination.total} events`);

// Get team details
const team = await client.teams.get('254');
console.log(`Team: ${team.data.name}`);

// Get team stats
const stats = await client.teams.getStats('254');
console.log(`OPR: ${stats.data.opr}`);

// Submit scouting data
const entry = await client.scouting.submit({
  team_id: 254,
  match_id: '2024cmptx_qm12',
  data: {
    auto_mobility: true,
    auto_game_pieces: 3,
    teleop_game_pieces: 8,
    endgame_position: 'stage',
  },
});
console.log(`Scouting entry ID: ${entry.data.id}`);

// Get event rankings
const rankings = await client.analytics.eventRankings('2024cmptx');
rankings.data.forEach((rank, i) => {
  console.log(`${i + 1}. Team ${rank.team_number} — Score: ${rank.score}`);
});

// Subscribe to live updates via WebSocket
const ws = client.realtime.subscribe('event:2024cmptx');
ws.on('scouting.submitted', (payload) => {
  console.log('New scouting entry:', payload.data.scouting_id);
});
```

### Python Examples

```python
from scouterfrc_api import ScouterFRCClient
from scouterfrc_api.exceptions import NotFoundError, RateLimitError

client = ScouterFRCClient(api_key='your-key')

# List all events with automatic pagination
for event in client.events.list_all():
    print(f"Event: {event.name} ({event.start_date})")

# Get team details
team = client.teams.get('254')
print(f"Team: {team.name}")

# Get team statistics
stats = client.teams.get_stats('254')
print(f"OPR: {stats.opr}, DPR: {stats.dpr}")

# Submit scouting data
entry = client.scouting.submit(
    team_id=254,
    match_id='2024cmptx_qm12',
    data={
        'auto_mobility': True,
        'auto_game_pieces': 3,
        'teleop_game_pieces': 8,
        'endgame_position': 'stage',
    },
    notes='Very fast auto cycle',
)
print(f"Entry ID: {entry.id}")

# Get event rankings
rankings = client.analytics.event_rankings('2024cmptx')
for rank in rankings:
    print(f"#{rank.rank} Team {rank.team_number}: {rank.score:.2f}")

# Error handling
try:
    team = client.teams.get('99999')
except NotFoundError:
    print('Team not found')
except RateLimitError as e:
    print(f'Rate limited. Retry after {e.retry_after}s')
```

---

## 21. Phase-Specific API Additions

### Phase 1: Core Foundation

**Goal:** Establish a stable, documented core API for event, team, and match data.

| Endpoint Group | Endpoints |
|----------------|-----------|
| Events | `GET/POST /v1/events`, `GET/PUT/DELETE /v1/events/{id}` |
| Teams | `GET /v1/events/{id}/teams`, `GET /v1/teams/{id}` |
| Matches | `GET /v1/events/{id}/matches`, `GET /v1/matches/{id}` |
| Authentication | OAuth 2.0, API key auth, JWT validation |
| API versioning | `/v1/` prefix on all endpoints |
| Pagination | `limit`/`offset` on all list endpoints |
| OpenAPI spec | Initial `openapi.yaml` with all Phase 1 endpoints |

### Phase 2: Scouting & Analytics

**Goal:** Enable data collection and analysis during competitions.

| Endpoint Group | Endpoints |
|----------------|-----------|
| Scouting | `POST /v1/scouting`, `GET/PUT/PATCH /v1/scouting/{id}`, `GET /v1/events/{id}/scouting` |
| Analytics | `GET /v1/analytics/team/{id}`, `GET /v1/analytics/match/{id}`, `GET /v1/analytics/events/{id}/rankings` |
| Alliance Builder | `POST /v1/alliance-builder`, `GET /v1/alliance-builder/{id}`, `GET /v1/alliance-builder/recommendations` |
| Video Tracking | `GET /v1/videos/{matchId}/tracking`, `/heatmap`, `/trajectory` |
| Webhooks | Webhook management and delivery |
| WebSockets | Real-time data subscriptions |
| Rate Limiting | Per-user, per-key, burst protection |

### Phase 3: AI & Community

**Goal:** Unlock advanced analytics, multi-organization support, and integrations.

| Endpoint Group | Endpoints |
|----------------|-----------|
| AI Recommendations | Enhanced alliance builder with ML-powered suggestions |
| Multi-org | Organization hierarchy, cross-org data sharing APIs |
| Advanced analytics | Custom metrics, trend analysis, predictive rankings |
| Community | Forum/discussion endpoints, shared strategy resources |
| API marketplace | Third-party app registration and approval |

---

## 22. Backward Compatibility

### Contract-Based Versioning

The API contract (as defined in `openapi.yaml`) is the authoritative specification. Any change to the contract that is backward-incompatible triggers a major version increment.

### Additive Changes Only in Minor Versions

Within a major version, only additive changes are permitted:

- New optional fields in responses ✅
- New optional query parameters ✅
- New endpoints ✅
- New enum values in non-exhaustive enums ✅ (with documentation note)

### Removal Only in Major Versions

Removing fields, endpoints, or enum values requires a major version with the full deprecation cycle.

### Optional Field Deprecation

Fields can be deprecated within a major version before removal in the next major version:

```json
{
  "team_number": 254,
  "team_name": "The Cheesy Poofs",
  "nickname": "The Cheesy Poofs"  // deprecated: use team_name
}
```

Deprecated fields are annotated in the OpenAPI spec with `deprecated: true` and documented in `docs/API_CHANGELOG.md`.

### Field Aliases for Renamed Fields

When a field is renamed in a new major version, both the old and new field names are supported during the deprecation window:

```json
{
  "team_id": 254,    // v2 field name (new)
  "teamId": 254      // v1 field name (deprecated alias, available during transition)
}
```

---

## 23. Testing & Validation

### API Integration Tests

Integration tests cover every endpoint in the OpenAPI spec. Tests run against a test database with seeded fixture data:

```python
# backend/tests/test_events_api.py
def test_list_events_pagination(client, seed_events):
    response = client.get('/v1/events?limit=5&offset=0')
    assert response.status_code == 200
    assert len(response.json()['data']) == 5
    assert response.json()['pagination']['total'] == seed_events.count

def test_get_event_not_found(client):
    response = client.get('/v1/events/nonexistent')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'NOT_FOUND'
```

### Load Testing

Load tests are run against the staging environment before each major release:

- **Tool:** Locust or k6
- **Scenarios:** Normal load (100 concurrent users), peak load (500 concurrent users), spike test
- **Acceptance criteria:** p95 latency < 500 ms at 100 concurrent users; no 5xx errors at normal load

### Security Testing

- **OWASP ZAP** is run against the staging API on each release.
- **SQL injection probes** are included in the integration test suite.
- **Authentication bypass tests** verify all protected endpoints require valid tokens.

### Contract Testing with SDKs

The official SDKs are tested against the live staging API to catch integration regressions:

```python
# sdk-tests/test_sdk_contract.py
def test_events_list_matches_openapi_schema(client):
    events = client.events.list()
    for event in events.data:
        assert hasattr(event, 'id')
        assert hasattr(event, 'name')
        assert hasattr(event, 'start_date')
```

### Staging Environment Parity

The staging environment (`api-staging.scouterfrc.com`) mirrors production configuration exactly, including:

- Same database schema and seed data refreshed weekly
- Same rate limiting configuration
- Same authentication configuration
- OpenAPI spec always reflects the staging API state

---

## 24. Rate Limit Scenarios & Examples

### Scenario 1: Normal Authenticated Usage

A scout app submitting data during a competition (user authenticated with OAuth token):

```
1,000 requests/hour limit
Typical match: ~15 scouting submissions
6 matches/hour × 15 submissions = 90 requests/hour
→ Well within limits; no rate limiting expected
```

### Scenario 2: API Key for Data Pipeline

A server-side script syncing scouting data to an external analytics system:

```
5,000 requests/hour limit
Exporting scouting data: ~500 records per event
With pagination (100/page): 5 requests per export
Scheduled every 10 minutes: 6 × 5 = 30 requests/hour
→ Far below limit; no issues expected
```

### Scenario 3: Burst During Match Results

Multiple clients requesting rankings immediately after a match completes:

```
Burst limit: 20 requests/minute
If >20 requests arrive in 1 minute, subsequent requests get 429
Client should implement exponential backoff and retry
Server caches rankings for 15 minutes to reduce burst impact
```

### Scenario 4: Unauthenticated Public Access

A browser hitting the API without a token (e.g., before login):

```
100 requests/hour (IP-based)
Only read endpoints are accessible without auth
Write endpoints return 401 regardless of rate limit
```

### Quota Reset Times

All rate limit windows are fixed-period (not sliding) and reset on the hour:

```
X-RateLimit-Reset: 1713632400  (Unix timestamp of next reset)
```

A client that hits the rate limit at 3:59 PM only needs to wait 1 minute, not a full hour.

### Fallback Strategies

| Strategy | When to Use |
|----------|-------------|
| Exponential backoff | Transient 429 due to burst |
| Request queuing | Predictable high-volume batch jobs |
| SDK retry logic | Automatic retry on any 429 |
| Cache responses | Avoid re-fetching unchanged data (use ETag/304) |
| Stagger requests | Distribute polling across multiple intervals |

---

## 25. Future Considerations

### GraphQL Support (Phase 4)

GraphQL may be introduced as an alternative query layer for clients that need highly flexible data fetching (e.g., complex dashboard queries that would otherwise require many REST calls). REST remains the primary API; GraphQL would be additive.

```
POST /graphql
{
  "query": "{ event(id: \"2024cmptx\") { name teams { teamNumber stats { opr } } } }"
}
```

### gRPC Support (Phase 4)

gRPC may be added for internal service-to-service communication and for latency-sensitive SDK clients (particularly Python analytics pipelines). Proto files would be published in a dedicated `proto/` directory.

### Multi-Protocol Support

The long-term goal is to support REST (primary), GraphQL (flexible client queries), and gRPC (high-performance server clients) from a single schema source of truth, with the OpenAPI/Proto definitions generated from the same data model.

### API Marketplace (Phase 3)

A developer portal allowing third-party apps to register, obtain API credentials, and be listed in an official ScouterFRC integration directory. This enables the FRC community to build tools (e.g., scouting overlays, match prediction models) that integrate natively with ScouterFRC data.

### Developer Community Portal

A dedicated developer hub at `developers.scouterfrc.com` with:

- API reference documentation (Swagger UI)
- Getting started guides
- SDK documentation
- Community forum for API questions
- Changelog and release notes
- API status page

---

*ScouterFRC API Strategy — Version 1.0 — Last Updated: 2024-04-20*
