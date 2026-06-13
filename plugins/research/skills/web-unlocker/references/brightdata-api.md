# BrightData Web Unlocker — `/request` API reference

The skill's `web_unlocker.sh` covers the common path (raw / markdown / country).
This file documents the full endpoint for the cases where the defaults aren't
enough. Official docs: https://docs.brightdata.com/scraping-automation/web-unlocker/

## Endpoint

```
POST https://api.brightdata.com/request
Content-Type: application/json
Authorization: Bearer <API_KEY>
```

The raw shape (this is the exact call the script makes):

```bash
curl https://api.brightdata.com/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_KEY>" \
  -d '{"zone":"web_unlocker","url":"https://example.com","format":"raw"}'
```

## Request body parameters

| Field | Type | Notes |
| --- | --- | --- |
| `zone` | string | Unlocker zone name. Default in the script: `web_unlocker`. |
| `url` | string | Target URL (must be `http(s)://`). |
| `format` | string | `raw` → response body only (default). `json` → BrightData wraps the body with status, headers, and metadata. |
| `data_format` | string | `markdown` returns the page converted to Markdown. Omit for the page as-is (HTML). Combine with `format:raw` to get raw Markdown. |
| `country` | string | 2-letter country code (lowercase, e.g. `us`, `gb`, `de`) to route through a proxy in that country. The script lowercases this for you. |
| `method` | string | HTTP method for the target request (`GET` default). Use `POST`/etc. for form submissions. |
| `headers` | object | Custom request headers sent to the target. |
| `cookies` | string/array | Cookies to send to the target. |
| `body` | string | Request body for non-GET methods. |
| `ua` | string | `mobile` to use mobile-device User-Agents (or pass a full UA via `headers`). |

### Rendering / browser features

Available on rendering-capable zones; consult the docs before relying on them:

- JavaScript rendering and waits (render the page in a real browser before returning).
- **Screenshots** — return a PNG of the rendered page instead of HTML.
- Sessions — reuse the same IP/cookies across calls for multi-step flows.
- Async jobs — submit a request and poll for the result, for slow targets.

## Passing parameters the script doesn't expose

`web_unlocker.sh` only builds `zone`, `url`, `format`, `data_format`, and
`country`. For anything else, call the endpoint directly. Resolve the key the
same way the script does so you still never hardcode it:

```bash
KEY="$(sops -d "$CLAUDE_CONFIG_DIR/plugins/marketplaces/ai-registry/secrets/brightdata.sops.json" \
  | jq -r .BRIGHTDATA_API_KEY)"
# (or just use $BRIGHTDATA_API_KEY if it's exported)

curl -sS https://api.brightdata.com/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  -d "$(jq -n --arg url "https://example.com" '{
        zone: "web_unlocker",
        url: $url,
        format: "raw",
        method: "GET",
        headers: {"Accept-Language": "en-GB"},
        ua: "mobile"
      }')"
```

Build the JSON with `jq -n` (as above) rather than hand-writing it — it escapes
the URL and any header values correctly.

## Errors

- Non-2xx HTTP from `api.brightdata.com` means an API-level problem (auth,
  quota, unknown zone, malformed body). When `format:json`, the body explains
  it; when `format:raw`, the body is usually a short plaintext reason
  (e.g. `zone "x" not found`).
- A 2xx with challenge-page content can still happen on a misconfigured zone —
  inspect the body, and try a rendering-capable zone or `--country` if so.

## Test endpoints (no real target needed)

BrightData exposes endpoints that echo the proxy details it used — handy for
verifying the key and country targeting without scraping a real site:

- `https://geo.brdtest.com/welcome.txt?product=unlocker&method=api` — plaintext.
- `https://geo.brdtest.com/mygeo.json?product=unlocker&method=api` — JSON; the
  reported country reflects the `--country` you passed.
