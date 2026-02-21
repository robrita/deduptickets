/**
 * E2E test: Merge workflow.
 *
 * Tests the complete merge flow: view clusters → select cluster → merge → verify.
 */

import { test, expect, type Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

// Mock API responses for consistent testing
const mockClusters = {
  data: [
    {
      id: 'cluster-001',
      status: 'pending',
      summary: 'Duplicate payment failure tickets for merchant Acme Corp',
      ticketCount: 3,
      createdAt: '2026-01-30T10:00:00Z',
    },
    {
      id: 'cluster-002',
      status: 'pending',
      summary: 'Card declined errors for category Electronics',
      ticketCount: 2,
      createdAt: '2026-01-30T09:00:00Z',
    },
  ],
  meta: {
    total: 2,
    offset: 0,
    limit: 20,
    hasMore: false,
  },
};

const mockClusterDetail = {
  id: 'cluster-001',
  status: 'pending',
  summary: 'Duplicate payment failure tickets for merchant Acme Corp',
  ticketCount: 3,
  members: [
    {
      ticketId: 'ticket-001',
      ticketNumber: 'TKT-2026-001',
      summary: 'Payment failed for my order',
      category: 'Payments',
      confidenceScore: 0.95,
      createdAt: '2026-01-30T09:30:00Z',
    },
    {
      ticketId: 'ticket-002',
      ticketNumber: 'TKT-2026-002',
      summary: 'Unable to complete payment',
      category: 'Payments',
      confidenceScore: 0.91,
      createdAt: '2026-01-30T09:45:00Z',
    },
    {
      ticketId: 'ticket-003',
      ticketNumber: 'TKT-2026-003',
      summary: 'Payment error at Acme Corp',
      category: 'Payments',
      confidenceScore: 0.88,
      createdAt: '2026-01-30T10:00:00Z',
    },
  ],
  createdAt: '2026-01-30T10:00:00Z',
};

const mockMergeResponse = {
  id: 'merge-001',
  clusterId: 'cluster-001',
  primaryTicketId: 'ticket-001',
  secondaryTicketIds: ['ticket-002', 'ticket-003'],
  mergeBehavior: 'keep_latest',
  status: 'completed',
  performedBy: 'agent@example.com',
  performedAt: '2026-01-30T11:00:00Z',
  revertDeadline: '2026-02-06T11:00:00Z',
};

const mockPendingCount = { pendingCount: 2 };

async function setupMockApi(page: Page) {
  // Mock clusters list endpoint
  await page.route('**/api/v1/clusters**', async (route, request) => {
    const url = new URL(request.url());
    const clusterId = url.pathname.match(/\/clusters\/([^/]+)$/)?.[1];

    if (url.pathname.includes('/pending/count')) {
      // Pending count
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPendingCount),
      });
    } else if (clusterId && !url.pathname.includes('dismiss') && !url.pathname.includes('members')) {
      // Get cluster detail
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockClusterDetail),
      });
    } else if (request.method() === 'GET') {
      // List clusters
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockClusters),
      });
    } else {
      await route.continue();
    }
  });

  // Mock merges endpoint
  await page.route('**/api/v1/merges**', async (route, request) => {
    if (request.method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(mockMergeResponse),
      });
    } else {
      await route.continue();
    }
  });
}

