---
description: "Zero-downtime database migrations: expand and contract, backfills and dual writes, run on SQLite, including a failure of the naive rename."
---

# 03 · Database Migrations: Expand & Contract

Code deploys can be rolled back in seconds. Schema changes usually cannot. The database is shared by every running version, by migrations, by batch jobs and by humans with a SQL console, and once data is changed or destroyed, redeploying old code does not bring it back. Zero-downtime delivery therefore needs one rule above all: **each step of a change must work with both the code before it and the code after it.**

!!! note "What was run"
    Experiments ran on **SQLite 3.53.4** through Python's `sqlite3` module, on tiny in-memory tables, using `ALTER TABLE ... RENAME COLUMN`, `ADD COLUMN`, `DROP COLUMN` and a trigger. SQLite is not PostgreSQL or MySQL: locking behaviour, online-DDL support and transactional DDL differ a lot between engines, and I did **not** run any of those. What the experiment shows is the logical compatibility problem, which is engine-independent; claims about locks and downtime on real engines are general and untested here.

## The naive rename breaks the old version

You want `users.name` to become `users.full_name`. The one-statement way:

```text
ALTER TABLE users RENAME COLUMN name TO full_name
old app  (SELECT name ...)       -> ERROR: no such column: name
new app  (SELECT full_name ...)  -> ('Ada',)
```

The new code works and the old code, still running during a rolling deploy (Lesson 01) or a rollback, fails immediately. Every request served by an old instance errors until the deploy finishes, and a rollback of the code would fail the other way. The migration and the deploy are separate events and neither can be atomic with the other.

## The expand / migrate / contract sequence

Split the change into steps, each compatible with its neighbours:

1. **Expand**: add the new column, nullable, with no constraint the old code would violate.
   ```text
   ALTER TABLE users ADD COLUMN full_name TEXT
   old app -> ('Ada',)     new app (before backfill) -> (None,)
   ```
   Both versions run. The new column is empty, so the new code must tolerate NULL for now.
2. **Backfill**: copy existing values (`UPDATE users SET full_name = name WHERE full_name IS NULL`). After it, `[(1,'Ada','Ada'), (2,'Bob','Bob')]`. On a large table do this in **batches** so no single statement holds locks for long or bloats the transaction log.
3. **Dual write**: the application now writes *both* columns, or a database trigger keeps them in sync. This closes the gap that I measured next.
4. **Switch reads** to the new column once the backfill is verified complete.
5. **Contract**: stop writing the old column, wait until no running or rollback-target version needs it, then drop it.

### The gap that backfill alone leaves

After step 2, the **old app is still running and inserting rows**. I inserted `(3, 'Cy')` through the old code path (it only knows `name`):

```text
row written by OLD app after backfill, new column: (None,)
```

`full_name` is NULL for that row, so the new code, which reads `full_name`, sees a user with no name. A one-time backfill is never enough while old writers exist. The fix is dual-writing from the new code and, for old writers you cannot change quickly, a sync trigger:

```text
CREATE TRIGGER sync AFTER INSERT ON users WHEN NEW.full_name IS NULL
BEGIN UPDATE users SET full_name = NEW.name WHERE id = NEW.id; END
insert via old code after the trigger -> full_name = 'Di'
```

### A surprise when contracting

Dropping the old column while the trigger still referenced it failed:

```text
drop with trigger present: error in trigger sync after drop column: no such column: new.name
```

I had not expected this; SQLite validates trigger bodies when you change the schema. The order is therefore: **remove the trigger first, then drop the column.** After `DROP TRIGGER` and `DROP COLUMN`, the old code fails (`no such column: name`), which is the point of contract: only do it when no old code remains. Other engines enforce dependencies differently (dropping a column used by a view or index may be blocked, cascaded, or silently allowed); learn your engine's rules.

## Rules for migrations in a pipeline

- **Migrations are code**, versioned, reviewed, and applied by the pipeline in order, never by hand against production.
- **Forward-only, with a tested plan B.** "Down" migrations that drop data are fiction in production; a rollback often means *deploying a new forward fix*. Where possible, make each step reversible by construction (an added nullable column can simply be left in place).
- **Separate deploy of schema from deploy of code.** Run expand before the code that needs it; run contract after the code that needed the old shape is gone, usually a release or two later.
- **Test on production-sized data.** A migration that takes 40 ms on a test database may lock a hundred-million-row table for minutes. Estimate from row counts, and rehearse on a restored copy.
- **Idempotent and resumable**: a backfill interrupted halfway should be safe to run again (note the `WHERE full_name IS NULL`).
- **Check for long-running transactions and lock waits** before DDL on a busy table; a DDL statement queued behind a long transaction can block every later query behind it on some engines. Use a lock timeout and retry.

## Dangerous operations, and safer shapes

| Operation | Why it hurts | Safer shape |
|---|---|---|
| Rename column or table | Breaks the other version | Add new, dual-write, backfill, switch, drop old |
| Add `NOT NULL` column without a default | Fails on existing rows; may rewrite the table | Add nullable, backfill, then add the constraint (validated) |
| Change a column type | Rewrites data, breaks readers | New column with the new type, migrate, switch |
| Add an index on a large table | Can block writes | Use the engine's online/concurrent index creation where it exists |
| Drop a column | Irreversible data loss; breaks old code | Stop all use first, back up, then drop |
| Large `UPDATE` in one statement | Long lock, huge log | Batches with pauses |

## Data fixes are migrations too

A one-off script that corrects bad rows should go through the same review and run as a pipeline job with a record of what changed, ideally keeping a copy of the old values (or relying on a verified backup) until you are sure.

## How It Actually Works

A schema is metadata stored in the database's catalog. DDL statements modify it, and the engine takes locks on the table while doing so. Running application code holds *prepared statements and cached plans* that refer to column names or positions; when the catalog changes under them, they either fail (as above), re-plan, or keep working against the old definition depending on the engine. Because deployments take minutes and migrations take seconds to hours, there is always an interval in which two code versions share one schema, and the expand/contract discipline is simply the practice of making the schema a **superset** of what both versions need during that interval. Contract is then removing the superset's unneeded half once the interval is over.

## Common mistakes

- **One-step renames and type changes** during a rolling deploy.
- **Backfill without dual-write**, leaving rows inserted by old writers incomplete.
- **Dropping the old column before the last old reader is gone**, including the rollback target.
- **Testing migrations only on tiny data.**
- **Down-migrations that destroy data** and have never been run.
- **Hand-applied production changes** that the repository does not know about.
- **Running migrations inside the app's start-up** in a fleet, so ten instances race to apply them.

## Exercise

1. Reproduce the experiment in Python's `sqlite3`: do the naive rename, then expand/backfill/dual-write/contract. Add the statement that fails and record the engine's error text.
2. Write the step list (with the deploy between each) for changing `orders.status` from an integer to a string enum without downtime.
3. Make the backfill batched: update 1,000 rows at a time by primary-key range and resume safely after an interruption. Test by killing it midway.
4. Decide what your rollback plan is if step 4 (switch reads) of your own migration shows a bug after 20 minutes in production.
