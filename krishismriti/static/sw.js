// Offline shell: the app opens with no signal; API calls need network (queued in production).
const C = "ks-v2";
self.addEventListener("install", e => e.waitUntil(caches.open(C).then(c => c.addAll(["/", "/static/icon.svg", "/static/manifest.webmanifest"]))));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k))))));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.pathname.startsWith("/api")) return;
  e.respondWith(fetch(e.request).then(r => { const cp = r.clone(); caches.open(C).then(c => c.put(e.request, cp)); return r; })
    .catch(() => caches.match(e.request)));
});
