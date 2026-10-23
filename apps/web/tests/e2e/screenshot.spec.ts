import { test, expect } from "@playwright/test";

test.describe("Visual verification screenshots", () => {
  test("Overview at 1366x768", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.screenshot({
      path: "tests/e2e/screenshots/overview-1366x768.png",
      fullPage: true,
    });
  });

  test("Overview at 768x1024", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.screenshot({
      path: "tests/e2e/screenshots/overview-768x1024.png",
      fullPage: true,
    });
  });

  test("Overview at 375x812 (mobile)", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.screenshot({
      path: "tests/e2e/screenshots/overview-375x812.png",
      fullPage: true,
    });
  });

  test("System Health at 1366x768", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/system-health", { waitUntil: "domcontentloaded" });
    await page.screenshot({
      path: "tests/e2e/screenshots/system-health-1366x768.png",
      fullPage: true,
    });
  });

  test("System Health at 375x812 (mobile)", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/system-health", { waitUntil: "domcontentloaded" });
    await page.screenshot({
      path: "tests/e2e/screenshots/system-health-375x812.png",
      fullPage: true,
    });
  });
});
