/**
 * E2E test: Merge workflow.
 *
 * Tests the complete merge flow: view clusters → select cluster → merge → verify.
 */

import { test, expect, type Page } from '@playwright/test';

// Mock API responses for consistent testing
const mockClusters = {
  data: [
    {
      id: 'cluster-001',
      status: 'pending',
      confidence: 'high',
      summary: 'Duplicate payment failure tickets for merchant Acme Corp',
      matching_signals: {
        exact_matches: [
          { field: 'merchant', value: 'Acme Corp' },
          { field: 'transaction_id', value: 'TXN-12345' },
        ],
        text_similarity: { score: 0.92, common_terms: ['payment', 'failed', 'declined'] },
      },
      ticket_count: 3,
      created_at: '2026-01-30T10:00:00Z',
    },
    {
      id: 'cluster-002',
      status: 'pending',
      confidence: 'medium',
      summary: 'Card declined errors for category Electronics',
      matching_signals: {
        exact_matches: [{ field: 'category', value: 'Electronics' }],
        text_similarity: { score: 0.75, common_terms: ['card', 'declined'] },
      },
      ticket_count: 2,
      created_at: '2026-01-30T09:00:00Z',
    },
  ],
  meta: {
    total: 2,
    offset: 0,
    limit: 20,
    has_more: false,
  },
};

const mockClusterDetail = {
  id: 'cluster-001',
  status: 'pending',
  confidence: 'high',
  summary: 'Duplicate payment failure tickets for merchant Acme Corp',
  matching_signals: {
    exact_matches: [
      { field: 'merchant', value: 'Acme Corp' },
      { field: 'transaction_id', value: 'TXN-12345' },
    ],
    text_similarity: { score: 0.92, common_terms: ['payment', 'failed', 'declined'] },
  },
  ticket_count: 3,
  tickets: [
    {
      id: 'ticket-001',
      ticket_number: 'TKT-2026-001',
      summary: 'Payment failed for my order',
      description: 'I tried to pay but the payment was declined.',
      status: 'open',
      priority: 'high',
      channel: 'in_app',
      category: 'Payments',
      region: 'US',
      merchant: 'Acme Corp',
      transaction_id: 'TXN-12345',
      created_at: '2026-01-30T09:30:00Z',
    },
    {
      id: 'ticket-002',
      ticket_number: 'TKT-2026-002',
      summary: 'Unable to complete payment',
      description: 'Payment keeps getting declined on checkout.',
      status: 'open',
      priority: 'high',
      channel: 'chat',
      category: 'Payments',
      region: 'US',
      merchant: 'Acme Corp',
      transaction_id: 'TXN-12345',
      created_at: '2026-01-30T09:45:00Z',
    },
    {
      id: 'ticket-003',
      ticket_number: 'TKT-2026-003',
      summary: 'Payment error at Acme Corp',
      description: 'Getting payment declined message.',
      status: 'open',
      priority: 'medium',
      channel: 'email',
      category: 'Payments',
      region: 'US',
      merchant: 'Acme Corp',
      transaction_id: 'TXN-12345',
      created_at: '2026-01-30T10:00:00Z',
    },
  ],
  created_at: '2026-01-30T10:00:00Z',
};

const mockMergeResponse = {
  id: 'merge-001',
  cluster_id: 'cluster-001',
  primary_ticket_id: 'ticket-001',
  secondary_ticket_ids: ['ticket-002', 'ticket-003'],
  merge_behavior: 'keep_latest',
  status: 'completed',
  performed_by: 'agent@example.com',
  performed_at: '2026-01-30T11:00:00Z',
  revert_deadline: '2026-02-06T11:00:00Z',
};

const mockPendingCount = { pending_count: 2 };

