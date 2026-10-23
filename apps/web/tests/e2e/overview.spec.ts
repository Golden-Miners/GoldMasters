import { test, expect } from "@playwright/test";

test.describe("Overview page", () => {
  test("renders overview content on root route", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveTitle("GoldMasters Research Console");
    await expect(page.locator("h1")).toContainText("Overview", { timeout: 10000 });
  });

  test("navigation links are present and clickable", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.locator('nav a[href="/overview"]')).toBeVisible();
    await expect(page.locator('nav a[href="/workbench"]')).toBeVisible();
    await expect(page.locator('nav a[href="/decision"]')).toBeVisible();
    await expect(page.locator('nav a[href="/strategy-lab"]')).toBeVisible();
    await expect(page.locator('nav a[href="/system-health"]')).toBeVisible();
  });

  test("shows unavailable state when market data is unavailable", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(
      page.locator('[data-testid="explicit-state-unavailable"]')
    ).toBeVisible({ timeout: 10000 });
  });

  test("does not show fabricated market data", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.locator("text=2642.15")).not.toBeVisible();
    await expect(page.locator("text=2650.30")).not.toBeVisible();
    await expect(page.locator("text=2680.10")).not.toBeVisible();
  });

  test("does not show fabricated strategy results", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.locator("text=agent_01")).not.toBeVisible();
    await expect(page.locator("text=trend-breakout")).not.toBeVisible();
    await expect(page.locator("text=R:R 1:2.0")).not.toBeVisible();
  });
});

test.describe("Responsive layout", () => {
  test("renders without horizontal overflow at 1366x768", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    const body = page.locator("body");
    const bodyBox = await body.boundingBox();
    const viewportWidth = 1366;
    expect(bodyBox?.width).toBeLessThanOrEqual(viewportWidth);
  });

  test("renders without horizontal overflow at 768x1024", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    const body = page.locator("body");
    const bodyBox = await body.boundingBox();
    const viewportWidth = 768;
    expect(bodyBox?.width).toBeLessThanOrEqual(viewportWidth);
  });

  test("navigation is accessible at mobile width", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(
      page.locator('nav .nav-mobile-toggle')
    ).toBeVisible();
  });
});
