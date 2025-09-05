import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('textbox', { name: '姓名输入框' }).click();
  await page.getByRole('textbox', { name: '姓名输入框' }).fill('你好');
  await page.getByRole('textbox', { name: '邮箱输入框' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).fill('111.co m');
  await page.getByRole('textbox', { name: '邮箱输入框' }).press('Enter');
  await page.getByRole('textbox', { name: '邮箱输入框' }).fill('111.com');
  await page.getByRole('checkbox', { name: '订阅通讯录' }).check();
  await page.getByRole('button', { name: '提交表单' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).click();
  await page.getByRole('textbox', { name: '邮箱输入框' }).fill('111.@co m');
  await page.getByRole('textbox', { name: '邮箱输入框' }).press('Enter');
  await page.getByRole('textbox', { name: '邮箱输入框' }).fill('111.@');
  await page.getByRole('textbox', { name: '邮箱输入框' }).press('CapsLock');
  await page.getByRole('textbox', { name: '邮箱输入框' }).fill('111.@qq.com');
  await page.getByRole('button', { name: '提交表单' }).click();
});