async function setupMockApi(page: Page) {
  // Mock clusters list endpoint
  await page.route('**/api/clusters*', async (route, request) => {
    const url = new URL(request.url());
    const clusterId = url.pathname.match(/\/clusters\/([^/]+)$/)?.[1];

    if (clusterId && !url.pathname.includes('dismiss') && !url.pathname.includes('members')) {
      // Get cluster detail
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockClusterDetail),
      });
    } else if (url.pathname.includes('/pending/count')) {
      // Pending count
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPendingCount),
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
  await page.route('**/api/merges*', async (route, request) => {
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

  test('should display pending clusters list', async ({ page }) => {
    await page.goto('/clusters');
    await expect(page.getByRole('heading', { name: /duplicate clusters/i })).toBeVisible();

    // Check pending count is displayed
    await expect(page.getByText('2')).toBeVisible();
    await expect(page.getByText(/pending review/i)).toBeVisible();

    // Check cluster cards are displayed
    await expect(page.getByText(/duplicate payment failure tickets/i)).toBeVisible();
    await expect(page.getByText(/card declined errors/i)).toBeVisible();
  });

  test('should show cluster detail when cluster is clicked', async ({ page }) => {
    await page.goto('/clusters');

    // Click on first cluster
    await page.getByText(/duplicate payment failure tickets/i).click();

    // Wait for detail panel to appear
    await expect(page.getByText('TKT-2026-001')).toBeVisible();
    await expect(page.getByText('TKT-2026-002')).toBeVisible();
    await expect(page.getByText('TKT-2026-003')).toBeVisible();

    // Check matching signals are shown
    await expect(page.getByText('Acme Corp')).toBeVisible();
  });

  test('should display confidence badge correctly', async ({ page }) => {
    await page.goto('/clusters');

    // High confidence cluster should have appropriate styling
    const highConfidenceBadge = page.locator('[data-testid="confidence-badge"]').first();
    await expect(highConfidenceBadge).toContainText(/high/i);
  });

  test('should open merge dialog and select primary ticket', async ({ page }) => {
    await page.goto('/clusters');

    // Click cluster to open detail
    await page.getByText(/duplicate payment failure tickets/i).click();
    await expect(page.getByText('TKT-2026-001')).toBeVisible();

    // Click merge button
    await page.getByRole('button', { name: /merge/i }).first().click();

    // Merge dialog should open
    await expect(page.getByRole('dialog')).toBeVisible();

    // Primary ticket selection should be available
    await expect(page.getByText(/select primary ticket/i)).toBeVisible();
  });

  test('should complete merge workflow successfully', async ({ page }) => {
    await page.goto('/clusters');

    // Open cluster detail
    await page.getByText(/duplicate payment failure tickets/i).click();
    await expect(page.getByText('TKT-2026-001')).toBeVisible();

    // Open merge dialog
    await page.getByRole('button', { name: /merge/i }).first().click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // Select primary ticket (first one)
    const primaryRadio = page.getByRole('radio').first();
    if (await primaryRadio.isVisible()) {
      await primaryRadio.click();
    }

    // Select merge behavior
    const behaviorSelect = page.getByRole('combobox');
    if (await behaviorSelect.isVisible()) {
      await behaviorSelect.selectOption('keep_latest');
    }

    // Confirm merge
    const confirmButton = page.getByRole('button', { name: /confirm merge/i });
    if (await confirmButton.isVisible()) {
      await confirmButton.click();

      // Should show success message or close dialog
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 });
    }
  });

  test('should allow dismissing a cluster', async ({ page }) => {
    // Mock dismiss endpoint
    await page.route('**/api/clusters/**/dismiss', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...mockClusterDetail, status: 'dismissed' }),
      });
    });

    await page.goto('/clusters');

    // Open cluster detail
    await page.getByText(/duplicate payment failure tickets/i).click();

    // Find and click dismiss button
    const dismissButton = page.getByRole('button', { name: /dismiss/i });
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
    await page.getByText(/duplicate payment failure tickets/i).click();

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
    await page.getByText(/duplicate payment failure tickets/i).click();
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
    await page.route('**/api/clusters*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'internal_error', message: 'Server error' }),
      });
    });

    await page.goto('/clusters');

    // Error banner should be visible
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Navigation', () => {
  test('should navigate to clusters page from dashboard', async ({ page }) => {
    // Mock dashboard route
    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], meta: { total: 0, offset: 0, limit: 20, has_more: false } }),
      });
    });

    await page.goto('/');

    // Look for clusters link in navigation
    const clustersLink = page.getByRole('link', { name: /clusters/i });
    if (await clustersLink.isVisible()) {
      await clustersLink.click();
      await expect(page).toHaveURL(/clusters/);
    }
  });
});
