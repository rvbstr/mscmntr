import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser', timeout: 30000, fullyParallel: false,
  use: {baseURL: process.env.TEST_BASE_URL || 'http://127.0.0.1:5173',locale:'ru-RU',timezoneId:'Europe/Moscow',
    launchOptions: {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,args:['--no-sandbox']}},
});
