import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ROUTES = [
  { path: "/", title: /Datos.*Vivos/i, label: "home" },
  { path: "/buscar", title: /Sin consulta|Pregunta/i, label: "buscar-empty" },
  { path: "/acerca", title: /Datos del Estado/i, label: "acerca" },
  { path: "/accesibilidad", title: /Ajusta DatosVivos/i, label: "accesibilidad" },
];

const THEMES = ["light", "dark", "contrast-light"] as const;

for (const route of ROUTES) {
  for (const theme of THEMES) {
    test(`${route.label} renders [${theme}]`, async ({ page }) => {
      await page.addInitScript((t) => {
        window.localStorage.setItem("datosvivos:theme", t);
      }, theme);
      await page.goto(route.path);
      await expect(page).toHaveTitle(/Datos.*Vivos/);
      const body = page.locator("body");
      await expect(body).toContainText(route.title);
    });

    test(`${route.label} passes axe a11y [${theme}]`, async ({ page }) => {
      await page.addInitScript((t) => {
        window.localStorage.setItem("datosvivos:theme", t);
      }, theme);
      await page.goto(route.path);
      const results = await new AxeBuilder({ page })
        .disableRules(["region"]) // landmarks ya cubiertos por <main id>; region es too strict
        .analyze();
      const serious = results.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      );
      expect(
        serious,
        `axe a11y violations [${route.path} · ${theme}]:\n${JSON.stringify(serious, null, 2)}`,
      ).toEqual([]);
    });
  }
}

test("home shows wordmark and tagline", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Datos");
  await expect(page.locator("h1")).toContainText("Vivos");
  await expect(page.getByText("Datos del Estado, en tus palabras.")).toBeVisible();
});

test("search input focuses with `/` keyboard shortcut", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("/");
  const input = page.locator("input#hero-search-input");
  await expect(input).toBeFocused();
});

test("color mode toggle persists in localStorage", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Modo oscuro/i }).click();
  const themeAttr = await page.evaluate(() =>
    document.documentElement.getAttribute("data-theme"),
  );
  expect(themeAttr).toBe("dark");
  const stored = await page.evaluate(() =>
    window.localStorage.getItem("datosvivos:theme"),
  );
  expect(stored).toBe("dark");
});
