/**
 * Cloudflare Worker — Anthropic API 代理
 *
 * 用途：把 API Key 藏在 Worker 環境變數，前端不暴露 Key
 *
 * 部署步驟：
 *   1. 登入 https://dash.cloudflare.com
 *   2. Workers & Pages → Create Worker
 *   3. 貼上這整段程式碼
 *   4. Settings → Variables → 新增環境變數：
 *        ANTHROPIC_API_KEY = sk-ant-xxxxxxxx（你的 Key）
 *   5. 部署後取得 Worker URL，例如：
 *        https://baseball-proxy.yourname.workers.dev
 *   6. 將該 URL 填入 taiwan-baseball-tracker.html 的 PROXY_URL 變數
 *
 * 費用：Cloudflare Workers 免費方案每天 10 萬次請求，個人使用完全夠用。
 */

const ALLOWED_ORIGIN = "*";  // 可改成你的 GitHub Pages 網域增加安全性
                              // 例如："https://yourname.github.io"

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // 只接受 POST
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // 讀取前端傳來的 body
    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    // 轉發到 Anthropic API
    const anthropicRes = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(body),
    });

    const data = await anthropicRes.json();

    return new Response(JSON.stringify(data), {
      status: anthropicRes.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      },
    });
  },
};