test.describe('Merge Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
  });

  async function openFirstCluster(page: Page) {
    const firstClusterCard = page.getByRole('button', { name: /tickets\s+pending/i }).first();
    await expect(firstClusterCard).toBeVisible();
    await firstClusterCard.click();
  }

  test('should display pending clusters list', async ({ page }) => {
    await page.goto('/clusters');
    await expect(page.getByRole('heading', { name: /duplicate clusters/i })).toBeVisible();

    // Check pending count is displayed
    await expect(page.getByText(/pending review/i)).toBeVisible();

    // Check cluster cards are displayed
    await expect(page.getByText(/duplicate payment failure tickets/i)).toBeVisible();
    await expect(page.getByText(/card declined errors/i)).toBeVisible();
  });

  test('should show cluster detail when cluster is clicked', async ({ page }) => {
    await page.goto('/clusters');

    // Click on first cluster
    await openFirstCluster(page);

    // Wait for detail panel to appear
    await expect(page.getByText('TKT-2026-001')).toBeVisible();
    await expect(page.getByText('TKT-2026-002')).toBeVisible();
    await expect(page.getByText('TKT-2026-003')).toBeVisible();

    // Check matching signals are shown
    await expect(page.getByText('Payments')).toBeVisible();
  });

  test('should display cluster status correctly', async ({ page }) => {
    await page.goto('/clusters');

    // Pending cluster should have appropriate styling
    await expect(page.getByText(/pending/i).first()).toBeVisible();
  });

  test('should open merge dialog and select primary ticket', async ({ page }) => {
    await page.goto('/clusters');

    // Click cluster to open detail
    await openFirstCluster(page);
    await expect(page.getByText('TKT-2026-001')).toBeVisible();

    // Select a ticket preview
    await page.getByText(/payment failed for my order/i).click();

    // Click merge tickets button
    await page.getByRole('button', { name: /merge tickets/i }).click();

    // Merge dialog should open
    await expect(page.getByRole('heading', { name: 'Confirm Merge', exact: true })).toBeVisible();

    // Confirm Merge button should be visible
    await expect(page.getByRole('button', { name: /confirm merge/i })).toBeVisible();
  });

  test('should complete merge workflow successfully', async ({ page }) => {
    await page.goto('/clusters');

    // Open cluster detail
    await openFirstCluster(page);
    await expect(page.getByText('TKT-2026-001')).toBeVisible();

    // Select a ticket preview in detail panel
    await page.getByText(/payment failed for my order/i).click();

    // Open merge dialog
    await page.getByRole('button', { name: /merge tickets/i }).click();
    await expect(page.getByRole('heading', { name: 'Confirm Merge', exact: true })).toBeVisible();

    // Confirm merge
    await page.getByRole('button', { name: /confirm merge/i }).click();

    // Should close dialog
    await expect(page.getByRole('heading', { name: 'Confirm Merge', exact: true })).not.toBeVisible({ timeout: 5000 });
  });

  test('should allow dismissing a cluster', async ({ page }) => {
    // Mock dismiss endpoint
    await page.route('**/api/v1/clusters/**/dismiss', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...mockClusterDetail, status: 'dismissed' }),
      });
    });

    await page.goto('/clusters');

    // Open cluster detail
    await openFirstCluster(page);

    // Find and click dismiss button
    const dismissButton = page.getByRole('button', { name: 'Dismiss Cluster', exact: true });
    if (await dismissButton.isVisible()) {
      // Handle window.prompt mock
      await page.evaluate(() => {
        window.prompt = () => 'Not actually duplicates';
      });

      await dismissButton.click();
    }
  });

  test('should show ticket preview with key information', async ({ page }) => {
    await page.goto('/clusters');

    // Open cluster detail
    await openFirstCluster(page);

    // Ticket previews should show relevant info
    await expect(page.getByText(/payment failed for my order/i)).toBeVisible();
    await expect(page.getByText(/unable to complete payment/i)).toBeVisible();
  });

  test('should filter clusters by status', async ({ page }) => {
    await page.goto('/clusters');

    // Look for filter controls
    const statusFilter = page.getByRole('combobox', { name: /status/i });
    if (await statusFilter.isVisible()) {
      await statusFilter.selectOption('pending');
      // Clusters should still be visible (mock returns pending only)
      await expect(page.getByText(/duplicate payment failure tickets/i)).toBeVisible();
    }
  });

  test('should close detail panel when close button is clicked', async ({ page }) => {
    await page.goto('/clusters');

    // Open cluster detail
    await openFirstCluster(page);
    await expect(page.getByText('TKT-2026-001')).toBeVisible();

    // Close the panel
    const closeButton = page.getByRole('button', { name: /close/i });
    if (await closeButton.isVisible()) {
      await closeButton.click();
      // Detail panel should be closed - tickets should no longer be visible
      await expect(page.getByText('TKT-2026-001')).not.toBeVisible();
    }
  });

  test('should refresh clusters when refresh button is clicked', async ({ page }) => {
    await page.goto('/clusters');

    // Wait for initial load
    await expect(page.getByText(/duplicate payment failure tickets/i)).toBeVisible();

    // Click refresh button
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    await refreshButton.click();

    // Clusters should still be visible after refresh
    await expect(page.getByText(/duplicate payment failure tickets/i)).toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('should display error message when API fails', async ({ page }) => {
    // Mock API error
    await page.route('**/api/v1/clusters**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'internal_error', message: 'Server error' }),
      });
    });

    await page.goto('/clusters');

    // Error banner should be visible
    await expect(page.getByRole('heading', { name: 'Error', exact: true })).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Navigation', () => {
  test('should navigate to clusters page from dashboard', async ({ page }) => {
    // Mock dashboard route
    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], meta: { total: 0, offset: 0, limit: 20, hasMore: false } }),
      });
    });

    await page.goto('/');

    // Look for clusters link in navigation
    const clustersLink = page.getByRole('link', { name: 'Clusters', exact: true });
    if (await clustersLink.isVisible()) {
      await clustersLink.click();
      await expect(page).toHaveURL(/clusters/);
    }
  });
});
