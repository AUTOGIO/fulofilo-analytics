/**
 * FulôFiló — Cloudflare Worker
 * Redirects dashboard.giovannini.us → Streamlit Cloud URL
 *
 * Deploy: bash scripts/deploy_cloudflare_worker.sh https://YOUR_APP.streamlit.app
 *
 * Error 1033 / "Tunnel error": this hostname must not be a Zero Trust Tunnel
 * public hostname. Remove it from Tunnels; use proxied DNS + this Worker only.
 */

const STREAMLIT_URL = "https://autogio-fulofilo.streamlit.app";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Preserve path and query string on redirect
    const destination = STREAMLIT_URL + url.pathname + url.search;

    return Response.redirect(destination, 302);
  },
};
