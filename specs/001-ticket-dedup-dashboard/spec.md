# Feature Specification: Ticket Deduplication & Clustering Dashboard

**Feature Branch**: `001-ticket-dedup-dashboard`  
**Created**: 2026-01-27  
**Status**: Draft  
**Input**: User description: "Build a ticket deduplication + clustering dashboard for a support team"

## Clarifications

### Session 2026-01-27

- Q: What similarity threshold should trigger a text-based match? → A: Configurable per deployment using Cosmos DB hybrid search
- Q: Who should be able to configure spike detection fields and thresholds? → A: Pre-defined at deployment, no runtime config
- Q: What happens to tickets in a soft group after creation? → A: Deferred to v2; MVP focuses on merge only
- Q: When should clustering analysis run? → A: Real-time on each ticket ingestion (<30 seconds)
- Q: Which customer fields should be masked in cluster views? → A: No masking in MVP; add masking in v2 after compliance review
- Q: Should RBAC be enforced in MVP? → A: Deferred to v2; MVP uses API key authentication only
- Q: Should export functionality with role-based limits be in MVP? → A: Deferred to v2; no export functionality in MVP

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review and Merge Duplicate Tickets (Priority: P1)

As a Support Agent (L1/L2), I need to review system-suggested duplicate ticket clusters and merge them into a single primary ticket, so I can avoid replying multiple times to the same customer issue and reduce duplicated handling effort.

**Why this priority**: This is the core value proposition—reducing duplicate work is the primary pain point. Without merge capability, the dashboard provides no actionable value.

**Independent Test**: Can be fully tested by creating sample tickets, viewing suggested clusters, and performing merge operations. Delivers immediate value by consolidating duplicate tickets.

**Acceptance Scenarios**:

1. **Given** the system has identified a cluster of 3 related tickets with the same transaction ID, **When** I open the cluster view, **Then** I see all 3 tickets listed with a cluster summary explaining they share the same transaction ID.

2. **Given** I am viewing a cluster of duplicate tickets, **When** I select one ticket as primary and click merge, **Then** the other tickets are linked to the primary ticket, and I can choose to keep latest reply, combine notes, or retain all references.

3. **Given** I am viewing a suggested cluster, **When** I examine the cluster details, **Then** I see the confidence level (High/Medium/Low) and the specific matching signals (e.g., same error code, same bank, similar text).

4. **Given** a cluster is displayed, **When** I decide the grouping is incorrect, **Then** I can dismiss the suggestion or remove individual tickets from the cluster without merging.

---

### User Story 2 - Revert a Merge (Priority: P2)

As a Support Agent or Team Lead, I need to undo a merge operation and restore tickets to their original state, so that mistakes can be corrected without data loss.

**Why this priority**: Human control and reversibility are core guardrails. Without revert capability, agents will hesitate to use merge, reducing adoption.

**Independent Test**: Can be tested by performing a merge, then reverting it, and verifying all original tickets are restored with their data intact.

**Acceptance Scenarios**:

1. **Given** I previously merged 3 tickets into a primary ticket, **When** I initiate a revert on that merge, **Then** all 3 original tickets are restored to their pre-merge state with all notes, history, and references intact.

2. **Given** a merge was reverted, **When** I view the audit trail, **Then** I see who performed the original merge, when it happened, who reverted it, and when the revert occurred.

3. **Given** I attempt to revert a merge, **When** the primary ticket has been updated since the merge, **Then** the system warns me about potential conflicts and preserves all post-merge updates on the restored primary ticket.

---

### User Story 3 - Detect and Investigate Ticket Spikes (Priority: P3)

As a Team Lead or Queue Manager, I need to see when ticket volume spikes occur grouped by specific fields (category, channel, region, partner, error code), so I can identify emerging issues and rebalance queues appropriately.

**Why this priority**: Spike detection enables proactive incident response but requires the clustering foundation from P1 to be meaningful.

**Independent Test**: Can be tested by simulating a surge of tickets with common attributes and verifying the spike appears in the dashboard with drill-down capability.

**Acceptance Scenarios**:

1. **Given** ticket volume for "cash-in failures" increased 300% in the last hour compared to baseline, **When** I view the spike detection dashboard, **Then** I see an alert highlighting this anomaly with the affected field values.

