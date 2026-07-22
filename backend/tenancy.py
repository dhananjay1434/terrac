"""V8 Part 5 (D) — multi-tenancy query scoping.

A `PortalUser.org_id` of NULL (the state of every user before this Part, and
any global admin managing multiple orgs) means "unscoped": sees every row,
identical to pre-tenancy behavior — this Part is additive, never a silent
narrowing of what an existing user could already see. A user WITH an org_id
is confined to that org's rows PLUS ungrouped/legacy rows (org_id IS NULL) —
old data that predates tenancy is treated as shared, not as belonging to any
other org.

Kept as a separate module (no `server`/`routes` import) so these functions
stay pure query transforms: given a SQLAlchemy `Select` and a user, return a
(possibly) further-filtered `Select`. No DB/HTTP side effects, easily unit
tested with an in-memory SQLite session.
"""

from __future__ import annotations

from sqlalchemy import Select, select

from models import Batch, PortalUser, Project


def scope_by_org(stmt: Select, org_id_column, user: PortalUser) -> Select:
    """Restrict [stmt] to rows where [org_id_column] matches the user's org,
    or is NULL (ungrouped/legacy). No-op when the user is unscoped."""
    if user.org_id is None:
        return stmt
    return stmt.where((org_id_column == user.org_id) | (org_id_column.is_(None)))


def scope_batches_by_org(stmt: Select, user: PortalUser) -> Select:
    """Batch has no direct org_id column — it's scoped indirectly through its
    (bare-string, non-FK) `project_id` against the Project it names. A batch
    whose project_id doesn't resolve to any registered Project (offline-first
    device wrote a project the portal hasn't registered yet) is excluded once
    a user IS org-scoped — it can't be proven to belong to their org, so
    fail-closed rather than leak it across a tenant boundary."""
    if user.org_id is None:
        return stmt
    eligible_project_ids = select(Project.project_id).where(
        (Project.org_id == user.org_id) | (Project.org_id.is_(None))
    )
    return stmt.where(Batch.project_id.in_(eligible_project_ids))
