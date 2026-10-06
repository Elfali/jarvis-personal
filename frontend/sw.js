// Service worker mínimo: permite instalar JARVIS como aplicación y da un
// arranque básico sin conexión. Red primero, para no servir versiones viejas.
const CACHE = "jarvis-v1";
const ASSETS = [
  "/",
  "/static/orb.js",
  "/static/manifest.webmanifest",
  "/static/icon-192.png",
  "/static/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // Nunca cacheamos la API ni el WebSocket.
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/ws")) return;
  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
