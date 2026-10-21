export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. API Route: /api/waitlist
    if (url.pathname === "/api/waitlist") {
      const headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Cache-Control": "no-store",
      };

      if (request.method === "OPTIONS") {
        return new Response(null, { headers });
      }

      // GET: Return live spots remaining
      if (request.method === "GET") {
        try {
          if (env.DB) {
            await env.DB.prepare(`
              CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                ip TEXT,
                country TEXT,
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
              )
            `).run();

            const countRow = await env.DB.prepare("SELECT COUNT(*) AS total FROM waitlist").first();
            const total = countRow ? Number(countRow.total || 0) : 0;
            const spotsLeft = Math.max(0, 100 - total);
            return new Response(JSON.stringify({ success: true, total, spotsLeft }), { headers });
          }

          // Fallback baseline if D1 is pending
          return new Response(JSON.stringify({ success: true, total: 62, spotsLeft: 38, note: "D1 pending" }), { headers });
        } catch (err) {
          return new Response(JSON.stringify({ success: false, error: err.message }), { status: 500, headers });
        }
      }

      // POST: Register early tester email
      if (request.method === "POST") {
        try {
          let body = {};
          const contentType = request.headers.get("content-type") || "";

          if (contentType.includes("application/json")) {
            body = await request.json().catch(() => ({}));
          } else if (contentType.includes("form")) {
            const formData = await request.formData();
            body = { email: formData.get("email") };
          } else {
            body = await request.json().catch(() => ({}));
          }

          const email = String(body.email || "").trim().toLowerCase();
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

          if (!email || !emailRegex.test(email)) {
            return new Response(
              JSON.stringify({ success: false, error: "Please enter a valid email address." }),
              { status: 400, headers }
            );
          }

          const clientIp = request.headers.get("cf-connecting-ip") || "unknown";
          const country = request.headers.get("cf-ipcountry") || "unknown";
          const userAgent = request.headers.get("user-agent") || "unknown";

          if (env.DB) {
            await env.DB.prepare(`
              CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                ip TEXT,
                country TEXT,
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
              )
            `).run();

            const existing = await env.DB.prepare("SELECT id FROM waitlist WHERE email = ?").bind(email).first();

            let passNumber;
            let isNew = true;

            if (existing) {
              passNumber = existing.id;
              isNew = false;
            } else {
              const insertRes = await env.DB.prepare(
                "INSERT INTO waitlist (email, ip, country, user_agent) VALUES (?, ?, ?, ?)"
              ).bind(email, clientIp, country, userAgent).run();

              passNumber = insertRes.meta?.last_row_id || 1;
            }

            const countRow = await env.DB.prepare("SELECT COUNT(*) AS total FROM waitlist").first();
            const total = countRow ? Number(countRow.total || 0) : passNumber;
            const spotsLeft = Math.max(0, 100 - total);

            return new Response(
              JSON.stringify({
                success: true,
                email,
                passNumber,
                total,
                spotsLeft,
                isNew,
              }),
              { headers }
            );
          }

          // If DB is not attached yet, return success and note
          return new Response(
            JSON.stringify({
              success: true,
              email,
              passNumber: 63,
              spotsLeft: 37,
              isNew: true,
              warning: "Cloudflare D1 database 'DB' binding is not attached yet in dashboard.",
            }),
            { headers }
          );
        } catch (err) {
          return new Response(JSON.stringify({ success: false, error: err.message }), { status: 500, headers });
        }
      }

      return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers });
    }

    // 2. Serve static website assets
    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    return new Response("Not found", { status: 404 });
  },
};
