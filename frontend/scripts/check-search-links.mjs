// Run against the local Vite preview with Playwright installed (or PLAYWRIGHT_MODULE set).
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || "playwright");
const base = process.env.PREVIEW_URL || "http://127.0.0.1:4173";
const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "msedge", headless: true });
const first = "11111111-1111-4111-8111-111111111111";
const second = "22222222-2222-4222-8222-222222222222";
const token = "33333333-3333-4333-8333-333333333333";
const answers = new Map();
let searches = 0;
let shared = false;
const errors = [];
async function mock(context, owner, member = false, admin = false) {
  await context.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1/", "");
    const send = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "auth/csrf") return route.fulfill({ contentType: "application/json", headers: { "set-cookie": "csrftoken=test; Path=/" }, body: "{}" });
    if (path === "auth/me") return member ? send({ id: "member", name: "테스트", email: "test@example.com" }) : send({}, 401);
    if (path === "me/searches" && member) return send({ items: [{ ...answers.get(first), id: first, created_at: "2026-09-22T00:00:00Z" }] });
    if (admin && path === "admin/session") return send({ authenticated: true });
    if (admin && path === "admin/dashboard") return send({
      summary: { total_reports: 0, received_reports: 0, reviewing_reports: 0, completed_reports: 0 },
      recent_reports: [], recent_users: [], recent_searches: [{ ...answers.get(first), id: first, user_name: "테스트", created_at: "2026-09-22T00:00:00Z" }],
    });
    if (admin && path === "admin/searches") {
      const offset = new URL(route.request().url()).searchParams.get("offset");
      return send({ total: 21, items: [{ ...answers.get(first), id: first,
        question: offset === "20" ? "관리자 목록 두 번째 페이지" : answers.get(first).question,
        user_name: "테스트", user_email: "test@example.com", created_at: "2026-09-22T00:00:00Z" }] });
    }
    if (admin && path === `admin/searches/${first}`) return send({ ...answers.get(first), id: first });
    if (path === "searches") {
      searches++;
      const input = route.request().postDataJSON();
      const id = searches === 1 ? first : second;
      const result = { search_result_id: id, question: input.question, audience_level: input.audience_level,
        response_type: "answered", summary: `요약 ${searches}`, message: `저장된 답변 ${searches}`, citations: [], media: [] };
      answers.set(id, result);
      if (input.question === "느린 질문") await new Promise(resolve => setTimeout(resolve, 600));
      return send(result);
    }
    if (path.endsWith("/share") && owner) { shared = true; return send({ share_path: `/share/${token}` }); }
    if (path === `shared-searches/${token}` && shared) return send({ ...answers.get(first), search_result_id: undefined, shared: true, share_path: `/share/${token}` });
    if (path.startsWith("searches/") && owner && answers.has(path.split("/")[1])) return send(answers.get(path.split("/")[1]));
    return send({ error: { message: "결과를 찾을 수 없거나 접근 권한이 없습니다." } }, 404);
  });
}
try {
  const context = await browser.newContext();
  await mock(context, true);
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const page = await context.newPage();
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(base);
  await page.getByRole("textbox", { name: "질문", exact: true }).fill("경복궁은 왜 지어졌나요?");
  await page.getByRole("button", { name: "질문하기", exact: true }).click();
  await page.waitForURL(`**/search/${first}`);
  await page.getByText("저장된 답변 1", { exact: true }).waitFor();
  if (process.env.SCREENSHOT_DIR) await page.screenshot({ path: `${process.env.SCREENSHOT_DIR}/share-header-desktop.png` });
  await page.reload();
  await page.getByText("요약 1", { exact: true }).waitFor();
  assert.equal(searches, 1, "reload must not generate another answer");
  await page.getByRole("button", { name: "초등학생", exact: true }).click();
  await page.waitForURL(`**/search/${second}`);
  await page.goBack();
  await page.getByText("저장된 답변 1", { exact: true }).waitFor();
  await page.goForward();
  await page.getByText("저장된 답변 2", { exact: true }).waitFor();
  await page.goBack();
  await page.getByText("저장된 답변 1", { exact: true }).waitFor();
  await page.getByRole("button", { name: "공유하기", exact: true }).click();
  await page.getByText("복사되었습니다", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), `${base}/share/${token}`);
  assert.equal(await page.getByRole("textbox", { name: "공유 주소", exact: true }).count(), 0);
  await page.getByText("복사되었습니다", { exact: true }).waitFor({ state: "hidden" });
  // Exercise the real non-secure HTTP origin, not a granted clipboard mock.
  const insecureContext = await browser.newContext();
  await mock(insecureContext, true);
  await insecureContext.route("http://heritage.test/**", async route => {
    const target = new URL(route.request().url());
    if (target.pathname.startsWith("/api/")) return route.fallback();
    const response = await route.fetch({ url: `${base}${target.pathname}${target.search}` });
    return route.fulfill({ response });
  });
  const insecurePage = await insecureContext.newPage();
  insecurePage.on("pageerror", error => errors.push(error.message));
  await insecurePage.goto(`http://heritage.test/search/${first}`);
  assert.equal(await insecurePage.evaluate(() => window.isSecureContext), false);
  assert.equal(await insecurePage.evaluate(() => Boolean(navigator.clipboard)), false);
  await insecurePage.getByRole("button", { name: "공유하기", exact: true }).click();
  await insecurePage.getByText("복사되었습니다", { exact: true }).waitFor();
  await page.bringToFront();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), `http://heritage.test/share/${token}`);
  assert.equal(await insecurePage.locator("textarea").count(), 0, "temporary copy field must be removed");
  await insecurePage.bringToFront();
  await insecurePage.evaluate(() => { document.execCommand = () => false; });
  await insecurePage.getByRole("button", { name: "공유하기", exact: true }).click();
  await insecurePage.getByText("복사하지 못했습니다. 다시 시도해 주세요.", { exact: true }).waitFor();
  assert.equal(await insecurePage.getByText("복사되었습니다", { exact: true }).count(), 0);
  await insecurePage.reload();
  await insecurePage.route(`**/api/v1/searches/${first}/share`, route => route.fulfill({
    status: 503, contentType: "application/json", body: JSON.stringify({ error: { message: "공유 링크 생성 서버 오류" } }),
  }));
  await insecurePage.getByRole("button", { name: "공유하기", exact: true }).click();
  await insecurePage.getByText("공유 링크 생성 서버 오류", { exact: true }).waitFor();
  assert.equal(await insecurePage.getByText("복사되었습니다", { exact: true }).count(), 0);
  await insecureContext.close();
  const visitor = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await mock(visitor, false);
  const publicPage = await visitor.newPage();
  publicPage.on("pageerror", error => errors.push(error.message));
  await publicPage.goto(`${base}/share/${token}`);
  await publicPage.getByText("저장된 답변 1", { exact: true }).waitFor();
  await publicPage.getByRole("button", { name: "공유하기", exact: true }).waitFor();
  assert.equal(await publicPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, "mobile layout should fit viewport");
  if (process.env.SCREENSHOT_DIR) await publicPage.screenshot({ path: `${process.env.SCREENSHOT_DIR}/share-header-mobile.png` });
  await publicPage.reload();
  await publicPage.getByText("요약 1", { exact: true }).waitFor();
  await publicPage.goto(`${base}/search/${first}`);
  await publicPage.getByRole("alert").waitFor();
  await publicPage.goto(`${base}/share/invalid`);
  await publicPage.getByRole("alert").waitFor();
  await page.getByRole("button", { name: "← 검색으로 돌아가기" }).click();
  await page.getByRole("textbox", { name: "질문", exact: true }).fill("느린 질문");
  await page.getByRole("button", { name: "질문하기", exact: true }).click();
  await page.getByRole("button", { name: "← 검색으로 돌아가기" }).click();
  await page.waitForTimeout(900);
  assert.equal(new URL(page.url()).pathname, "/", "late answers must not navigate away from home");
  await page.getByRole("textbox", { name: "질문", exact: true }).waitFor();
  const memberContext = await browser.newContext();
  await mock(memberContext, true, true);
  const memberPage = await memberContext.newPage();
  memberPage.on("pageerror", error => errors.push(error.message));
  await memberPage.goto(`${base}/mypage/searches`);
  await memberPage.getByRole("button", { name: /경복궁은 왜 지어졌나요/ }).click();
  await memberPage.waitForURL(`**/mypage/searches/${first}`);
  await memberPage.getByText("저장된 답변 1", { exact: true }).waitFor();
  await memberPage.getByRole("button", { name: "공유하기", exact: true }).waitFor();
  await memberPage.reload();
  await memberPage.getByText("요약 1", { exact: true }).waitFor();
  await memberPage.goBack();
  await memberPage.getByRole("heading", { name: "나의 검색 기록", exact: true }).waitFor();
  await memberPage.goForward();
  await memberPage.getByText("저장된 답변 1", { exact: true }).waitFor();
  await memberPage.getByRole("button", { name: "← 나의 검색기록으로 돌아가기", exact: true }).click();
  await memberPage.getByRole("heading", { name: "나의 검색 기록", exact: true }).waitFor();
  // main's admin navigation remains read-only and uses only the admin endpoint.
  const searchCountBeforeAdmin = searches;
  const adminContext = await browser.newContext();
  await mock(adminContext, false, false, true);
  const adminPage = await adminContext.newPage();
  adminPage.on("pageerror", error => errors.push(error.message));
  await adminPage.goto(`${base}/admin`);
  await adminPage.getByRole("button", { name: /경복궁은 왜 지어졌나요/ }).click();
  await adminPage.waitForURL(`**/admin/searches/${first}`);
  await adminPage.getByText("저장된 답변 1", { exact: true }).waitFor();
  for (const name of ["초등학생", "중·고등학생", "성인 일반"]) {
    assert.equal(await adminPage.getByRole("button", { name, exact: true }).isDisabled(), true);
  }
  assert.equal(await adminPage.getByRole("button", { name: "공유하기", exact: true }).count(), 0);
  await adminPage.reload();
  await adminPage.getByText("저장된 답변 1", { exact: true }).waitFor();
  await adminPage.goBack();
  await adminPage.getByRole("heading", { name: "운영 대시보드", exact: true }).waitFor();
  await adminPage.goForward();
  await adminPage.getByText("저장된 답변 1", { exact: true }).waitFor();
  await adminPage.getByRole("button", { name: "← 관리자 검색기록으로 돌아가기", exact: true }).click();
  await adminPage.getByRole("heading", { name: "전체 검색 기록", exact: true }).waitFor();
  await adminPage.getByRole("button", { name: "다음", exact: true }).click();
  await adminPage.getByRole("button", { name: /관리자 목록 두 번째 페이지/ }).waitFor();
  await adminPage.getByRole("button", { name: "이전", exact: true }).click();
  await adminPage.getByRole("button", { name: /경복궁은 왜 지어졌나요/ }).waitFor();
  await adminPage.getByRole("link", { name: "이용약관", exact: true }).click();
  await adminPage.getByRole("dialog", { name: "이용약관", exact: true }).waitFor();
  await adminPage.getByRole("button", { name: "문서 닫기", exact: true }).click();
  assert.equal(new URL(adminPage.url()).pathname, "/admin/searches");
  assert.equal(searches, searchCountBeforeAdmin, "admin review must not generate answers");
  assert.deepEqual(errors, []);
  console.log("PASS: HTTPS/HTTP clipboard copy, rejected copy and share API errors, search URL, reload, level change, back/forward, explicit sharing, anonymous/mobile access, denied/invalid links stale response cancellation mypage history/refresh/navigation, admin read-only/detail/pagination navigation and legal modal");
} finally { await browser.close(); }
