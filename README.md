# SE Ranking Connector

[![Imperal SDK](https://img.shields.io/badge/imperal--sdk-5.9.12-blue)](https://pypi.org/project/imperal-sdk/)
[![Version](https://img.shields.io/badge/version-1.3.0-green)](https://github.com/SeeuWHM/imperal-se-ranking-connector-extension/releases)
[![License](https://img.shields.io/badge/license-LGPL--2.1-orange)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Imperal%20Cloud-purple)](https://panel.imperal.io)

**[SE Ranking](https://online.seranking.com/) SEO extension for [Imperal Cloud](https://panel.imperal.io).**

Projects, keyword rankings, SEO opportunities, CTR gaps, site audits, keyword research, domain and competitor analysis, and backlinks — through natural language.

---

## What It Does

Talk to it naturally:

```
"show me my SE Ranking projects"
"how are we ranking for managed wordpress hosting"
"what are my quick-win keywords right now"
"найди пробелы против конкурентов"
"сколько бэклинков у competitor.com"
"estimate the cost before you research that keyword"
```

Or open the sidebar panel — connect an account, switch between several, and click any tracked project to see its rankings and top content opportunities rendered server-side (zero LLM tokens).

---

## Capabilities

### Projects & Rankings
| Function | Description |
|----------|-------------|
| `list_projects` | Your tracked SE Ranking projects — id, title, url, keyword count |
| `rankings` | Current Google positions for all tracked keywords in a project |
| `opportunities` | Zero-credit content opportunities: quick wins (rank 4–20), untracked keywords |
| `ctr_gaps` | High-impression, low-CTR keywords — titles/meta likely need work |

### Keyword Research & Domain Analysis
| Function | Description |
|----------|-------------|
| `estimate_keyword_cost` | Credit cost estimate for a keyword expansion — always call first |
| `research_keywords` | Expand a seed keyword into longtail / related / question variants (spends credits) |
| `domain_overview` | Traffic overview for any domain — organic traffic, keyword count, top pages (spends credits) |
| `domain_keywords` | Keywords a domain ranks for, organic or paid (spends credits) |
| `audit_project` | Zero-credit project health audit — CTR gaps, untracked-but-ranking keywords, wasted deep-ranking slots |

### Competitor Tracking
| Function | Description |
|----------|-------------|
| `list_competitors` / `add_competitor` / `delete_competitor` | Manage the competitor domains tracked per project |
| `competitor_positions` | A tracked competitor's keyword positions |
| `serp_top10` | Current top-10 Google results for one tracked keyword |
| `all_competitors` | Discover every domain appearing in top-10 for your tracked keywords |
| `competitor_gaps` | Keywords competitors rank for that you don't (or rank much lower) — feeds Article Writer briefs |

### Backlinks
| Function | Description |
|----------|-------------|
| `backlinks_summary` | Backlink authority summary for any domain — totals, dofollow/nofollow split, top anchors (spends credits) |
| `domain_authority` | Authority scores for up to 100 domains in one call (spends credits) |

### Account Connection
| Function | Description |
|----------|-------------|
| `connection_status` | Whether an SE Ranking account is currently connected |
| `save_seranking_key` | Connect an SE Ranking account — validates the key live before saving; connecting again adds another account instead of replacing it |
| `list_seranking_accounts` | Every connected account, masked key, which one is active |
| `switch_seranking_account` | Make a different connected account the active one |
| `disconnect_seranking_account` | Disconnect one account by label |
| `disconnect_seranking` | Disconnect every connected account |

---

## Architecture

```
User (chat)
    ↓
se-ranking-connector (this extension)
    │  Authorization: Bearer <backend_jwt>        — app-level, developer-set, same for every install
    │  X-SER-API-Key: <caller's own SE Ranking key> — user-level, one of several connected accounts
    ↓
se-ranking-control (shared backend microservice — https://api.webhostmost.com/se-ranking/)
    ↓
SE Ranking API (online.seranking.com)
```

Two distinct credentials travel on every call. `backend_jwt` authenticates *this extension* to the
shared `se-ranking-control` microservice — one value for every installer, developer-managed only,
never entered or seen by end users. The caller's **own** SE Ranking API key is a real per-user
credential: each user connects their own account (own subscription, own credit quota) through the
sidebar's Connect form or `save_seranking_key`, and can connect several keys at once and switch
between them (`ser_accounts.py`) — the backend partitions caching and daily credit quota per key so
one user's data or spend never leaks into another's.

Endpoints scoped to a specific account (projects, rankings, harvest, competitors, audit, backlinks)
require the caller's own key and say so clearly when it's missing. Keyword research and domain
analysis aren't scoped to one account, so those still work on the backend's shared default key even
before a user connects anything.

---

## File Structure

```
imperal-se-ranking-connector-extension/
├── main.py                  # Entry point — sys.modules purge/reload + import order; removes ext
│                             #   dir from sys.path after load (cross-extension module shadowing fix)
├── app.py                    # Extension + ChatExtension setup, secret declarations, health check
├── cache_helpers.py           # ctx.cache wrapper for panel reads — project list (120s TTL),
│                             #   rankings/opportunities (240s TTL); keyed on scope + sha256(api_key)
├── api_client.py             # call_ser() — single HTTP bridge to se-ranking-control;
│                             #   require_user_key short-circuit; headers_override for key validation
├── ser_accounts.py           # Multi-account key storage — add/switch/disconnect/mask,
│                             #   legacy single-key migration
├── params.py                 # Pydantic param models for every chat function
├── response_models.py        # Pydantic response models + dedupe_opportunities()
├── skeleton.py                # ser_config (TTL 300s) + ser_projects (TTL 600s) skeleton providers
├── handlers.py                # list_projects, rankings, opportunities, ctr_gaps
├── handlers_research.py       # estimate_keyword_cost, research_keywords, domain_overview,
│                              #   domain_keywords, audit_project
├── handlers_settings.py       # connection_status, save/list/switch/disconnect account handlers
├── handlers_competitors.py    # list/add/delete_competitor, competitor_positions, serp_top10,
│                              #   all_competitors, competitor_gaps
├── handlers_backlinks.py      # backlinks_summary, domain_authority
├── panels.py                  # sidebar (left): account selector + connect form + project list
├── panels_workspace.py         # workspace (center): one project's rankings + top opportunities
├── icon.svg                   # SE Ranking's official brand mark
├── imperal.json                # Extension manifest (generated by `imperal build`)
└── tests/                      # test_cache_helpers.py — 3 tests: fetch-once/serve-from-cache,
                                 #   per-api-key and per-extra-params key separation
```

---

## Function Reference

| Function | Type | Description |
|----------|------|-------------|
| `list_projects` | read | List your SE Ranking projects |
| `rankings` | read | Current keyword positions for a project |
| `opportunities` | read | Zero-credit content opportunities |
| `ctr_gaps` | read | High-impression, low-CTR keywords |
| `estimate_keyword_cost` | read | Credit cost estimate before researching a keyword |
| `research_keywords` | read | Longtail / related / question keyword expansion |
| `domain_overview` | read | Traffic/keyword overview for a domain |
| `domain_keywords` | read | Keywords a domain ranks for (organic or paid) |
| `audit_project` | read | Zero-credit project health audit |
| `connection_status` | read | Whether an SE Ranking account is connected |
| `save_seranking_key` | write | Connect (validate + store) an SE Ranking API key |
| `list_seranking_accounts` | read | List every connected account |
| `switch_seranking_account` | write | Switch the active account |
| `disconnect_seranking_account` | destructive | Disconnect one account |
| `disconnect_seranking` | destructive | Disconnect every account |
| `list_competitors` | read | List tracked competitor domains |
| `add_competitor` | write | Track a new competitor domain |
| `delete_competitor` | write | Stop tracking a competitor |
| `competitor_positions` | read | A tracked competitor's keyword positions |
| `serp_top10` | read | Top-10 SERP results for one keyword |
| `all_competitors` | read | Discover organic competitors in top-10 |
| `competitor_gaps` | read | Keyword gaps vs. tracked competitors |
| `backlinks_summary` | read | Backlink authority summary for a domain |
| `domain_authority` | read | Authority scores for up to 100 domains |

Plus 2 internal skeleton refreshers (`skeleton_refresh_ser_config`, `skeleton_refresh_ser_projects`) that keep Webbee's context warm between chat turns — not user-callable functions, but counted in the manifest's 26 total tools.

---

## Secrets

| Secret | Scope | Write mode | Required | Purpose |
|--------|-------|------------|----------|---------|
| `backend_jwt` | app | extension | yes | Authenticates this extension to `se-ranking-control`. Developer-managed only. |
| `seranking_api_key` | user | both | no | Legacy single-key secret — kept so pre-existing connections keep working; auto-migrated into `seranking_accounts` on first read. |
| `seranking_accounts` | user | extension | no | Current source of truth — JSON list of `{label, api_key, is_active}`. Managed only through this extension's connect/switch/disconnect functions. |

---

## Development

```bash
python3 -m py_compile *.py   # syntax check before every commit
pytest tests/ -q              # 3 tests: cache_helpers hit/miss + key separation
imperal validate .            # 0 errors/warnings
```

Beyond `cache_helpers.py`'s unit tests, every endpoint's actual data quality is verified live
against the real SE Ranking API through the platform — see the endpoint-by-endpoint audit results
in this project's SE Ranking hardening notes.

---

## Built with

- [imperal-sdk](https://github.com/imperalcloud/imperal-sdk) 5.9.12
- [Imperal Cloud](https://panel.imperal.io)
