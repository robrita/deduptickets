# Data Model: Ticket Deduplication & Clustering Dashboard

**Feature**: 001-ticket-dedup-dashboard  
**Date**: 2026-01-27  
**Database**: Azure Cosmos DB for NoSQL

## Container Architecture

```
deduptickets-db (Database)
├── tickets              # PK: pk (region|year-month)
├── clusters             # PK: pk (region|year-month)
├── merges               # PK: pk (region|year-month)
├── audit                # PK: pk (year-month), TTL enabled
├── spikes               # PK: pk (year-month)
└── baselines            # PK: pk (field|value)
```

### Partition Key Strategy

**Hierarchical Partition Key (HPK) Pattern**: `{region}|{year-month}`

- **High cardinality**: Combines region (NCR, Visayas, Mindanao, etc.) with year-month
- **Query flexibility**: Supports queries filtered by region, by month, or both
- **Even distribution**: Prevents hot partitions during spikes
- **Overcomes 20GB limit**: HPK allows exceeding single logical partition limits

Example partition keys:
- `PH|2025-12` - Philippines, December 2025
- `NCR|2026-01` - National Capital Region, January 2026
- `VISAYAS|2026-01` - Visayas region, January 2026

---

## Container: tickets

Stores all ingested support tickets. Denormalized structure with embedded customer and transaction data.

### Document Schema

```json
{
  "id": "a7c8b4f9-1d3a-4d66-9b1a-5d3d2f3a1c01",
  "pk": "NCR|2025-12",
  "ticketNumber": "GCASH-202512000123",
  "createdAt": "2025-12-03T02:11:45.000Z",
  "updatedAt": "2025-12-03T03:05:20.000Z",
  "closedAt": null,
  "status": "InProgress",
  "priority": "High",
  "severity": "S2",
  "channel": "InApp",
  
  "customerId": "CUST-0098123",
  "name": "Juan Dela Cruz",
  "mobileNumber": "+639171234567",
  "email": "juan.delacruz@example.com",
  "accountType": "Verified",
  "region": "NCR",
  "city": "Makati",
  
  "category": "Transfers",
  "subcategory": "BankTransferFailed",
  "summary": "Instapay transfer failed but amount was deducted",
  "description": "I tried sending to BPI via Instapay. It failed but my balance went down.",
  
  "transactionId": "TXN-88123-XYZ",
  "amount": 2500.0,
  "currency": "PHP",
  "merchant": "BPI",
  "occurredAt": "2025-12-03T02:09:11.000Z",
  
  "mergedIntoId": null,
  "clusterId": null,
  "_ts": 1733192720
}
```

### Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique document identifier |
| pk | string | Yes | Partition key: `{region}\|{year-month}` |
| ticketNumber | string | Yes | External ticket ID from source system |
| createdAt | string (ISO 8601) | Yes | When ticket was created |
| updatedAt | string (ISO 8601) | Yes | Last modification timestamp |
| closedAt | string (ISO 8601) | No | When ticket was closed |
| status | string | Yes | Open, InProgress, Resolved, Closed, Merged |
| priority | string | Yes | Low, Medium, High, Urgent |
| severity | string | No | S1, S2, S3, S4 |
| channel | string | Yes | InApp, Chat, Email, Social, Phone |
| customerId | string | Yes | Customer identifier |
| name | string | Yes | Customer display name (masked in API) |
| mobileNumber | string | No | Phone number (masked in API) |
| email | string | No | Email address (masked in API) |
| accountType | string | No | Verified, Basic, etc. |
| region | string | Yes | Geographic region |
| city | string | No | City name |
| category | string | Yes | Issue category |
| subcategory | string | No | Issue subcategory |
| summary | string | Yes | Brief issue description |
| description | string | No | Detailed issue description |
| transactionId | string | No | Related transaction ID |
| amount | number | No | Transaction amount |
| currency | string | No | Currency code (PHP, USD, etc.) |
| merchant | string | No | Bank/merchant name |
| occurredAt | string (ISO 8601) | No | When the issue occurred |
| mergedIntoId | string (UUID) | No | If merged, points to primary ticket |
| clusterId | string (UUID) | No | Associated cluster ID |

