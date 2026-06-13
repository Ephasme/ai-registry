---
name: web-unlocker
description: Fetch a web page through BrightData's Web Unlocker proxy when an ordinary fetch fails or returns unusable content. Use this skill whenever retrieving a URL is blocked or degraded — HTTP 403/429, Cloudflare or other "are you human" / anti-bot interstitials, CAPTCHA walls, "Access Denied", bot detection, rate limiting, geo-restricted pages, or JavaScript-only pages that hand a plain fetch empty or garbled HTML. Trigger it when WebFetch, curl, or the research plugin's web fetch comes back empty, truncated, or shows a challenge page instead of the real content, and when the user says a site is "blocking me", "won't let me scrape", "needs a real browser", or asks to pull content from a hard-to-scrape, protected, or region-locked URL. Returns the resolved page as raw HTML or clean Markdown, optionally geo-targeted by country.
---

# Web Unlocker

Some pages can't be fetched the ordinary way: they sit behind Cloudflare or another anti-bot wall, demand a CAPTCHA, block datacenter IPs with a 403/429, render only via JavaScript, or serve different content by region. BrightData's Web Unlocker routes the request through a residential proxy that solves the challenge, runs a real browser when needed, and returns the resolved content — so you get the actual page instead of a "verify you are human" interstitial.

This skill wraps that API in a single bundled script that resolves the API key for you, builds the request safely, and surfaces API errors clearly.

## When to reach for it

Escalate to the Web Unlocker only **after** a normal fetch has failed or come back unusable — it costs a metered API request per call, so don't burn it on pages that fetch fine. Signs you should escalate:

- A plain `WebFetch` / `curl` returns empty, truncated, or obviously-wrong content (a challenge page, a login wall, a "checking your browser" splash).
- HTTP **403 / 429 / 503**, "Access Denied", or a Cloudflare/PerimeterX/Datadome interstitial.
- The page is a JavaScript SPA that ships no meaningful HTML without rendering.
- The content is **geo-restricted** and you need it as seen from a specific country.
- The user explicitly says a site is blocking them, needs "a real browser", or asks to scrape a known-protected source.

If a normal fetch already works, just use that.

## How to run it

The skill is the bundled script. Call it with the target URL:

```bash
"$CLAUDE_PLUGIN_ROOT/skills/web-unlocker/scripts/web_unlocker.sh" <url>
```

When running inside a clone of the ai-registry repo (not via the installed plugin), call the script by its path in the repo. It prints the resolved page to stdout; redirect or use `-o` to save it.

### Options

| Option | Effect | Use when |
| --- | --- | --- |
| `--markdown` | Return clean Markdown (`data_format=markdown`) instead of raw HTML | You want to **read or extract** the content — Markdown is far cheaper to reason over than full HTML |
| `--country <cc>` | Geo-target via 2-letter country code (`us`, `gb`, `de`, `fr`, …) | The page is region-locked or shows different content per country |
| `--zone <name>` | BrightData zone (default `web_unlocker`) | You use a non-default unlocker zone |
| `--format <fmt>` | `raw` (default, body only) or `json` (BrightData metadata wrapper) | You need the response headers/status BrightData saw |
| `-o, --output <f>` | Write the body to a file instead of stdout | The page is large — saving avoids dumping tens of KB into the transcript |
| `--timeout <secs>` | curl max time (default 120) | A slow target needs longer |

### Typical calls

```bash
# Get a blocked page as raw HTML
web_unlocker.sh https://example.com/blocked-page

# Pull an article as clean Markdown, straight to a file (preferred for reading)
web_unlocker.sh --markdown https://news.site/article -o /tmp/article.md

# Fetch a UK-only page as seen from Britain
web_unlocker.sh --country gb --markdown https://shop.example/uk-only -o /tmp/page.md
```

**Prefer `--markdown` + `-o <file>` when the goal is to read or extract content.** A real page can be tens of thousands of bytes of HTML; Markdown to a file keeps the transcript clean and gives you content that's easy to grep, summarize, or quote. Read the file back with the Read tool. Use raw HTML only when you specifically need the markup (e.g. extracting attributes, links, or structured data the Markdown drops).

## Reading the result

- On success the script writes the page body to stdout (or to `-o`'s file) and exits 0.
- On an API-level failure (bad zone, auth, quota, target error) it prints the HTTP status and the BrightData response body to **stderr** and exits non-zero — read that message; it usually names the problem ("zone … not found", quota exceeded, etc.).
- A bad/missing URL exits 2.

## API key handling

The key is **never hardcoded**. The script resolves it at runtime, in order:

1. `$BRIGHTDATA_API_KEY` if set in the environment (override / fresh-machine escape hatch).
2. SOPS-decrypts the committed, age-encrypted secret `secrets/brightdata.sops.json` (searched in the marketplace clone under `$CLAUDE_CONFIG_DIR/plugins/marketplaces/ai-registry/secrets/`, and by walking up from the script when run inside a repo clone).

Decryption needs `sops` plus the age private key at `~/.config/sops/age/keys.txt`. If you're on a machine without that key, `export BRIGHTDATA_API_KEY=<key>` and the script will use it. If the script reports it "could not resolve the BrightData API key", that's the fix.

## Cost awareness

Each call is a billable Web Unlocker request against the user's BrightData account. Fetch once and reuse the saved output rather than re-fetching; don't loop the unlocker over many URLs without the user's go-ahead.

## More parameters

The underlying `/request` endpoint supports more than this skill exposes by default — JS rendering controls, screenshots, custom headers/cookies, sessions, mobile user-agents, and async jobs. See [references/brightdata-api.md](references/brightdata-api.md) for the full parameter list and how to pass extras, and only reach for it when the default raw/markdown/country options aren't enough.
