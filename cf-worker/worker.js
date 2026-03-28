/**
 * FulôFiló — Cloudflare Worker
 * Redirects dashboard.giovannini.us → Streamlit Cloud URL
 * Update STREAMLIT_URL after deploying on share.streamlit.io
 */

const STREAMLIT_URL = "https://REPLACE_WITH_YOUR_STREAMLIT_URL.streamlit.app";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Preserve path and query string on redirect
    const destination = STREAMLIT_URL + url.pathname + url.search;

    return Response.redirect(destination, 302);
  },
};