### Indexing Policy

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    { "path": "/status/*" },
    { "path": "/category/*" },
    { "path": "/channel/*" },
    { "path": "/transactionId/*" },
    { "path": "/merchant/*" },
    { "path": "/createdAt/*" },
    { "path": "/region/*" }
  ],
  "excludedPaths": [
    { "path": "/description/*" },
    { "path": "/name/*" },
    { "path": "/mobileNumber/*" },
    { "path": "/email/*" }
  ],
  "compositeIndexes": [
    [
      { "path": "/status", "order": "ascending" },
      { "path": "/createdAt", "order": "descending" }
    ],
    [
      { "path": "/category", "order": "ascending" },
      { "path": "/createdAt", "order": "descending" }
    ],
    [
      { "path": "/merchant", "order": "ascending" },
      { "path": "/createdAt", "order": "descending" }
    ]
  ]
}
```

---

## Container: clusters

Stores proposed ticket groupings with embedded member references.

### Document Schema

```json
{
  "id": "c3d4e5f6-2a3b-4c5d-6e7f-8a9b0c1d2e3f",
  "pk": "NCR|2025-12",
  "status": "Pending",
  "confidence": "High",
  "summary": "Multiple tickets for BPI Instapay transfer failures",
  "ticketCount": 3,
  "createdAt": "2025-12-03T03:00:00.000Z",
  "updatedAt": "2025-12-03T03:00:00.000Z",
  "expiresAt": "2025-12-10T03:00:00.000Z",
  "createdBy": "system",
  
  "matchingSignals": {
    "exactMatches": [
      { "field": "transactionId", "value": "TXN-88123-XYZ" }
    ],
    "timeWindow": {
      "start": "2025-12-03T02:00:00.000Z",
      "end": "2025-12-03T03:00:00.000Z"
    },
    "textSimilarity": {
      "score": 0.92,
      "commonTerms": ["instapay", "failed", "BPI", "deducted"]
    },
    "fieldMatches": [
      { "field": "merchant", "value": "BPI" },
      { "field": "category", "value": "Transfers" }
    ]
  },
  
  "members": [
    {
      "ticketId": "a7c8b4f9-1d3a-4d66-9b1a-5d3d2f3a1c01",
      "ticketNumber": "GCASH-202512000123",
      "isPrimary": false,
      "addedAt": "2025-12-03T03:00:00.000Z"
    },
    {
      "ticketId": "b8d9e0f1-2c4d-5e6f-7a8b-9c0d1e2f3a4b",
      "ticketNumber": "GCASH-202512000124",
      "isPrimary": false,
      "addedAt": "2025-12-03T03:00:00.000Z"
    },
    {
      "ticketId": "c9e0f1a2-3d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "ticketNumber": "GCASH-202512000125",
      "isPrimary": true,
      "addedAt": "2025-12-03T03:00:00.000Z"
    }
  ],
  
  "primaryTicketId": "c9e0f1a2-3d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "_ts": 1733194800
}
```

### Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Cluster identifier |
| pk | string | Yes | Partition key: `{region}\|{year-month}` |
| status | string | Yes | Pending, Merged, Dismissed, Expired |
| confidence | string | Yes | High, Medium, Low |
| summary | string | Yes | Human-readable cluster summary |
| ticketCount | number | Yes | Number of tickets in cluster |
| createdAt | string (ISO 8601) | Yes | When cluster was proposed |
| updatedAt | string (ISO 8601) | Yes | Last modification |
| expiresAt | string (ISO 8601) | No | Auto-expire if not actioned |
| createdBy | string | Yes | "system" or user ID |
| matchingSignals | object | Yes | Why tickets were grouped |
| members | array | Yes | Embedded ticket references |
| primaryTicketId | string (UUID) | No | Selected primary after merge |

### Indexing Policy

```json
{
  "indexingMode": "consistent",
  "includedPaths": [
    { "path": "/status/*" },
    { "path": "/confidence/*" },
    { "path": "/createdAt/*" },
    { "path": "/primaryTicketId/*" }
  ],
  "excludedPaths": [
    { "path": "/matchingSignals/*" },
    { "path": "/members/*" }
  ],
  "compositeIndexes": [
    [
      { "path": "/status", "order": "ascending" },
      { "path": "/createdAt", "order": "descending" }
    ]
  ]
}
```

---

## Container: merges

Stores completed merge operations with full ticket snapshots for revert capability.

### Document Schema

```json
{
  "id": "d0f1a2b3-4c5d-6e7f-8a9b-0c1d2e3f4a5b",
  "pk": "NCR|2025-12",
  "clusterId": "c3d4e5f6-2a3b-4c5d-6e7f-8a9b0c1d2e3f",
  "primaryTicketId": "c9e0f1a2-3d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "secondaryTicketIds": [
    "a7c8b4f9-1d3a-4d66-9b1a-5d3d2f3a1c01",
    "b8d9e0f1-2c4d-5e6f-7a8b-9c0d1e2f3a4b"
  ],
  "mergeBehavior": "CombineNotes",
  "status": "Completed",
  "performedBy": "agent-001",
  "performedAt": "2025-12-03T04:15:00.000Z",
  "revertedAt": null,
  "revertedBy": null,
  "revertReason": null,
  
  "originalStates": [
    {
      "ticketId": "a7c8b4f9-1d3a-4d66-9b1a-5d3d2f3a1c01",
      "snapshot": {
        "ticketNumber": "GCASH-202512000123",
        "status": "Open",
        "summary": "Instapay transfer failed but amount was deducted",
        "description": "I tried sending to BPI via Instapay...",
        "updatedAt": "2025-12-03T03:05:20.000Z"
      }
    },
    {
      "ticketId": "b8d9e0f1-2c4d-5e6f-7a8b-9c0d1e2f3a4b",
      "snapshot": {
        "ticketNumber": "GCASH-202512000124",
        "status": "Open",
        "summary": "BPI transfer failed",
        "description": "My transfer to BPI did not go through...",
        "updatedAt": "2025-12-03T02:50:10.000Z"
      }
    }
  ],
  
  "_ts": 1733198100
}
```

### Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Merge operation identifier |
| pk | string | Yes | Partition key: `{region}\|{year-month}` |
| clusterId | string (UUID) | Yes | Source cluster |
| primaryTicketId | string (UUID) | Yes | Merge target ticket |
| secondaryTicketIds | array | Yes | Tickets merged into primary |
| mergeBehavior | string | Yes | KeepLatest, CombineNotes, RetainAll |
| status | string | Yes | Completed, Reverted |
| performedBy | string | Yes | Actor identity |
| performedAt | string (ISO 8601) | Yes | Merge timestamp |
| revertedAt | string (ISO 8601) | No | If reverted, when |
| revertedBy | string | No | Who reverted |
| revertReason | string | No | Optional reason |
| originalStates | array | Yes | Full ticket snapshots for revert |

---

## Container: audit

Immutable log of all significant actions. TTL-enabled for automatic cleanup.

### Document Schema

```json
{
  "id": "e1a2b3c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "pk": "2025-12",
  "actionType": "Merge",
  "actorId": "agent-001",
  "actorType": "User",
  "resourceType": "Cluster",
  "resourceId": "c3d4e5f6-2a3b-4c5d-6e7f-8a9b0c1d2e3f",
  "relatedIds": [
    "a7c8b4f9-1d3a-4d66-9b1a-5d3d2f3a1c01",
    "b8d9e0f1-2c4d-5e6f-7a8b-9c0d1e2f3a4b"
  ],
  "metadata": {
    "mergeBehavior": "CombineNotes",
    "ticketCount": 3
  },
  "outcome": "Success",
  "errorMessage": null,
  "ipAddress": "10.0.1.50",
  "userAgent": "Mozilla/5.0...",
  "createdAt": "2025-12-03T04:15:00.000Z",
  "ttl": 7776000,
  "_ts": 1733198100
}
```

### TTL Configuration

- **Default TTL**: 90 days (7,776,000 seconds)
- **Purpose**: Automatic cleanup of old audit logs
- **Override**: Set `ttl` to -1 to retain indefinitely

### Indexing Policy

```json
{
  "indexingMode": "consistent",
  "includedPaths": [
    { "path": "/actionType/*" },
    { "path": "/actorId/*" },
    { "path": "/resourceType/*" },
    { "path": "/resourceId/*" },
    { "path": "/createdAt/*" }
  ],
  "excludedPaths": [
    { "path": "/metadata/*" },
    { "path": "/userAgent/*" }
  ],
  "compositeIndexes": [
    [
      { "path": "/resourceType", "order": "ascending" },
      { "path": "/resourceId", "order": "ascending" },
      { "path": "/createdAt", "order": "descending" }
    ]
  ]
}
```

---

## Container: spikes

Stores detected volume anomalies.

### Document Schema

```json
{
  "id": "f2b3c4d5-6e7f-8a9b-0c1d-2e3f4a5b6c7d",
  "pk": "2025-12",
  "status": "Active",
  "severity": "High",
  "fieldName": "merchant",
  "fieldValue": "BPI",
  "currentCount": 150,
  "baselineCount": 25.5,
  "percentageIncrease": 488.2,
  "timeWindowStart": "2025-12-03T02:00:00.000Z",
  "timeWindowEnd": "2025-12-03T03:00:00.000Z",
  "affectedClusterIds": [
    "c3d4e5f6-2a3b-4c5d-6e7f-8a9b0c1d2e3f"
  ],
  "detectedAt": "2025-12-03T03:05:00.000Z",
  "acknowledgedBy": null,
  "acknowledgedAt": null,
  "resolvedAt": null,
  "_ts": 1733195100
}
```

---

## Container: baselines

Stores historical volume baselines for spike detection.

### Document Schema

```json
{
  "id": "g3c4d5e6-7f8a-9b0c-1d2e-3f4a5b6c7d8e",
  "pk": "merchant|BPI",
  "fieldName": "merchant",
  "fieldValue": "BPI",
  "hourOfDay": 2,
  "dayOfWeek": 2,
  "avgCount": 25.5,
  "stddevCount": 8.3,
  "sampleCount": 28,
  "computedAt": "2025-12-03T00:00:00.000Z",
  "_ts": 1733184000
}
```

### Partition Key Strategy

- **PK**: `{fieldName}|{fieldValue}` enables efficient baseline lookups
- Example: `merchant|BPI`, `category|Transfers`, `channel|InApp`

---

## Query Patterns

### High-Frequency Queries (RU-Optimized)

| Query | Partition Key Used | Expected RU |
|-------|-------------------|-------------|
| Get ticket by ID | Yes (point read) | ~1 RU |
| List pending clusters by region/month | Yes | ~5-10 RU |
| Get merge operation by ID | Yes (point read) | ~1 RU |
| Search audit by resource ID | Partial (cross-partition) | ~20-50 RU |

### Cross-Partition Queries (Use Sparingly)

| Query | When to Use | Mitigation |
|-------|-------------|------------|
| Search tickets by transactionId | Deduplication check | Cache results; limit to 30-day window |
| List all active spikes | Dashboard load | Aggregate in memory; refresh interval |
| Trend aggregation | Analytics | Pre-compute in background worker |

---

## Validation Rules

### Ticket
- ticketNumber: Required, max 50 chars
- summary: Required, max 500 chars
- status: Must be valid enum (Open, InProgress, Resolved, Closed, Merged)
- pk: Must follow `{region}\|{YYYY-MM}` format
- createdAt: Must be valid ISO 8601

### Cluster
- status: Pending → Merged | Dismissed | Expired only
- confidence: High | Medium | Low only
- summary: Required, max 1000 chars
- ticketCount: Must match members array length
- members: Max 100 tickets per cluster

### MergeOperation
- mergeBehavior: KeepLatest | CombineNotes | RetainAll only
- originalStates: Must contain all secondary ticket snapshots
- Cannot revert if status already = Reverted

### AuditEntry
- Immutable after creation
- createdAt: Auto-set on insert
- ttl: Default 90 days, -1 for indefinite

---

## Container Setup Script

```python
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey

