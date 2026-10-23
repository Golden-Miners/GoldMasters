import { test, expect } from "@playwright/test";

test.describe("Instrument Workbench page", () => {
  test("renders workbench content", async ({ page }) => {
    await page.goto("/workbench", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveTitle("GoldMasters Research Console");
    await expect(
      page.locator('nav a[href="/workbench"]')
    ).toBeVisible();
  });

  test("shows offline state when market data is unavailable", async ({ page }) => {
    await page.goto("/workbench", { waitUntil: "domcontentloaded" });
    await expect(
      page.locator('section[data-testid="explicit-state-unavailable"]')
    ).toBeVisible({ timeout: 10000 });
  });

  test("does not show fabricated market data", async ({ page }) => {
    await page.goto("/workbench", { waitUntil: "domcontentloaded" });
    await expect(page.locator("text=2642.15")).not.toBeVisible();
    await expect(page.locator("text=2650.30")).not.toBeVisible();
    await expect(page.locator("text=2680.10")).not.toBeVisible();
  });
});

test.describe("Workbench responsive layout", () => {
  test("renders without horizontal overflow at 1366x768", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/workbench", { waitUntil: "domcontentloaded" });
    const body = page.locator("body");
    const bodyBox = await body.boundingBox();
    const viewportWidth = 1366;
    expect(bodyBox?.width).toBeLessThanOrEqual(viewportWidth);
  });

  test("renders without horizontal overflow at 768x1024", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/workbench", { waitUntil: "domcontentloaded" });
    const body = page.locator("body");
    const bodyBox = await body.boundingBox();
    const viewportWidth = 768;
    expect(bodyBox?.width).toBeLessThanOrEqual(viewportWidth);
  });
});
