import { test, expect } from "@playwright/test";

for (const view of ["agenda", "calendar", "spaces", "sources", "review"]) {
  test(`removable filter tags and reset work in ${view}`, async ({ page }) => {
    await page.goto(`/?view=${view}&scene=independent&category=gallery`);
    const tags = page.getByRole("region", { name: "Выбранные фильтры" });
    await expect(tags).toBeVisible();
    await expect(
      tags.getByRole("button", {
        name: "Убрать фильтр: Независимая сцена",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".coverage-note")).toBeVisible();
    expect(
      await tags.evaluate((el) =>
        el.previousElementSibling?.classList.contains("coverage-note"),
      ),
    ).toBe(true);
    await tags
      .getByRole("button", {
        name: "Убрать фильтр: Независимая сцена",
        exact: true,
      })
      .click();
    await expect(page).not.toHaveURL(/scene=/);
    await expect(page).toHaveURL(/category=gallery/);
    await expect(
      page
        .locator(".sidebar select")
        .filter({ has: page.locator('option[value="gallery"]') }),
    ).toHaveValue("gallery");
    await tags
      .getByRole("button", { name: "Сбросить фильтры", exact: true })
      .click();
    await expect(tags).toHaveCount(0);
    await expect(page).not.toHaveURL(/category=|scene=/);
    await expect(
      page.locator(".independent-section,.spotlight-list"),
    ).toHaveCount(0);
  });
}

test("event type/date tags clear independently and restore the calendar", async ({
  page,
}) => {
  await page.goto(
    "/?view=calendar&period=all&type=talk,opening&from=2026-10-17&to=2026-10-31&geography=all",
  );
  const tags = page.getByRole("region", { name: "Выбранные фильтры" });
  await tags
    .getByRole("button", {
      name: "Убрать фильтр: Лекция / дискуссия",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/type=opening/);
  await expect(
    page.getByRole("checkbox", { name: "Лекция / дискуссия", exact: true }),
  ).not.toBeChecked();
  await expect(
    page.getByRole("checkbox", { name: "Открытие", exact: true }),
  ).toBeChecked();
  await tags.getByRole("button", { name: /^Убрать фильтр: С / }).click();
  await expect(page).not.toHaveURL(/from=/);
  await expect(page).toHaveURL(/to=2026-10-31/);
  await tags.getByRole("button", { name: /^Убрать фильтр: По / }).click();
  await expect(page).not.toHaveURL(/to=|period=/);
  await page.reload();
  await expect(
    tags.getByRole("button", { name: "Убрать фильтр: Открытие", exact: true }),
  ).toBeVisible();
  await tags
    .getByRole("button", { name: "Сбросить фильтры", exact: true })
    .click();
  await expect(page.locator(".sidebar input[type=date]").first()).toHaveValue(
    "",
  );
  await expect(
    page.getByRole("combobox", { name: "География", exact: true }),
  ).toHaveValue("moscow");
});

test("status tags work for source and directory statuses", async ({ page }) => {
  await page.goto("/?view=sources");
  await page
    .getByRole("combobox", { name: "Статус источника" })
    .selectOption("working");
  const tags = page.getByRole("region", { name: "Выбранные фильтры" });
  await tags
    .getByRole("button", {
      name: "Убрать фильтр: Статус: Работает",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Статус источника" }),
  ).toHaveValue("");
  await page
    .getByRole("navigation", { name: "Основная навигация" })
    .getByRole("button", { name: /Пространства/ })
    .click();
  await page
    .getByRole("combobox", { name: "Статус пространства" })
    .selectOption("watchlist");
  await tags
    .getByRole("button", {
      name: "Убрать фильтр: Статус: Наблюдение",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Статус пространства" }),
  ).toHaveValue("");
  await expect(tags).toHaveCount(0);
});

test("long filter tags wrap on mobile in both themes", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 844 });
  await page.goto(
    "/?q=оченьдлинныйпоисковыйзапросбезпробеловдляпроверкипереноса&scene=independent&type=talk",
  );
  for (const label of ["Включить тёмную тему", "Включить светлую тему"]) {
    await expect(
      page.getByRole("region", { name: "Выбранные фильтры" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: label }).click();
  }
});

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
  // Exercises several full-catalogue loads, a download and a reload of real data.
  test.slow();
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
  await page.locator(".workspace-layout").waitFor();
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

test("IVANY regional exhibition can be revealed without losing other filters", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-10-18T12:00:00+03:00"));
  await page.goto("/?institution=MSK068&period=ongoing");
  await expect(page.locator(".event-row")).toHaveCount(0);
  await expect(page.locator(".geography-note")).toContainText(
    "в Подмосковье найдено ещё: 1",
  );
  await page
    .getByRole("button", { name: "Включить Подмосковье", exact: true })
    .click();
  await expect(page).toHaveURL(/geography=all/);
  await expect(page).toHaveURL(/institution=MSK068/);
  await expect(page.locator(".event-row")).toHaveCount(1);
  await expect(page.locator(".event-row")).toContainText("ХЛЕБА");
  await expect(page.locator(".event-row")).toContainText("Подмосковье");
  await page.reload();
  await expect(page.locator(".event-row")).toHaveCount(1);
  await page.getByRole("button", { name: "Архив", exact: true }).click();
  await expect(
    page.locator(".event-row").filter({ hasText: "ХЛЕБА" }),
  ).toHaveCount(1);
  await expect(
    page.locator(".event-row").filter({ hasText: "ХЛЕБА" }),
  ).toContainText("18:00");
});

test("review queue exposes remaining source text, reasons and filters", async ({
  page,
  request,
}) => {
  const queue = await (await request.get("/data/review.json")).json();
  const catalog = await (await request.get("/data/catalog.json")).json();
  const example = queue.items.find(
    (row: { candidate?: { description?: string; primary_url?: string } }) =>
      row.candidate?.description && row.candidate.primary_url,
  );
  const source = catalog.sources.find(
    (row: { source_id: string }) => row.source_id === example.source_id,
  );
  await page.goto("/?view=review");
  const candidates = page.getByRole("region", {
    name: "Источники-кандидаты",
    exact: true,
    includeHidden: true,
  });
  const posts = page.getByRole("region", {
    name: "Публикации на проверке",
    exact: true,
  });
  await expect(posts).toBeVisible();
  await expect(posts.locator(".review-card")).toHaveCount(
    Math.min(25, queue.items.length),
  );
  if (queue.items.length > 25) {
    await page
      .getByRole("button", { name: /^Показать ещё · осталось/ })
      .click();
    await expect(posts.locator(".review-card")).toHaveCount(
      Math.min(50, queue.items.length),
    );
  }
  await page.getByRole("button", { name: /^Источники-кандидаты/ }).click();
  await expect(candidates).toBeVisible();
  await expect(candidates.locator(".review-card")).toHaveCount(0);
  await page.getByRole("button", { name: /^Публикации/ }).click();
  await page
    .getByRole("combobox", { name: "Причина остановки публикации" })
    .selectOption(example.reason);
  await page
    .getByRole("textbox", { name: "Поиск по афише и каталогу" })
    .fill(source.url);
  expect(await posts.locator(".review-card").count()).toBeGreaterThan(0);
  await posts
    .locator(".review-card")
    .first()
    .getByText("Прочитать извлечённый текст", { exact: true })
    .click();
  await expect(posts.locator(".review-text").first()).toBeVisible();
  await page.getByRole("button", { name: /^Убрать фильтр: Причина:/ }).click();
  await expect(
    page.getByRole("combobox", { name: "Причина остановки публикации" }),
  ).toHaveValue("");
  await page
    .getByRole("region", { name: "Выбранные фильтры" })
    .getByRole("button", { name: "Сбросить фильтры", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Выбранные фильтры" }),
  ).toHaveCount(0);
});

test("missing review snapshot does not block the agenda and can be retried", async ({
  page,
  request,
}) => {
  const queue = await (await request.get("/data/review.json")).json();
  await page.route("**/data/review.json?*", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.goto("/");
  await expect(page.locator(".event-row").first()).toBeVisible();
  await page
    .getByRole("navigation", { name: "Основная навигация" })
    .getByRole("button", { name: /На проверке/ })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Не удалось загрузить очередь",
  );
  await page.unroute("**/data/review.json?*");
  await page
    .getByRole("button", { name: "Повторить загрузку очереди", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page
      .getByRole("region", { name: "Публикации на проверке" })
      .locator(".review-card"),
  ).toHaveCount(Math.min(25, queue.items.length));
});

test("review and geography notices fit mobile in both themes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 844 });
  for (const view of ["agenda", "review"]) {
    await page.goto(
      view === "agenda" ? "/?institution=MSK068" : "/?view=review",
    );
    await expect(page.locator(".workspace-layout")).toBeVisible();
    for (const theme of ["light", "dark"]) {
      await page.evaluate(
        (value) => (document.documentElement.dataset.theme = value),
        theme,
      );
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
  }
});

test("UNOVIS stays absent from the public directory and old detail links", async ({
  page,
}) => {
  await page.goto("/?view=spaces&q=unovis");
  await expect(page.locator(".workspace-layout")).toBeVisible();
  await expect(page.locator(".institution-row")).toHaveCount(0);
  await page.goto("/?space=WATCH02");
  await page.locator(".workspace-layout").waitFor();
  await expect(page.getByRole("dialog")).toContainText(
    "В опубликованном наборе данных нет этой записи",
  );
});

test("tentative events show their uncertainties in calendar cards and exports", async ({
  page,
  request,
}) => {
  const feed = await (await request.get("/data/events.json")).json();
  const event = feed.events.find(
    (row: { review_status?: string; start_date: string }) =>
      row.review_status === "tentative" && row.start_date >= "2026-10-19",
  );
  await page.goto(
    `/?view=calendar&period=all&institution=${event.institution_id}&geography=all&from=${event.start_date}&to=${event.start_date}`,
  );
  await expect(page.locator(".tentative-calendar-count").first()).toBeVisible();
  const card = page
    .locator(".event-row")
    .filter({
      has: page.getByRole("button", { name: event.title, exact: true }),
    })
    .first();
  await expect(card.getByText("Предварительно", { exact: true })).toBeVisible();
  await expect(
    card.getByRole("complementary", { name: "Предварительные данные" }),
  ).toContainText(event.uncertainties[0]);
  await card.getByRole("button", { name: event.title, exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByRole("complementary", { name: "Предварительные данные" }),
  ).toBeVisible();
  const downloading = page.waitForEvent("download");
  await dialog
    .getByRole("button", { name: "В календарь", exact: true })
    .click();
  const file = await downloading;
  const { readFile } = await import("node:fs/promises");
  const content = (await readFile((await file.path())!, "utf8")).replaceAll(
    "\r\n ",
    "",
  );
  expect(content).toContain("STATUS:TENTATIVE");
  expect(content).toContain("[Предварительно]");
});
