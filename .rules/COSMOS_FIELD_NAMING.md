# Cosmos DB Field Naming Conventions

## Rule: All field names must be camelCase

This project uses **camelCase** for all document fields stored in Cosmos DB. Pydantic models serialize with camelCase aliases (e.g. Python `ticket_number` → Cosmos DB `ticketNumber`).

This means indexing policies, excluded paths, and composite indexes in `cosmos/setup.py` **must** use the exact camelCase field names that appear in documents.

## Complete Field Reference

All multi-word fields across every model, organized by container. Single-word fields (`id`, `pk`, `status`, `category`, etc.) are omitted — they don't transform.

### Ticket fields (`tickets` container)

| Wrong (snake_case)      | Correct (camelCase)     | Affected Area                   |
|------------------------|-------------------------|---------------------------------|
| `/ticket_number`       | `/ticketNumber`         | Unique key policy               |
| `/created_at`          | `/createdAt`            | Composite indexes, queries      |
| `/updated_at`          | `/updatedAt`            | Composite indexes, queries      |
| `/closed_at`           | `/closedAt`             | Queries                         |
| `/customer_id`         | `/customerId`           | Queries                         |
| `/mobile_number`       | `/mobileNumber`         | Excluded paths                  |
| `/account_type`        | `/accountType`          | Queries                         |
| `/transaction_id`      | `/transactionId`        | Queries, indexes                |
| `/occurred_at`         | `/occurredAt`           | Queries                         |
| `/merged_into_id`      | `/mergedIntoId`         | Queries                         |
| `/cluster_id`          | `/clusterId`            | Queries                         |
| `/content_vector`      | `/contentVector`        | Vector indexes, excluded paths  |
| `/dedup_text`          | `/dedupText`            | Excluded paths                  |
| `/raw_metadata`        | `/rawMetadata`          | Excluded paths                  |

### Cluster fields (`clusters` container)

| Wrong (snake_case)              | Correct (camelCase)           | Affected Area                   |
|--------------------------------|-------------------------------|---------------------------------|
| `/created_at`                  | `/createdAt`                  | Composite indexes, queries      |
| `/updated_at`                  | `/updatedAt`                  | Queries                         |
| `/expires_at`                  | `/expiresAt`                  | Queries                         |
| `/created_by`                  | `/createdBy`                  | Queries                         |
| `/customer_id`                 | `/customerId`                 | Queries                         |
| `/ticket_count`                | `/ticketCount`                | Queries                         |
| `/open_count`                  | `/openCount`                  | Queries                         |
| `/confidence_score`            | `/confidenceScore`            | Queries                         |
| `/primary_ticket_id`           | `/primaryTicketId`            | Queries                         |
| `/representative_ticket_id`    | `/representativeTicketId`     | Queries                         |
| `/centroid_vector`             | `/centroidVector`             | Vector indexes, excluded paths  |
| `/matching_signals`            | `/matchingSignals`            | Excluded paths                  |
| `/dismissed_by`                | `/dismissedBy`                | Queries                         |
| `/dismissal_reason`            | `/dismissalReason`            | Queries                         |

### Cluster sub-model fields (nested in `members`, `matchingSignals`)

| Wrong (snake_case)      | Correct (camelCase)     | Affected Area                   |
|------------------------|-------------------------|---------------------------------|
| `/ticket_id`           | `/ticketId`             | Queries (JOIN on members)       |
| `/ticket_number`       | `/ticketNumber`         | Queries                         |
| `/is_primary`          | `/isPrimary`            | Queries                         |
| `/added_at`            | `/addedAt`              | Queries                         |
| `/exact_matches`       | `/exactMatches`         | Excluded paths (nested)         |
| `/time_window`         | `/timeWindow`           | Excluded paths (nested)         |
| `/text_similarity`     | `/textSimilarity`       | Excluded paths (nested)         |
| `/field_matches`       | `/fieldMatches`         | Excluded paths (nested)         |
| `/common_terms`        | `/commonTerms`          | Excluded paths (nested)         |

### MergeOperation fields (`merges` container)

| Wrong (snake_case)          | Correct (camelCase)       | Affected Area                   |
|----------------------------|---------------------------|---------------------------------|
| `/cluster_id`              | `/clusterId`              | Queries                         |
| `/primary_ticket_id`       | `/primaryTicketId`        | Queries                         |
| `/secondary_ticket_ids`    | `/secondaryTicketIds`     | Queries                         |
| `/merge_behavior`          | `/mergeBehavior`          | Queries                         |
| `/performed_by`            | `/performedBy`            | Queries                         |
| `/performed_at`            | `/performedAt`            | Queries, composite indexes      |
| `/revert_deadline`         | `/revertDeadline`         | Queries                         |
| `/reverted_at`             | `/revertedAt`             | Queries                         |
| `/reverted_by`             | `/revertedBy`             | Queries                         |
| `/revert_reason`           | `/revertReason`           | Queries                         |
| `/original_states`         | `/originalStates`         | Excluded paths                  |

### MergeOperation sub-model fields (nested in `originalStates`)

| Wrong (snake_case)      | Correct (camelCase)     | Affected Area                   |
|------------------------|-------------------------|---------------------------------|
| `/ticket_id`           | `/ticketId`             | Queries                         |

## Why This Matters

- **Misnamed excluded paths are silently ignored.** Cosmos DB won't error — it just indexes the field anyway, wasting RU on writes.
- **Misnamed composite indexes are non-functional.** Queries that should use a composite index will fall back to expensive cross-partition scans or individual field indexes.
- **Misnamed unique key paths fail silently.** The constraint applies to a non-existent field, so duplicates won't be caught.

## How to Verify

1. Check the Pydantic model **aliases** (camelCase) in `backend/src/models/` — these are the source of truth for Cosmos DB field names.
2. Cross-reference every path in `cosmos/setup.py` (`CONTAINERS` dict) against the model aliases.
3. SQL queries in `backend/src/repositories/` use `c.fieldName` — these must match the camelCase aliases.

## Reference

- Models: `backend/src/models/ticket.py`, `cluster.py` (incl. `ClusterMember`, `MatchingSignals`, `TextSimilarity`), `merge_operation.py` (incl. `TicketSnapshot`)
- Container setup: `backend/src/cosmos/setup.py`
- Repositories: `backend/src/repositories/ticket.py`, `cluster.py`, `merge.py`
- Generator: `backend/scripts/generate_sample_tickets.py` (outputs camelCase directly)
- Legacy migration: `backend/scripts/migrate_sample_tickets_snake_to_camel.py` (deprecated — kept for one-off external data)
