"""
Busca automática de imagem de carta pra ilustrar o produto no PDV.

Usa bancos de dados públicos feitos especificamente pra esse tipo de
uso (diferente de "procurar no Google e torcer") — cada um deles é a
fonte oficial/comunitária de referência do próprio jogo:

- Magic: The Gathering -> Scryfall (https://scryfall.com)
- Pokémon               -> pokemontcg.io (https://pokemontcg.io)
- Yu-Gi-Oh!             -> YGOPRODeck (https://ygoprodeck.com)

Todas as funções aqui SEMPRE devolvem uma lista (vazia em caso de
erro/timeout/sem resultado) — nunca deixam a tela quebrar por causa
de uma API externa fora do ar.
"""
import requests

TIMEOUT = 8


def _seguro(func):
    """Roda a busca e nunca deixa uma falha de rede quebrar a tela."""
    try:
        return func()
    except (requests.RequestException, ValueError, KeyError):
        return []


def _preco_seguro(valor):
    """Converte preço (que às vezes vem como texto) pra float, ou None se não der."""
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _buscar_magic(nome):
    def _fazer():
        resp = requests.get(
            "https://api.scryfall.com/cards/search",
            params={"q": nome, "unique": "prints"},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        dados = resp.json().get("data", [])[:3]
        candidatos = []
        for carta in dados:
            imagens = carta.get("image_uris") or (carta.get("card_faces", [{}])[0].get("image_uris") if carta.get("card_faces") else {})
            if not imagens:
                continue
            precos = carta.get("prices", {})
            candidatos.append({
                "titulo": carta.get("name", nome),
                "edicao": carta.get("set_name", ""),
                "imagem_url": imagens.get("large") or imagens.get("normal"),
                "thumb_url": imagens.get("small") or imagens.get("normal"),
                "raridade": (carta.get("rarity") or "").capitalize(),
                "tipo": carta.get("type_line", ""),
                "preco_referencia": _preco_seguro(precos.get("usd")),
                "preco_moeda": "USD",
            })
        return candidatos
    return _seguro(_fazer)


def _buscar_pokemon(nome):
    def _fazer():
        resp = requests.get(
            "https://api.pokemontcg.io/v2/cards",
            params={"q": f'name:"{nome}"', "pageSize": 3},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        dados = resp.json().get("data", [])[:3]
        candidatos = []
        for carta in dados:
            imagens = carta.get("images", {})
            if not imagens.get("large"):
                continue
            preco = None
            tcgplayer = (carta.get("tcgplayer") or {}).get("prices") or {}
            for variante in tcgplayer.values():
                if isinstance(variante, dict) and variante.get("market"):
                    preco = variante["market"]
                    break
            candidatos.append({
                "titulo": carta.get("name", nome),
                "edicao": (carta.get("set") or {}).get("name", ""),
                "imagem_url": imagens.get("large"),
                "thumb_url": imagens.get("small") or imagens.get("large"),
                "raridade": carta.get("rarity", ""),
                "tipo": ", ".join(carta.get("types") or []) + (f" · HP {carta['hp']}" if carta.get("hp") else ""),
                "preco_referencia": _preco_seguro(preco),
                "preco_moeda": "USD",
            })
        return candidatos
    return _seguro(_fazer)


def _buscar_yugioh(nome):
    def _fazer():
        resp = requests.get(
            "https://db.ygoprodeck.com/api/v7/cardinfo.php",
            params={"fname": nome},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        dados = resp.json().get("data", [])[:3]
        candidatos = []
        for carta in dados:
            imagens = carta.get("card_images") or []
            if not imagens:
                continue
            precos = (carta.get("card_prices") or [{}])[0]
            sets = carta.get("card_sets") or []
            raridade = sets[0].get("set_rarity", "") if sets else ""
            atk_def = ""
            if "atk" in carta:
                atk_def = f"ATK {carta.get('atk')} / DEF {carta.get('def', '?')}"
            candidatos.append({
                "titulo": carta.get("name", nome),
                "edicao": carta.get("type", ""),
                "imagem_url": imagens[0].get("image_url"),
                "thumb_url": imagens[0].get("image_url_small") or imagens[0].get("image_url"),
                "raridade": raridade,
                "tipo": atk_def or carta.get("race", ""),
                "preco_referencia": _preco_seguro(precos.get("tcgplayer_price")),
                "preco_moeda": "USD",
            })
        return candidatos
    return _seguro(_fazer)


BUSCADORES = {
    "magic": _buscar_magic,
    "pokemon": _buscar_pokemon,
    "yugioh": _buscar_yugioh,
}


def buscar_candidatos_imagem(nome, jogo):
    """Devolve até 3 candidatos de imagem {titulo, edicao, imagem_url, thumb_url}."""
    buscador = BUSCADORES.get(jogo)
    if not buscador or not nome:
        return []
    return buscador(nome.strip())


def buscar_por_codigo_barras(codigo):
    """
    Busca imagem de produto LACRADO (booster box, blister, ETB, etc)
    pelo código de barras (UPC/EAN), via UPCitemdb — banco de dados
    de produtos por código de barras, gratuito, sem precisar de
    cadastro/chave (100 consultas grátis por dia por IP).
    Muito mais preciso que buscar por nome pra esse tipo de produto,
    já que não existe um "banco de dados de cartas" pra embalagens.
    """
    def _fazer():
        if not codigo or not codigo.strip():
            return []
        resp = requests.get(
            "https://api.upcitemdb.com/prod/trial/lookup",
            params={"upc": codigo.strip()},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        itens = resp.json().get("items", [])[:1]  # UPC é um código exato, só tem 1 produto de verdade
        candidatos = []
        for item in itens:
            imagens = item.get("images") or []
            titulo = item.get("title", "")
            marca = item.get("brand", "")
            for img_url in imagens[:3]:
                candidatos.append({
                    "titulo": titulo,
                    "edicao": marca,
                    "imagem_url": img_url,
                    "thumb_url": img_url,
                })
        return candidatos
    return _seguro(_fazer)


def baixar_imagem(url):
    """Baixa os bytes de uma imagem já escolhida pelo usuário. Devolve None se falhar."""
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.content:
            return resp.content
    except requests.RequestException:
        pass
    return None