2. **Given** a spike is detected for a specific partner (e.g., Bank X), **When** I click on the spike, **Then** I can drill down to see the affected clusters and individual tickets.

3. **Given** I am monitoring spikes, **When** multiple field combinations show elevated volume, **Then** I see them ranked by severity/increase percentage with the ability to filter by channel, region, partner, or error code.

---

### User Story 4 - View Top Drivers and Trends (Priority: P4)

As a Team Lead or Product Owner, I need to see the top recurring cluster themes and trending drivers over time, so I can identify repeat-contact hotspots and prioritize root cause fixes.

**Why this priority**: Trend analysis provides strategic insights but depends on historical cluster data accumulated from P1 operations.

**Independent Test**: Can be tested by accumulating cluster data over a simulated period and verifying trend views display accurate aggregations.

**Acceptance Scenarios**:

1. **Given** cluster data has been collected for the past week, **When** I view the "Top Drivers" dashboard, **Then** I see the top 10 cluster themes ranked by frequency.

2. **Given** I am viewing trend data, **When** I select "Fastest growing driver vs last week", **Then** I see drivers sorted by week-over-week growth percentage.

3. **Given** I am analyzing repeat contacts, **When** I view "Most duplicated driver", **Then** I see which root issues generate the highest number of duplicate tickets per incident.

---

### User Story 5 - Audit Trail for All Actions (Priority: P5)

As an Ops Manager or Compliance Officer, I need a complete audit trail of all merge actions, reverts, and cluster membership changes, so I can ensure accountability and investigate issues when needed.

**Why this priority**: Auditability is a guardrail requirement and supports all other stories but provides indirect value.

**Independent Test**: Can be tested by performing various actions and verifying each appears in the audit log with correct metadata.

**Acceptance Scenarios**:

1. **Given** any merge, revert, or cluster modification occurs, **When** I access the audit log, **Then** I see the action type, actor identity, timestamp, affected tickets, and reason (if provided).

2. **Given** I need to investigate a specific ticket's history, **When** I search the audit log by ticket ID, **Then** I see all actions that affected that ticket in chronological order.

---

### Edge Cases

- What happens when two agents attempt to merge the same cluster simultaneously?
  - The second merge attempt should fail gracefully with a message indicating the cluster was already merged, showing who performed the merge.

- What happens when a ticket in a pending cluster is updated by the customer before merge?
  - The cluster should refresh to reflect the update, and agents should see visual indication that ticket content changed since suggestion.

- How does the system handle very large clusters (50+ tickets)?
  - Pagination should be applied, with summary statistics shown first before loading individual ticket details.

- What happens if the source ticketing system is temporarily unavailable?
  - The dashboard should display cached data with a clear "stale data" indicator and timestamp of last successful sync.

- How does the system behave during a major incident with 10x normal ticket volume?
  - Clustering should prioritize recent tickets and degrade gracefully (batch processing vs real-time) to maintain dashboard responsiveness.

## Requirements *(mandatory)*

### Functional Requirements

**Clustering & Deduplication**

- **FR-001**: System MUST analyze each incoming ticket in real-time (<30 seconds from ingestion) and propose clusters of related/duplicate tickets. Clustering is triggered synchronously on ticket creation.
- **FR-002**: System MUST display a summary for each cluster explaining what tickets have in common.
- **FR-003**: System MUST show matching signals for each cluster (e.g., same transaction ID, same error code, same bank/merchant, same time window, similar text). Text similarity uses Cosmos DB hybrid search (vector + keyword) with admin-configurable similarity threshold (default 0.7).
- **FR-004**: System MUST assign a confidence indicator (High/Medium/Low) to each cluster based on matching strength.
- **FR-005**: System MUST NOT automatically merge or close tickets without human action.

**Merge Controls**

- **FR-006**: Users MUST be able to open a cluster and review all member tickets.
- **FR-007**: Users MUST be able to select a primary ticket and merge other tickets into it.
- **FR-008**: Users MUST be able to choose merge behavior: keep latest reply, combine notes, or retain all references.
- **FR-009**: *(Deferred to v2)* Users MUST be able to group tickets without merging (soft grouping). MVP focuses on merge and dismiss actions only.
- **FR-010**: Users MUST be able to dismiss cluster suggestions or remove individual tickets from a cluster.

**Revert Capability**

