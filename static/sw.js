const CACHE_NOME = "belletti-v2";
const URLS_APP_SHELL = [
    "/static/css/app.css",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NOME).then((cache) => cache.addAll(URLS_APP_SHELL))
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((chaves) =>
            Promise.all(chaves.filter((c) => c !== CACHE_NOME).map((c) => caches.delete(c)))
        )
    );
    self.clients.claim();
});

// Estratégia: network-first pras páginas (sempre tenta rede primeiro,
// só usa cache se estiver offline de verdade) — assim os dados nunca
// ficam desatualizados quando há internet.
self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") return;

    event.respondWith(
        fetch(event.request)
            .then((resposta) => {
                const clone = resposta.clone();
                caches.open(CACHE_NOME).then((cache) => cache.put(event.request, clone));
                return resposta;
            })
            .catch(() => caches.match(event.request))
    );
});

// --- Notificações push ---------------------------------------------------
self.addEventListener("push", (event) => {
    let dados = { titulo: "Belletti Cards Universe", corpo: "Você tem uma notificação nova." };
    try {
        dados = event.data.json();
    } catch (e) {
        if (event.data) dados.corpo = event.data.text();
    }
    event.waitUntil(
        self.registration.showNotification(dados.titulo || "Belletti Cards Universe", {
            body: dados.corpo || "",
            icon: "/static/icons/icon-192.png",
            badge: "/static/icons/icon-192.png",
        })
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow("/relatorios/"));
});
