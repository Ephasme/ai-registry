# Disk-cleanup category taxonomy (macOS)

Path-by-path reference. Read this when you need to judge a specific location the
assessment surfaced and it isn't covered by the scripts. The guiding question for
each item: **what does deleting this actually cost?**

## 🟢 Regenerable — wipe freely (handled by `clean-safe-caches.sh`)

| Path | What it is | Cost of deleting |
|---|---|---|
| `~/.cache/uv` | uv Python package cache | re-downloaded on next `uv`/install |
| `~/.cache/{pip,puppeteer,pyright-python,pre-commit,firebase,node,gh}` | tool caches | rebuilt on demand |
| `~/Library/Caches/*` | general app caches | apps rebuild them |
| `~/Library/Developer/Xcode/DerivedData` | Xcode build products/index | next build is slower |
| `~/Library/Developer/Xcode/iOS DeviceSupport` | per-device symbols | re-created on device connect |
| `~/.npm/_cacache` | npm content cache | re-downloaded on install |
| `~/.gradle/caches` | Gradle build cache | re-downloaded/rebuilt |
| Editor `Cache`,`Code Cache`,`GPUCache`,`CachedData`,`CachedExtensionVSIXs`,`logs` | Electron caches | regenerated on launch |
| `xcrun simctl delete unavailable` | orphaned simulators | none — they're already broken |
| `brew cleanup`, `docker builder prune` | old formula versions / build cache | re-downloaded/rebuilt |

**Never** treat these as cache even though they sit nearby:
`Application Support/<app>/User`, `workspaceStorage`, `backups`, `*-sessions`,
`Local Storage`, `IndexedDB`, `History`, `Login Data`, mail stores. They are
state, not cache.

## 🟠 Recoverable with impact — confirm scope first

| Path | What it is | Notes |
|---|---|---|
| `**/node_modules` | JS deps | `reclaim-node-modules.sh`; breaks projects until reinstall |
| `~/Library/Android/sdk` | Android SDK | large, re-downloadable; keep if doing Android dev |
| `~/.android/avd` | Android emulators | config + state lost; re-creatable |
| `~/Library/Developer/CoreSimulator` | iOS sim runtimes/devices | `simctl delete unavailable` first; full delete re-downloads |
| Docker images/volumes/`Docker.raw` | containers & data | see `docker-reclaim.sh`; volumes may hold real data |
| `~/go/pkg/mod`, `~/.cargo/registry`, `~/.rustup`, `~/.m2/repository` | language module/registry caches | re-downloaded; safe-ish but can be slow to refill |
| `~/Library/Caches/com.apple.dt.Xcode` | Xcode misc | regenerable |

## 🔴 Personal / irreplaceable — back up or confirm per item

- `~/Downloads` — triage by category (see SKILL.md), never bulk-delete; keep `*.pdf`.
- `~/.Trash` — emptying is permanent; confirm.
- `~/Library/Application Support/Google/Chrome`, `.../Firefox`, browser profiles —
  history, logins, extensions. Only the `Cache`/`Code Cache` subdirs are 🟢.
- `~/Documents`, `~/Desktop`, `~/Pictures`, `~/Movies` — user data.
- Local DB volumes / dumps, mail stores, Photos library, iMessage, Notes.

## ⚠ Sensitive — flag loudly, never silently delete

Password-manager exports (`*.1pux`, vault `*.csv`), private keys (`*.pem`,
`id_rsa*`, `*.p12`), keychains (`*.keychain*`), crypto wallet/seed files. These
are a security risk if left lying around (especially in Downloads) AND a disaster
if deleted without the user knowing. Surface them, recommend secure relocation or
deletion, and confirm.

## Big-win checklist (typical order of magnitude on a dev Mac)

1. `~/.cache/uv` — tens of GB
2. `~/Library/Developer/Xcode/DerivedData` — tens of GB
3. `~/Library/Caches` — tens of GB
4. `Docker.raw` (full reset) — 10–30+ GB, **only after inspecting volumes**
5. Android SDK + AVD — ~15 GB
6. `node_modules` sweep — several GB
7. `~/.npm`, `~/.gradle/caches` — several GB each
8. Downloads triage + dedupe — varies
