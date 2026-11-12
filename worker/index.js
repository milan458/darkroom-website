// Sends the old domain (and www) to https://getnoxium.app with a permanent redirect, keeping the
// path and query, so links and search rankings from darkroom.buzz carry over. Everything else is
// served from the static files. Plain http on getnoxium.app also gets a 301 to https, because
// Google had indexed http://getnoxium.app/ as a separate URL (Search Console, November 2026).
// Preview hosts (*.workers.dev) and local dev are left alone.
const CANONICAL = "getnoxium.app";
const REDIRECT_HOSTS = new Set(["darkroom.buzz", "www.darkroom.buzz", "www.getnoxium.app"]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const insecureCanonical = url.hostname === CANONICAL && url.protocol === "http:";
    if (REDIRECT_HOSTS.has(url.hostname) || insecureCanonical) {
      url.hostname = CANONICAL;
      url.protocol = "https:";
      url.port = "";
      return Response.redirect(url.toString(), 301);
    }
    // Simplified Chinese pages were live for a few hours on 12 Nov 2026, then replaced by Traditional
    // Chinese (/zh-hant/), because Noxium isn't sold in the mainland China App Store. Send old links
    // to the English page.
    if (url.pathname === "/zh-hans" || url.pathname.startsWith("/zh-hans/")) {
      url.pathname = url.pathname.slice("/zh-hans".length) || "/";
      return Response.redirect(url.toString(), 301);
    }
    const response = await env.ASSETS.fetch(request);
    // Static assets answer trailing-slash fixes (/guides → /guides/, /about/ → /about) with a
    // temporary 307. Make them permanent so search engines index only the canonical URL.
    if (response.status === 307) {
      return new Response(null, { status: 308, headers: response.headers });
    }
    return response;
  },
};
