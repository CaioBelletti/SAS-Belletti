// ============================================================
// Suporte offline do PDV: guarda produtos localmente (IndexedDB)
// pra buscar sem internet, e enfileira vendas feitas offline pra
// sincronizar assim que a conexão voltar.
// ============================================================

const DB_NOME = "belletti_pdv_offline";
const DB_VERSAO = 1;

function abrirBancoOffline() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NOME, DB_VERSAO);
        req.onupgradeneeded = (evento) => {
            const db = evento.target.result;
            if (!db.objectStoreNames.contains("produtos")) {
                db.createObjectStore("produtos", { keyPath: "id" });
            }
            if (!db.objectStoreNames.contains("vendas_pendentes")) {
                db.createObjectStore("vendas_pendentes", { keyPath: "uuid_offline" });
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function sincronizarCatalogoLocal() {
    try {
        const resp = await fetch("/pdv/api/produtos-offline/");
        if (!resp.ok) return;
        const dados = await resp.json();
        const db = await abrirBancoOffline();
        const tx = db.transaction("produtos", "readwrite");
        const store = tx.objectStore("produtos");
        store.clear();
        dados.produtos.forEach((p) => store.put(p));
        localStorage.setItem("belletti_catalogo_sincronizado_em", dados.gerado_em);
    } catch (e) {
        // sem internet agora — tudo bem, usa o que já tem salvo de antes
    }
}

async function buscarProdutosOffline(termo) {
    const db = await abrirBancoOffline();
    return new Promise((resolve) => {
        const tx = db.transaction("produtos", "readonly");
        const store = tx.objectStore("produtos");
        const resultado = [];
        const termoBusca = termo.toLowerCase();
        store.openCursor().onsuccess = (evento) => {
            const cursor = evento.target.result;
            if (cursor) {
                const p = cursor.value;
                if (
                    p.nome.toLowerCase().includes(termoBusca) ||
                    p.sku.toLowerCase().includes(termoBusca) ||
                    (p.codigo_barras && p.codigo_barras === termo) ||
                    (p.ean && p.ean === termo)
                ) {
                    resultado.push(p);
                }
                cursor.continue();
            } else {
                resolve(resultado.slice(0, 10));
            }
        };
    });
}

async function enfileirarVendaOffline(payload) {
    payload.uuid_offline = crypto.randomUUID();
    payload.salva_em = new Date().toISOString();
    const db = await abrirBancoOffline();
    const tx = db.transaction("vendas_pendentes", "readwrite");
    tx.objectStore("vendas_pendentes").put(payload);
    return payload.uuid_offline;
}

async function contarVendasPendentes() {
    const db = await abrirBancoOffline();
    return new Promise((resolve) => {
        const tx = db.transaction("vendas_pendentes", "readonly");
        const req = tx.objectStore("vendas_pendentes").count();
        req.onsuccess = () => resolve(req.result);
    });
}

async function sincronizarVendasPendentes(csrftoken) {
    const db = await abrirBancoOffline();
    const vendas = await new Promise((resolve) => {
        const tx = db.transaction("vendas_pendentes", "readonly");
        const req = tx.objectStore("vendas_pendentes").getAll();
        req.onsuccess = () => resolve(req.result);
    });

    if (vendas.length === 0) return { sincronizadas: 0, pendentes: 0 };

    try {
        const resp = await fetch("/pdv/api/sincronizar-offline/", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
            body: JSON.stringify({ vendas }),
        });
        if (!resp.ok) return { sincronizadas: 0, pendentes: vendas.length };
        const data = await resp.json();

        const tx = db.transaction("vendas_pendentes", "readwrite");
        const store = tx.objectStore("vendas_pendentes");
        let sincronizadas = 0;
        data.resultados.forEach((r) => {
            if (r.ok) {
                store.delete(r.uuid_offline);
                sincronizadas += 1;
            }
            if (!r.ok && r.pendente_revisao) {
                store.delete(r.uuid_offline);
            }
        });
        return { sincronizadas, pendentes: vendas.length - sincronizadas };
    } catch (e) {
        return { sincronizadas: 0, pendentes: vendas.length };
    }
}

window.addEventListener("online", () => {
    const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
    if (csrftoken) {
        sincronizarVendasPendentes(csrftoken).then((r) => {
            if (r.sincronizadas > 0 && typeof mostrarMensagem === "function") {
                mostrarMensagem(`${r.sincronizadas} venda(s) offline sincronizada(s) com sucesso.`, "sucesso");
            }
            if (typeof atualizarIndicadorOffline === "function") atualizarIndicadorOffline();
        });
    }
});

async function atualizarIndicadorOffline() {
    const el = document.getElementById("indicadorOffline");
    if (!el) return;

    const pendentes = await contarVendasPendentes();
    const offline = !navigator.onLine;

    if (!offline && pendentes === 0) {
        el.style.display = "none";
        return;
    }

    el.style.display = "block";
    if (offline) {
        el.innerHTML = `<div class="msg" style="background:#f26d6d22; color:#f26d6d; border:1px solid #f26d6d55; padding:10px 14px; border-radius:8px; margin-bottom:14px; font-size:13px;">
            📴 Sem conexão — as vendas estão sendo salvas no aparelho${pendentes > 0 ? ` (${pendentes} pendente(s))` : ""} e serão enviadas assim que a internet voltar.
        </div>`;
    } else {
        el.innerHTML = `<div class="msg" style="background:#e8b34d22; color:#e8b34d; border:1px solid #e8b34d55; padding:10px 14px; border-radius:8px; margin-bottom:14px; font-size:13px;">
            🔄 ${pendentes} venda(s) feita(s) offline aguardando sincronização...
        </div>`;
    }
}

window.addEventListener("offline", atualizarIndicadorOffline);
window.addEventListener("online", () => setTimeout(atualizarIndicadorOffline, 1500));
document.addEventListener("DOMContentLoaded", atualizarIndicadorOffline);

sincronizarCatalogoLocal();