async def setup_containers(client: CosmosClient, database_name: str):
    database = await client.create_database_if_not_exists(database_name)
    
    # tickets container with HPK
    await database.create_container_if_not_exists(
        id="tickets",
        partition_key=PartitionKey(path="/pk"),
        indexing_policy={...},  # See indexing policy above
        default_ttl=None  # No TTL for tickets
    )
    
    # clusters container
    await database.create_container_if_not_exists(
        id="clusters",
        partition_key=PartitionKey(path="/pk"),
        indexing_policy={...}
    )
    
    # merges container
    await database.create_container_if_not_exists(
        id="merges",
        partition_key=PartitionKey(path="/pk")
    )
    
    # audit container with TTL
    await database.create_container_if_not_exists(
        id="audit",
        partition_key=PartitionKey(path="/pk"),
        default_ttl=7776000  # 90 days
    )
    
    # spikes container
    await database.create_container_if_not_exists(
        id="spikes",
        partition_key=PartitionKey(path="/pk")
    )
    
    # baselines container
    await database.create_container_if_not_exists(
        id="baselines",
        partition_key=PartitionKey(path="/pk")
    )
```

---

## SDK Best Practices

1. **Singleton Client**: Reuse `CosmosClient` instance across all requests
2. **Async Operations**: Use `azure-cosmos` async SDK for all I/O
3. **Retry Logic**: SDK has built-in retry for 429s; configure preferred regions
4. **Diagnostics Logging**: Capture diagnostic strings when latency > 100ms or on errors
5. **Connection Mode**: Use Gateway mode for serverless; Direct mode for provisioned
6. **Bulk Operations**: Use bulk executor for batch ingestion (>100 docs)
