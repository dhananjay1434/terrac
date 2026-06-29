# 06 — Repo Hygiene and Config

## 🔴 Secrets Leaking
- `backend/.env` is committed and contains DB credentials
  (`DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dmrv`)
  plus leftover `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS="*"`.
- `.gitignore`'s "Environment files" section is **empty** (only ignores
  `*token.json*` / `*credentials.json*`) — so `.env` is **not** ignored.
- The `.gitignore` file itself is **corrupted** — it contains UTF-16 / NUL-byte
  garbage near the end (`b a c k e n d / u p l o a d s /`), so git treats it as
  binary and ignore rules there are unreliable.
- `all_user_inputs.txt` (547 KB) and `longest_msg.txt` are a full dump of the
  development chat/prompt history — internal information leak; should never be
  in a product repo.

## 🔴 Messy Repository
- 15+ throwaway scripts committed.
- 62 MB `build/` directory committed.
- 176 uploaded JPEGs committed.
- A SQLite DB `backend/dmrv.db` committed.

**Fix direction:** 
1. Purge secrets from history.
2. Rotate the DB password.
3. Rewrite `.gitignore` as clean UTF-8 with real env/db/build/uploads rules.
4. Delete prompt dumps and throwaway scripts.
5. Remove `build/` and JPEGs from source control.
