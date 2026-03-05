# Production Hardening — Future Work

Notes on securing the application for internet-facing deployment. Not yet
implemented — documenting the strategy for when we're ready.

---

## Threat Surface

The application is a FastAPI + SQLite single-instance deployment. No metered
cloud services or billing APIs, so the primary cost vector is compute and
bandwidth rather than per-request charges. The main risks:

1. **Expensive GET endpoints** — `get_character` runs 6+ DB queries per call
   (items, AC, weapons, encumbrance, retainers, mercenaries, specialists).
   The referee panel multiplies that across every active character. These are
   the most CPU-intensive endpoints and the most attractive DDoS targets.

2. **SQLite write contention** — SQLite serializes all writes. Spamming write
   endpoints (HP updates, XP awards, round-effects) can block all other write
   operations and stall the application.

3. **Dev token endpoint** — `POST /api/auth/token` bypasses OAuth entirely.
   Must be disabled in any internet-facing deployment.

4. **Unauthenticated surface** — Anything reachable without a valid JWT is
   the widest attack surface for anonymous abuse.

---

## Recommended Mitigations

### 1. Rate Limiting Middleware (high impact, moderate effort)

Use `slowapi` (Python library built on `limits`) wired into FastAPI.

**Strategy — tiered limits with user/IP split:**

- **Per-IP (unauthenticated):** Tight limits since only the auth flow should
  be hit without a JWT. Something like 10 req/min.
- **Per-user (authenticated):** Higher limits keyed to JWT user ID. Legitimate
  use during combat involves frequent refreshes.
- **Tiered by endpoint cost:**
  - Cheap reads (list campaigns, get spell): generous (e.g. 120 req/min)
  - Expensive reads (get character, referee panel): tighter (e.g. 30 req/min)
  - Write endpoints (HP, XP, round-effects): moderate (e.g. 30 req/min)
  - Auth endpoints: very tight (e.g. 5 req/min per IP)

This matches actual usage patterns — a GM refreshing the referee panel during
combat is legitimate high-frequency use, an anonymous IP hammering it is not.

### 2. Reverse Proxy — nginx (high impact, low effort)

Run nginx in front of uvicorn. This provides:

- **Connection-level rate limiting** (`limit_req_zone`, `limit_conn_zone`) —
  drops abusive connections before they reach Python
- **Request buffering** — absorbs slow clients without tying up uvicorn workers
- **SSL termination** — HTTPS without burdening the application
- **Static file serving** — serve the SvelteKit build directly from nginx

nginx is preferred over caddy here because `limit_req_zone` and
`limit_conn_zone` give fine-grained connection control specifically suited
to DDoS mitigation. This is the first line of defense; FastAPI rate limiting
is the second.

Ship an example nginx config in a `deploy/` directory to keep self-hosting
easy.

### 3. Disable Dev Token in Production (high impact, trivial effort)

Gate `POST /api/auth/token` behind an environment variable:

```python
# In auth router setup
if settings.ENABLE_DEV_TOKEN:
    router.add_api_route("/token", dev_token_endpoint, methods=["POST"])
```

Default `ENABLE_DEV_TOKEN=false`. Only local `.env` files enable it.

### 4. CORS Tightening (low effort)

Currently CORS allows origins from config. For production, ensure the allowed
origin list is locked to the actual frontend domain rather than wildcards.
Read from `.env`:

```
CORS_ORIGINS=https://my-ose-sheets.example.com
```

### 5. Response Caching (moderate impact, moderate effort) — DEFERRED

Brief caching (5–10 seconds) on expensive GET endpoints would eliminate
repeated hammering. However, it introduces cache invalidation complexity
(edit character then GET returns stale data). SQLite reads are fast enough
that rate limiting alone likely handles the abuse case. Revisit if moving
to PostgreSQL or seeing actual performance issues.

---

## Implementation Order (when ready)

1. Dev token env gate (5 minutes, immediate win)
2. CORS from env (5 minutes)
3. `slowapi` rate limiter with tiered config (a few hours)
4. `deploy/` directory with nginx example config (an hour)
5. Response caching (only if needed)

---

## What We're NOT Worried About

- **Cloud billing attacks** — no metered services, no pay-per-request APIs
- **Data exfiltration** — all data access is gated behind OAuth + permission
  checks (GM/player roles)
- **SQL injection** — SQLAlchemy ORM parameterizes all queries
- **XSS** — Svelte auto-escapes template expressions
- **Centralized scaling** — this is designed for self-hosted single-instance
  deployment, not multi-tenant SaaS
