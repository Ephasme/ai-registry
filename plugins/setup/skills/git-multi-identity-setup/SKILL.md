---
name: git-multi-identity-setup
description: Set up per-directory git identity profiles (email, SSH signing key, SSH auth key, commit signing) using gitconfig includeIf. Use this whenever the user wants to configure different git identities for different projects, set up SSH commit signing, use separate SSH keys for work vs personal GitHub accounts, migrate from a single global git identity to per-directory profiles, or replicate this kind of setup on a new machine. Trigger even if the user just says "set up my git identities" or "configure work and personal git separately".
---

# Git Multi-Identity Setup

Set up clean, per-directory git identity profiles where each code root gets its own email, SSH signing key, SSH auth key, and commit signing config — no global defaults, no cross-contamination between profiles.

## What this creates

For each profile:
- `~/.gitconfig-<profile>` — email, signingkey, sshCommand, gpg.ssh.allowedSignersFile
- `~/.ssh/allowed_signers_<profile>` — enables `git log --show-signature` to display verified signatures

In `~/.gitconfig`:
- One `[includeIf "gitdir:~/code/<dir>/"]` block per profile
- No default email or signingkey (commits outside configured dirs fail loudly — intentional)

## Step 1: Gather profile information

Ask the user (or infer from context) before writing any files:

1. **How many profiles?** (typically 2: work + personal)
2. **For each profile:**
   - Short name (e.g. `sherpas`, `perso`)
   - Code root directory (e.g. `~/code/sherpas/`, `~/code/perso/`)
   - Git email address
   - SSH key name (e.g. `id_ed25519_sherpas`) — must exist at `~/.ssh/<name>` and `~/.ssh/<name>.pub`
3. **Any repos with a custom SSH host alias in their remotes?** (e.g. `git@work.github.com:org/repo`) — these need updating to `git@github.com:org/repo`

Check what SSH keys exist:
```bash
ls ~/.ssh/*.pub
```

## Step 2: Update `~/.gitconfig`

Read the file first. Then:
- Remove `user.email` and `user.signingkey` from the global `[user]` section (they move to profile files)
- Keep `user.name`, and these signing settings (add them if missing):
  ```ini
  [gpg]
      format = ssh
  [gpg "ssh"]
      program = ssh-keygen
  [commit]
      gpgsign = true
  [tag]
      gpgsign = true
  ```
- Add one `[includeIf]` block per profile at the end:
  ```ini
  [includeIf "gitdir:~/code/sherpas/"]
      path = ~/.gitconfig-sherpas

  [includeIf "gitdir:~/code/perso/"]
      path = ~/.gitconfig-perso
  ```

## Step 3: Create per-profile gitconfig files

For each profile, write `~/.gitconfig-<profile>`:

```ini
[user]
    email = <email>
    signingkey = /Users/<username>/.ssh/<key>.pub

[core]
    sshCommand = ssh -i ~/.ssh/<key> -o IdentitiesOnly=yes

[gpg "ssh"]
    allowedSignersFile = ~/.ssh/allowed_signers_<profile>
```

**Why `core.sshCommand` instead of `~/.ssh/config` host aliases?**
The `sshCommand` is scoped to a directory via `includeIf`, so the right key is picked automatically without needing a custom hostname (like `work.github.com`). Remote URLs stay clean (`git@github.com:org/repo`) and no SSH config entries are needed per profile. Once `sshCommand` is in place, any GitHub host aliases in `~/.ssh/config` can be removed.

## Step 4: Create allowed signers files

For each profile, write `~/.ssh/allowed_signers_<profile>` with one line:

```
<email> <pubkey-type> <pubkey-data>
```

Get the key content from:
```bash
cat ~/.ssh/<key>.pub
```

Example result:
```
loup.peluso@sherpas.com ssh-ed25519 AAAAC3Nz... loup.peluso@sherpas.com
```

## Step 5: Clean up `~/.ssh/config`

Read `~/.ssh/config`. Remove any GitHub-specific host entries — both the generic `Host github.com` with an IdentityFile, and any custom aliases like `Host work.github.com`. The `sshCommand` in each profile's gitconfig handles key selection now.

Keep all non-GitHub entries (servers, NAS, CI runners, etc.) untouched.

## Step 6: Update existing repo remotes (if needed)

If any repos used a custom SSH host alias in their remotes, bulk-update them:

```bash
find ~/code/<dir> -maxdepth 4 -name ".git" -type d | while read gitdir; do
  repo="${gitdir%/.git}"
  remote=$(git -C "$repo" remote get-url origin 2>/dev/null)
  if echo "$remote" | grep -q "<alias>.github.com"; then
    new="${remote/<alias>.github.com/github.com}"
    git -C "$repo" remote set-url origin "$new"
    echo "updated: $repo → $new"
  fi
done
```

Also clear any local `user.email` and `core.sshCommand` overrides in individual repos (they're superseded by the profile files). Always check both — `sshCommand` is commonly set per-repo when setting up key-based auth before a profile system exists:

```bash
for setting in user.email core.sshCommand; do
  find ~/code/<dir> -maxdepth 4 -name ".git" -type d | while read gitdir; do
    repo="${gitdir%/.git}"
    val=$(git -C "$repo" config --local "$setting" 2>/dev/null)
    [ -n "$val" ] && git -C "$repo" config --unset "$setting" && echo "cleared $setting: $repo"
  done
done
```

## Step 7: Verify everything works

```bash
# 1. Email resolves correctly per directory
git -C ~/code/<work-dir>/any-repo config user.email    # → work email
git -C ~/code/<perso-dir>/any-repo config user.email   # → personal email

# 2. SSH auth works on updated remotes
git -C ~/code/<work-dir>/any-repo ls-remote --heads origin 2>&1 | head -3

# 3. Commit signing uses the right key
git -C ~/code/<work-dir>/any-repo commit --allow-empty -m "test: signing"
git -C ~/code/<work-dir>/any-repo log --show-signature -1
git -C ~/code/<work-dir>/any-repo reset --hard HEAD~1
```

A correctly configured repo shows:
```
Good "git" signature for <email> with ED25519 key SHA256:...
```

If `--show-signature` shows "Good" but "No principal matched", that commit predates the allowed signers setup — not a problem going forward.
