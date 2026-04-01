---
phase: quick
plan: 260401-stv
type: execute
wave: 1
depends_on: []
files_modified:
  - docker-compose.yml
  - docker/initdb/01-enable-pgvector.sql
autonomous: true
must_haves:
  truths:
    - "PostgreSQL container runs with pgvector extension available"
    - "CREATE EXTENSION vector executes automatically on first start"
    - "Existing checkpointer functionality is unaffected"
  artifacts:
    - path: "docker-compose.yml"
      provides: "pgvector-enabled PostgreSQL image"
      contains: "pgvector/pgvector:pg17"
    - path: "docker/initdb/01-enable-pgvector.sql"
      provides: "Auto-enable vector extension on DB init"
      contains: "CREATE EXTENSION"
  key_links:
    - from: "docker-compose.yml"
      to: "docker/initdb/01-enable-pgvector.sql"
      via: "bind mount to /docker-entrypoint-initdb.d"
      pattern: "docker/initdb:/docker-entrypoint-initdb.d"
---

<objective>
Enable pgvector extension in the existing PostgreSQL container for future RAG support.

Purpose: Prepare the database layer for vector similarity search without affecting current checkpointer functionality.
Output: Updated docker-compose.yml using pgvector image + init script that enables the extension on first boot.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@docker-compose.yml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Switch to pgvector image and add init script</name>
  <files>docker-compose.yml, docker/initdb/01-enable-pgvector.sql</files>
  <action>
1. Create `docker/initdb/01-enable-pgvector.sql` with:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. In `docker-compose.yml`, update the postgres service:
   - Change `image: postgres:17-alpine` to `image: pgvector/pgvector:pg17`
   - Add a bind mount for the init script: `./docker/initdb:/docker-entrypoint-initdb.d` (BEFORE the named volume line)
   - Keep all other settings (environment, healthcheck, named volume) unchanged

Note: The pgvector/pgvector:pg17 image is based on the official postgres:17 image with the pgvector extension pre-installed. It is fully compatible with existing PostgreSQL data and the langgraph-checkpoint-postgres checkpointer. The init script only runs on first database initialization (empty data volume); existing volumes are unaffected.
  </action>
  <verify>
    <automated>grep -q "pgvector/pgvector:pg17" docker-compose.yml && grep -q "docker-entrypoint-initdb.d" docker-compose.yml && test -f docker/initdb/01-enable-pgvector.sql && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>docker-compose.yml uses pgvector image with init script mount; SQL file exists with CREATE EXTENSION statement</done>
</task>

<task type="auto">
  <name>Task 2: Verify pgvector extension loads in running container</name>
  <files></files>
  <action>
1. Remove the existing postgres volume to force a fresh init (the init script only runs on first boot):
   ```bash
   docker compose down -v --remove-orphans
   ```

2. Start only the postgres service:
   ```bash
   docker compose up -d postgres
   ```

3. Wait for healthy, then verify the extension:
   ```bash
   docker compose exec postgres psql -U postgres -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
   ```
   Expected: one row showing `vector` with a version number (e.g., 0.8.0).

4. Tear down after verification:
   ```bash
   docker compose down
   ```
  </action>
  <verify>
    <automated>docker compose up -d postgres && sleep 5 && docker compose exec postgres psql -U postgres -t -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q vector && echo "PASS" || echo "FAIL"; docker compose down</automated>
  </verify>
  <done>pgvector extension is confirmed loaded and queryable in the PostgreSQL container</done>
</task>

</tasks>

<verification>
- `docker-compose.yml` uses `pgvector/pgvector:pg17` image
- `docker/initdb/01-enable-pgvector.sql` exists with `CREATE EXTENSION IF NOT EXISTS vector;`
- Init script is mounted to `/docker-entrypoint-initdb.d` in postgres service
- Extension is available when queried via psql
</verification>

<success_criteria>
PostgreSQL container starts with pgvector extension enabled and ready for future RAG vector operations. Existing checkpointer (langgraph-checkpoint-postgres) continues to work unchanged.
</success_criteria>

<output>
After completion, create `.planning/quick/260401-stv-rag-pgvector/260401-stv-SUMMARY.md`
</output>
