// Sends the old domain (and www) to https://getnoxium.app with a permanent redirect, keeping the
// path and query, so links and search rankings from darkroom.buzz carry over. Everything else is
// served from the static files. Preview hosts (*.workers.dev) are left alone.
const CANONICAL = "getnoxium.app";
// Paused 26 Oct 2026: getnoxium.app doesn't resolve yet (new registration), so darkroom.buzz serves
// the site directly. Put "darkroom.buzz" and "www.darkroom.buzz" back once getnoxium.app loads.
const REDIRECT_HOSTS = new Set(["www.getnoxium.app"]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (REDIRECT_HOSTS.has(url.hostname)) {
      url.hostname = CANONICAL;
      url.protocol = "https:";
      url.port = "";
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
