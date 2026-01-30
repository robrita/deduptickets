# DedupTickets Frontend

React + TypeScript frontend for the Ticket Deduplication & Clustering Dashboard.

## Overview

A single-page application for support agents and team leads to:
- **Review clusters** of potential duplicate tickets
- **Merge duplicates** into a primary ticket
- **Revert merges** when mistakes are made
- **Monitor spikes** in ticket volume
- **Analyze trends** and top issue drivers
- **Audit all operations** for compliance

## Tech Stack

- **React 18** - Component framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first styling
- **React Router** - Client-side routing
- **React Query** (optional) - Server state management

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── audit/            # AuditLog component
│   │   ├── clusters/         # ClusterCard, ClusterList, MergeDialog
│   │   ├── merges/           # MergeHistoryItem, RevertConfirmDialog
│   │   ├── shared/           # ConfidenceBadge, TicketPreview
│   │   ├── spikes/           # SpikeAlertCard, SpikeDrilldown
│   │   └── trends/           # TopDrivers, TrendChart
│   ├── hooks/                # Custom React hooks
│   ├── pages/
│   │   ├── AuditPage.tsx     # Audit trail with search
│   │   ├── ClustersPage.tsx  # Cluster review dashboard
│   │   ├── Dashboard.tsx     # Summary widgets
│   │   ├── MergesPage.tsx    # Merge history with revert
│   │   ├── SpikesPage.tsx    # Active spike alerts
│   │   └── TrendsPage.tsx    # Trend analysis views
│   ├── services/             # API client services
│   ├── types/                # TypeScript interfaces
│   ├── App.tsx               # Root component with routing
│   └── main.tsx              # Application entry point
├── public/                   # Static assets
├── index.html                # HTML template
├── vite.config.ts            # Vite configuration
├── tailwind.config.js        # TailwindCSS configuration
└── package.json              # Project dependencies
```

## Quick Start

### Prerequisites

- Node.js 20+
- Backend API running at `http://localhost:8000`

### Setup

```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env.local
# Edit .env.local with your settings

# Start development server
npm run dev
```

### Development Commands

```bash
# Start development server (port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint

# Run linting with auto-fix
npm run lint -- --fix

# Run type checking
npm run typecheck

# Run unit tests
npm test

# Run E2E tests
npm run test:e2e
```

## Pages

### Dashboard (`/`)

Summary widgets showing:
- Pending cluster count with link to review
- Active spike alerts with severity
- Products tracked with trend link
- Quick audit trail access

### Clusters (`/clusters`)

- Filterable list of pending/merged/dismissed clusters
- Confidence score badges (High/Medium/Low)
- Click to view cluster detail with member tickets
- Merge dialog with primary selection and behavior choice
- Dismiss option for false positives

### Merges (`/merges`)

- History of all merge operations
- Status indicators (Completed/Reverted)
- Revert button with confirmation dialog
- Conflict warnings for post-merge changes

### Spikes (`/spikes`)

- Active spike alerts by region/month
- Severity indicators (Low/Medium/High)
- Deviation percentage display
- Drilldown to affected clusters
- Acknowledge and resolve actions

### Trends (`/trends`)

- Tab navigation: Top Drivers | Fastest Growing | Most Duplicated
- Ranked driver list with cluster counts
- Growth percentage indicators
- Simple bar chart visualization

### Audit (`/audit`)

- Searchable audit log
- Filter by entity type, action, user
- Date range selection
- Expandable change details
- Pagination for large result sets

## Components

### Shared Components

| Component | Purpose |
|-----------|---------|
| `ConfidenceBadge` | Colored badge for High/Medium/Low confidence |
| `TicketPreview` | Compact ticket display for lists |

### Cluster Components

| Component | Purpose |
|-----------|---------|
| `ClusterCard` | Summary card with signals and action buttons |
| `ClusterList` | Filterable, paginated cluster list |
| `ClusterDetail` | Full cluster view with member tickets |
| `MergeDialog` | Modal for executing merge with options |

### Merge Components

| Component | Purpose |
|-----------|---------|
| `MergeHistoryItem` | Single merge operation display |
| `RevertConfirmDialog` | Confirmation modal with conflict warnings |

### Spike Components

| Component | Purpose |
|-----------|---------|
| `SpikeAlertCard` | Alert card with severity and deviation |
| `SpikeDrilldown` | Detail modal with linked clusters |

### Trend Components

| Component | Purpose |
|-----------|---------|
| `TopDrivers` | Ranked list of issue drivers |
| `TrendChart` | Simple bar visualization |

### Audit Components

| Component | Purpose |
|-----------|---------|
| `AuditLog` | Filterable log with pagination |

## Services

API client services in `src/services/`:

```typescript
// Example: clusterService.ts
export async function listClusters(filters, page, pageSize) {
  const response = await api.get('/clusters', { params: { ...filters, page, page_size: pageSize } });
  return response.data;
}

export async function mergeCluster(clusterId, primaryId, behavior) {
  const response = await api.post('/merges', { cluster_id: clusterId, primary_ticket_id: primaryId, merge_behavior: behavior });
  return response.data;
}
```

## Types

TypeScript interfaces in `src/types/index.ts`:

```typescript
export interface Cluster {
  id: string;
  status: ClusterStatus;
  matching_fields: string[];
  ticket_count: number;
  confidence_score: number;
  summary: string;
  ticket_ids: string[];
  created_at: string;
  updated_at: string;
}

export type ClusterStatus = 'pending' | 'merged' | 'dismissed';
export type MergeBehavior = 'KeepLatest' | 'CombineNotes' | 'RetainAll';
```

## Configuration

Environment variables (`.env.local`):

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000/api/v1` |
| `VITE_API_KEY` | API authentication key | (required) |

## Styling

TailwindCSS is used for styling. Key patterns:

```tsx
// Status colors
const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  merged: 'bg-green-100 text-green-800',
  dismissed: 'bg-gray-100 text-gray-800',
};

// Severity colors
const severityColors = {
  LOW: 'bg-yellow-100 text-yellow-800',
  MEDIUM: 'bg-orange-100 text-orange-800',
  HIGH: 'bg-red-100 text-red-800',
};

// Confidence colors
const confidenceColors = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-gray-100 text-gray-800',
};
```

## Testing

### Unit Tests

Component tests with React Testing Library:

```typescript
test('renders cluster card with correct data', () => {
  render(<ClusterCard cluster={mockCluster} />);
  expect(screen.getByText('3 tickets')).toBeInTheDocument();
  expect(screen.getByText('High')).toBeInTheDocument();
});
```

### E2E Tests

End-to-end tests with Playwright (or Cypress):

```typescript
test('merge workflow', async ({ page }) => {
  await page.goto('/clusters');
  await page.click('[data-testid="cluster-card-0"]');
  await page.click('button:has-text("Merge")');
  await page.selectOption('[data-testid="primary-select"]', { index: 0 });
  await page.click('button:has-text("Confirm")');
  await expect(page.locator('.toast-success')).toBeVisible();
});
```

## Contributing

1. Create feature branch
2. Add/update components with TypeScript types
3. Add unit tests for new components
4. Run linting: `npm run lint -- --fix`
5. Ensure build passes: `npm run build`
6. Submit PR

## License

Proprietary - Internal use only
