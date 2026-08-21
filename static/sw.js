/* Fluér de Luné — Service Worker
   Strategy:
   - HTML navigations: network-first (fresh content), offline fallback page
   - Static assets: cache-first with background update
   - API / admin / media: never cached
*/
const VERSION = 'fdl-v1';
const STATIC_CACHE = `${VERSION}-static`;
const OFFLINE_URL = '/offline/';

const NEVER_CACHE = [
    '/admin/',
    '/cart/',
    '/wishlist/',
    '/checkout/',
    '/payments/',
    '/orders/',
    '/accounts/',
    '/media/',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => cache.addAll([
            OFFLINE_URL,
            '/static/css/main.css',
            '/static/js/main.js',
        ])).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const { request } = event;

    if (request.method !== 'GET') return;
    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;
    if (NEVER_CACHE.some((prefix) => url.pathname.startsWith(prefix))) return;
    if (url.pathname.startsWith('/partials/')) return;

    /* Page navigations → network-first */
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    const copy = response.clone();
                    caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
                    return response;
                })
                .catch(() =>
                    caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL))
                )
        );
        return;
    }

    /* Static assets → cache-first */
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then((cached) => {
                const fetchPromise = fetch(request).then((response) => {
                    if (response.ok) {
                        const copy = response.clone();
                        caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
                    }
                    return response;
                });
                return cached || fetchPromise;
            })
        );
    }
});
