import { test, expect } from "@playwright/test";

test("real catalog, aliases, favorites, persistence and combined filters", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/?view=spaces");
  await expect(
    page.getByRole("heading", { name: /Пространства Москвы/ }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Поиск по афише и каталогу" })
    .fill("ivany");
  await expect(page.locator(".institution-row")).toHaveCount(1);
  await page
    .getByRole("button", { name: /Добавить в избранное: Иваний/ })
    .click();
  await page.reload();
  await expect(
    page.getByRole("button", { name: /Убрать из избранного: Иваний/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("button", { name: "Мои пространства", exact: false })
    .first()
    .click();
  await expect(page.locator(".institution-row")).toHaveCount(1);
  await page
    .getByRole("button", {
      name: "Иваний галерея / IVANY GALLERY",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("dialog").getByRole("link", { name: /Телеграм/ }),
  ).toHaveAttribute("href", "https://t.me/ivanygallery");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("calendar, source journal, public refresh and shareable navigation", async ({
  page,
}) => {
  await page.goto("/?view=calendar");
  await expect(page.locator(".full-calendar")).toBeVisible();
  await page
    .getByRole("button", { name: "Следующий месяц", exact: true })
    .last()
    .click();
  await expect(page.locator(".full-calendar .calendar-heading")).toContainText(
    "ноябрь",
  );
  await page
    .getByRole("button", { name: /17 ноября, событий:/ })
    .last()
    .click();
  await expect(page).toHaveURL(/from=\d{4}-11-17/);
  await page.reload();
  await expect(page.locator(".full-calendar")).toBeVisible();
  await page
    .getByRole("navigation", { name: "Основная навигация" })
    .getByRole("button", { name: /Источники/ })
    .click();
  await expect(page.locator(".source-row").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Обновить данные", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Новая проверка источников не запускалась",
  );
  await expect(
    page.getByRole("link", { name: /Запустить проверку источников/ }),
  ).toHaveAttribute("href", /actions\/workflows\/refresh-deploy.yml/);
});

test("published real events expose evidence, saving and iCalendar", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".workspace-layout").waitFor();
  const response = await page.request.get("/data/events.json");
  const feed = await response.json();
  expect(
    feed.events.length,
    "Production ingestion must have extracted real events",
  ).toBeGreaterThan(0);
  await page.goto("/?period=all");
  await page.locator(".event-title").first().click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByRole("link", { name: /Оригинальный анонс/ }),
  ).toHaveAttribute("href", /^https:\/\//);
  await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(
    dialog.getByRole("button", { name: "Сохранено", exact: true }),
  ).toBeVisible();
  const pending = page.waitForEvent("download");
  await dialog
    .getByRole("button", { name: "В календарь", exact: true })
    .click();
  const download = await pending;
  expect(download.suggestedFilename()).toMatch(/\.ics$/);
  await page.reload();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("button", { name: "Сохранено", exact: true }),
  ).toBeVisible();
});

test("mobile remains readable and filters work", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".workspace-layout")).toBeVisible();
  await page.getByRole("button", { name: "Фильтры", exact: true }).click();
  await page.getByRole("checkbox", { name: "Открытие", exact: true }).check();
  await expect(page).toHaveURL(/type=opening/);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("navigation", { name: "Основная навигация" })
    .getByRole("button", { name: /Пространства/ })
    .click();
  await page
    .getByRole("textbox", { name: "Поиск по афише и каталогу" })
    .fill("nnfn");
  await expect(page.locator(".institution-row")).toHaveCount(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("monochrome layout removes branding and keeps large text in both saved themes", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await expect(page.locator(".workspace-layout")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(
    page.getByRole("heading", { level: 1, name: "Арт-календарь Москвы" }),
  ).toBeVisible();
  await expect(page.getByText("арт / монитор", { exact: true })).toHaveCount(0);
  await expect(
    page.getByText("Большие институции.", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Оставайтесь внимательны.", { exact: true }),
  ).toHaveCount(0);
  expect(
    await page.locator(".brand-symbol,.masthead,.title-asterisk").count(),
  ).toBe(0);
  const sizes = await page.evaluate(() => ({
    body: parseFloat(getComputedStyle(document.documentElement).fontSize),
    title: parseFloat(
      getComputedStyle(document.querySelector(".event-title")!).fontSize,
    ),
    nav: parseFloat(
      getComputedStyle(document.querySelector(".main-nav button")!).fontSize,
    ),
  }));
  expect(sizes.body).toBeGreaterThanOrEqual(20);
  expect(sizes.title).toBeGreaterThanOrEqual(30);
  expect(sizes.nav).toBeGreaterThanOrEqual(22);
  for (const theme of ["light", "dark"]) {
    if (theme === "dark")
      await page.getByRole("button", { name: "Включить тёмную тему" }).click();
    const colors = await page.evaluate(() =>
      [
        document.documentElement,
        document.querySelector(".event-title")!,
        document.querySelector(".period-tabs .active")!,
      ].map((el) => ({
        color: getComputedStyle(el).color,
        background: getComputedStyle(el).backgroundColor,
      })),
    );
    for (const color of colors.flatMap((c) => [c.color, c.background])) {
      const channels = color
        .match(/[\d.]+/g)!
        .slice(0, 3)
        .map(Number);
      expect(channels[0]).toBe(channels[1]);
      expect(channels[1]).toBe(channels[2]);
    }
  }
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(
    page.getByRole("button", { name: "Включить светлую тему" }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("system theme and mobile source/calendar views stay usable at larger sizes", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?view=sources");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator(".source-row").first()).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("navigation", { name: "Основная навигация" })
    .getByRole("button", { name: /Календарь/ })
    .click();
  await expect(page.locator(".full-calendar")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Включить светлую тему" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
