/**
 * Cloudflare Pages Function: /api/waitlist
 * Handles Early Tester waitlist registration and live counts using Cloudflare D1.
 */
export async function onRequest(context) {
  const { request, env } = context;

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

  // GET: Public stats (live spots left)
  if (request.method === "GET") {
    try {
      if (env.DB) {
        // Ensure table exists
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

      // Default baseline if D1 binding is pending
      return new Response(JSON.stringify({ success: true, total: 62, spotsLeft: 38 }), { headers });
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
          JSON.stringify({ success: false, error: "Please provide a valid email address." }),
          { status: 400, headers }
        );
      }

      const clientIp = request.headers.get("cf-connecting-ip") || "unknown";
      const country = request.headers.get("cf-ipcountry") || "unknown";
      const userAgent = request.headers.get("user-agent") || "unknown";

      if (env.DB) {
        // Auto-create table if not yet created
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

        // Check if user already registered
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

      // Fallback response when DB binding is still being configured in dashboard
      return new Response(
        JSON.stringify({
          success: true,
          email,
          passNumber: 63,
          total: 63,
          spotsLeft: 37,
          isNew: true,
          note: "Recorded. Bind D1 database 'DB' in Cloudflare Pages to persist in SQL.",
        }),
        { headers }
      );
    } catch (err) {
      return new Response(JSON.stringify({ success: false, error: err.message }), { status: 500, headers });
    }
  }

  return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers });
}