- **FR-011**: Users MUST be able to revert any merge operation and restore original tickets to their pre-merge state.
- **FR-012**: System MUST preserve all data from both pre-merge and post-merge states during revert.
- **FR-013**: System MUST warn users if reverting a merge where the primary ticket has been modified since merge.

**Spike Detection**

- **FR-014**: System MUST detect unusual increases in ticket volume grouped by pre-defined fields (category, channel, region, merchant, subcategory, severity). Field list and thresholds are configured at deployment via environment variables; no runtime UI for modification.
- **FR-015**: System MUST display spike alerts with severity and percentage increase vs baseline.
- **FR-016**: Users MUST be able to drill down from a spike to affected clusters to underlying tickets.

**Trend & Driver Views**

- **FR-017**: System MUST display top recurring cluster themes over configurable time periods.
- **FR-018**: System MUST display fastest growing drivers compared to previous period.
- **FR-019**: System MUST display drivers with highest duplication rate (duplicates per root issue).

**Explainability & Trust**

- **FR-020**: Every cluster MUST show why it was created with visible matching signals (no black box).
- **FR-021**: System MUST NOT take irreversible actions on tickets.

**Data Safety & Access Control**

- **FR-022**: *(Deferred to v2)* System MUST minimize visible PII in cluster views; sensitive fields masked by default. MVP displays all fields without masking pending compliance review.
- **FR-023**: *(Deferred to v2)* System MUST enforce role-based access control for viewing, merging, and reverting. MVP uses API key authentication only; RBAC integration with identity provider deferred.
- **FR-024**: *(Deferred to v2)* System MUST limit export of sensitive ticket fields based on user role. MVP has no export functionality.

**Auditability**

- **FR-025**: System MUST log all merge actions with actor, timestamp, affected tickets, and merge behavior chosen.
- **FR-026**: System MUST log all revert actions with actor, timestamp, affected tickets, and reason.
- **FR-027**: System MUST log cluster membership changes (additions, removals, dismissals).
- **FR-028**: Audit logs MUST be immutable and searchable by ticket ID, actor, or action type.

### Key Entities

- **Ticket**: Individual support ticket with ID, customer reference, issue details, status, timestamps, channel, category, and transaction metadata.

- **Cluster**: A proposed grouping of related tickets; contains member tickets, cluster summary, matching signals, confidence level, creation timestamp, and status (pending/merged/dismissed).

- **Merge Operation**: A completed merge action linking secondary tickets to a primary ticket; captures merge behavior, actor, timestamp, and original ticket states for revert.

- **Spike Alert**: A detected anomaly in ticket volume; contains affected field values, percentage increase, baseline comparison, severity, detection timestamp, and linked clusters.

- **Audit Entry**: A log record of any significant action; contains action type, actor identity, timestamp, affected entities, and metadata.

- **Driver**: An aggregated pattern representing a recurring issue theme; contains theme summary, frequency count, trend direction, and associated clusters.

## Assumptions

- The source ticketing system provides an API or data feed for ticket ingestion; specific integration method will be determined during planning.
- Clustering algorithms and matching logic will be refined during implementation; initial version uses field matching (transaction ID, error code, time window) and basic text similarity.
- "Same shift" for spike detection is assumed to mean within 2-4 hours; exact threshold to be configured per deployment.
- Role-based access control will integrate with existing identity provider; specific roles (Agent, Team Lead, Ops Manager) to be mapped during implementation.
- Historical ticket data retention follows organization policy; default assumption is 90 days for trend analysis.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Support agents reduce duplicate replies by at least 30% within 90 days of deployment (compared to pre-dashboard baseline).

- **SC-002**: Agents can review a suggested cluster and complete a merge decision in under 90 seconds for 90% of clusters.

- **SC-003**: Users accept/confirm system-suggested clusters as useful at a rate of 70% or higher (measured by merge/group vs dismiss ratio).

- **SC-004**: 100% of merge operations are reversible; revert functionality restores original tickets with zero data loss.

- **SC-005**: Ticket spikes become visible in the dashboard within the same operational shift (under 4 hours from surge onset) and are actionable via drill-down.

- **SC-006**: Dashboard remains responsive (page load under 3 seconds) during incident surges with 5x normal ticket volume.

- **SC-007**: All merge, revert, and cluster modification actions are captured in audit logs with complete metadata (actor, timestamp, affected entities).
