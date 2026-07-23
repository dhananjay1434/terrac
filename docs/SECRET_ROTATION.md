# Secret Rotation — Current State + Procedure

## Current state (re-verified 2026-07-23)

```
$ git ls-files demo_tools/ | grep -i secret
demo_tools/demo_secrets.example.bat

$ git check-ignore demo_tools/demo_secrets.bat
demo_tools/demo_secrets.bat        # printed = ignored, confirmed

$ git log --all --oneline -- demo_tools/demo_secrets.bat
                                    # empty = never committed to any branch
```

**`demo_tools/demo_secrets.bat` is gitignored, untracked, and has never been committed to
any branch.** Only `demo_secrets.example.bat` (a template with placeholder values, no real
secrets) is tracked. **There is nothing in git history to purge.** A prior session's
initial claim that this file was committed and needed a `git filter-repo`/BFG history rewrite
was **incorrect** — re-verified against the actual repository state above, and corrected
here rather than repeated.

**No destructive action (history rewrite, force-push) is needed or was taken.**

## What this means operationally

The file itself being clean in git does not guarantee the *secret values* it contains
(`DMRV_HMAC_SECRET`, `DMRV_ADMIN_SECRET`, or similar) were never exposed some other way —
screen-share during a demo, pasted into a chat, a screenshot, a colleague's shell history.
Git hygiene and value hygiene are two different questions.

**Action for whoever owns these values:** if there is any doubt the values in your local
`demo_tools/demo_secrets.bat` were ever shown or shared outside your own machine, rotate them
now — generate new values and update wherever they're consumed (local `.env`, deployed
environment variables, CI secrets). This is a value-rotation, not a git operation, and it is
the only residual action from this review. Do not do this by editing the tracked
`demo_secrets.example.bat` (it holds placeholders, not real values, and should stay that way).

## If a real leak is ever found in git history

The steps below are **prepared, not executed** — they rewrite history and require a human
to run them deliberately (force-push, coordinate with anyone else who has a clone, GitHub
secret-scanning follow-up). Use only if a *future* `git log --all -- <path>` actually shows
the secret file was committed:

```bash
# 1. Rotate the leaked secret VALUE first (assume it's already compromised).
#    Generate a new value and deploy it everywhere the old one was used
#    BEFORE touching git history — purging history doesn't undo a value
#    that's already been read by whoever had access to the commit.

# 2. Stop tracking the file going forward (if not already gitignored).
git rm --cached path/to/secret_file
echo "path/to/secret_file" >> .gitignore
git commit -m "chore: stop tracking secret file, rotate value"

# 3. Purge it from history (choose one; git filter-repo is the modern, faster tool).
pip install git-filter-repo
git filter-repo --path path/to/secret_file --invert-paths
# OR, if git-filter-repo isn't available:
# java -jar bfg.jar --delete-files secret_file

# 4. Force-push (coordinate with every other clone/fork first — this rewrites
#    every commit hash after the purge point).
git push --force --all
git push --force --tags

# 5. Have every other clone re-clone fresh (a stale clone will resurrect the
#    purged blob on its next push if not re-cloned).

# 6. If pushed to GitHub/GitLab, also contact their secret-scanning/support —
#    a purge does not remove already-cached forks or PR diffs on their side.
```

**None of step 3-6 above applies to the current repository state.** They are documented here
so a future real leak has a ready procedure, not because one exists today.
