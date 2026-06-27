# Linux equivalents

The scripts are macOS-first. On Linux, the workflow and tiers are identical —
only paths and a few commands change. Translate as follows.

## Measuring free space

macOS `diskutil info / | grep "Free Space"` → Linux:

```bash
df -h --output=avail / | tail -1       # available on /
df -h /                                # full picture
```

(Linux `df` is accurate; no APFS-container caveat.)

## 🟢 Regenerable caches

| macOS | Linux |
|---|---|
| `~/Library/Caches` | `~/.cache` (XDG cache home) |
| `~/.npm/_cacache` | same |
| `~/.gradle/caches` | same |
| Xcode DerivedData / DeviceSupport | n/a (no Xcode) |
| editor `Cache`/`Code Cache` under `Application Support` | same subdirs under `~/.config/<App>` |
| `brew cleanup` | `apt-get clean` / `dnf clean all` / `pacman -Sc` (system pkg caches; needs sudo) |
| `~/.cache/uv`, `~/.cache/pip`, etc. | same (already XDG) |

Extra Linux-only wins:
- `journalctl --vacuum-size=200M` (systemd logs, needs sudo)
- `~/.cache/thumbnails`
- old kernels: `apt-get autoremove --purge` (sudo)
- snap old revisions: `sudo snap set system refresh.retain=2` then remove disabled snaps

## 🟠 Recoverable

| macOS | Linux |
|---|---|
| `Docker.raw` (sparse image) | Docker uses `/var/lib/docker` directly — `docker system prune -a --volumes` actually frees space (no `.raw` to delete). Still inspect volumes first. |
| `~/Library/Android/sdk` | `~/Android/Sdk` |
| `~/.android/avd` | same |
| CoreSimulator | n/a |
| `~/go/pkg/mod`, `~/.cargo`, `~/.m2` | same paths |

## 🔴 Personal

- `~/Downloads`, `~/.local/share/Trash` (Linux trash), `~/Documents`, etc.
- Browser profiles under `~/.config` / `~/.mozilla`.

## Docker on Linux

No `Docker.raw`. The data is in `/var/lib/docker`, and pruning reclaims space
immediately:

```bash
docker system df -v          # inspect (same as macOS)
docker builder prune -af     # safe: build cache
docker image prune -f        # safe: dangling images
docker system prune -a --volumes   # FULL: destroys unused images + ALL unused volumes — confirm first
```
