// In local dev, VITE_API_BASE_URL / VITE_WS_URL are set explicitly (see
// .env.example) since the frontend dev server and backend run on different
// ports/origins.
//
// In production, the backend serves the built frontend itself as static
// files (Technical Architecture doc section 7 — single service), so
// frontend and backend share an origin. Rather than bake a specific
// deployed URL into the build (fragile, and easy to get wrong), fall back
// to relative/derived URLs when the env vars aren't set: an empty base URL
// resolves against the current origin, and the WebSocket URL is derived
// from window.location so it automatically uses wss:// on https:// pages —
// exactly the mixed-content/WSS pitfall the deployment ticket calls out.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export const WS_URL: string =
  import.meta.env.VITE_WS_URL ??
  `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/events`;
