// Offline support: the page shell is cached; board.json is network-first and falls back to the last copy.
// A cached board still carries its own generated_at, and the page downgrades anything older than the fresh window.
const SHELL = "shipyard-shell-v1";
self.addEventListener("install", e => e.waitUntil(caches.open(SHELL).then(c => c.addAll(["./", "index.html", "manifest.webmanifest"]))));
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.pathname.endsWith("board.json")) {
    e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request)));
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
