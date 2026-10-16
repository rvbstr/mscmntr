import { test, expect } from '@playwright/test';

test('real catalog, aliases, favorites, persistence and combined filters', async ({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/?view=spaces');
  await expect(page.getByRole('heading',{name:/Пространства Москвы/})).toBeVisible();
  await page.getByRole('textbox',{name:'Поиск по афише и каталогу'}).fill('ivany');
  await expect(page.locator('.institution-row')).toHaveCount(1);
  await page.getByRole('button',{name:/Добавить в избранное: Иваний/}).click();
  await page.reload();
  await expect(page.getByRole('button',{name:/Убрать из избранного: Иваний/})).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button',{name:'Мои пространства',exact:false}).first().click();
  await expect(page.locator('.institution-row')).toHaveCount(1);
  await page.getByRole('button',{name:'Иваний галерея / IVANY GALLERY',exact:true}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByRole('link',{name:/Телеграм/})).toHaveAttribute('href','https://t.me/ivanygallery');
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('calendar, source journal, public refresh and shareable navigation',async ({page})=>{
  await page.goto('/?view=calendar');
  await expect(page.locator('.full-calendar')).toBeVisible();
  await page.getByRole('button',{name:'Следующий месяц',exact:true}).last().click();
  await expect(page.locator('.full-calendar .calendar-heading')).toContainText('ноябрь');
  await page.getByRole('button',{name:/17 ноября, событий:/}).last().click();
  await expect(page).toHaveURL(/from=\d{4}-11-17/);
  await page.reload();await expect(page.locator('.full-calendar')).toBeVisible();
  await page.getByRole('navigation',{name:'Основная навигация'}).getByRole('button',{name:/Источники/}).click();
  await expect(page.locator('.source-row').first()).toBeVisible();
  await page.getByRole('button',{name:'Обновить данные',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Новая проверка источников не запускалась');
  await expect(page.getByRole('link',{name:/Запустить проверку источников/})).toHaveAttribute('href',/actions\/workflows\/refresh-deploy.yml/);
});

test('published real events expose evidence, saving and iCalendar',async({page})=>{
  await page.goto('/');await page.locator('.workspace-layout').waitFor();
  const response=await page.request.get('/data/events.json');const feed=await response.json();
  expect(feed.events.length,'Production ingestion must have extracted real events').toBeGreaterThan(0);
  await page.goto('/?period=all');
  await page.locator('.event-title').first().click();
  const dialog=page.getByRole('dialog');await expect(dialog.getByRole('link',{name:/Оригинальный анонс/})).toHaveAttribute('href',/^https:\/\//);
  await dialog.getByRole('button',{name:'Сохранить',exact:true}).click();await expect(dialog.getByRole('button',{name:'Сохранено',exact:true})).toBeVisible();
  const pending=page.waitForEvent('download');await dialog.getByRole('button',{name:'В календарь',exact:true}).click();const download=await pending;expect(download.suggestedFilename()).toMatch(/\.ics$/);
  await page.reload();await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByRole('dialog').getByRole('button',{name:'Сохранено',exact:true})).toBeVisible();
});

test('mobile remains readable and filters work',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');
  await expect(page.locator('.workspace-layout')).toBeVisible();
  await page.getByRole('button',{name:'Фильтры',exact:true}).click();
  await page.getByRole('checkbox',{name:'Открытие',exact:true}).check();
  await expect(page).toHaveURL(/type=opening/);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.getByRole('navigation',{name:'Основная навигация'}).getByRole('button',{name:/Пространства/}).click();
  await page.getByRole('textbox',{name:'Поиск по афише и каталогу'}).fill('nnfn');
  await expect(page.locator('.institution-row')).toHaveCount(1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
