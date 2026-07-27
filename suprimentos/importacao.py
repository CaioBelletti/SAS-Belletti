"""
Importação de estoque a partir de print, PDF ou .txt.

Fluxo: extrai texto bruto do arquivo (OCR pra imagem, leitura direta
pra PDF/txt), depois tenta interpretar as linhas como itens de compra
(nome, quantidade, valor). O resultado é sempre tratado como um
RASCUNHO — a pessoa confere e corrige na tela de preview antes de
qualquer coisa virar Ordem de compra de verdade.
"""
import io
import re
from decimal import Decimal, InvalidOperation

EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class ExtracaoNaoSuportadaError(Exception):
    pass


def extrair_texto(arquivo_django):
    """Recebe um InMemoryUploadedFile do Django e devolve o texto bruto."""
    nome = arquivo_django.name.lower()
    conteudo = arquivo_django.read()

    if nome.endswith(".txt"):
        for encoding in ("utf-8", "latin-1"):
            try:
                return conteudo.decode(encoding)
            except UnicodeDecodeError:
                continue
        return conteudo.decode("utf-8", errors="ignore")

    if nome.endswith(".pdf"):
        import pdfplumber

        texto_paginas = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for pagina in pdf.pages:
                texto_paginas.append(pagina.extract_text() or "")
        return "\n".join(texto_paginas)

    if any(nome.endswith(ext) for ext in EXTENSOES_IMAGEM):
        import os

        import pytesseract
        from PIL import Image

        caminho_customizado = os.environ.get("TESSERACT_CMD")
        if caminho_customizado:
            pytesseract.pytesseract.tesseract_cmd = caminho_customizado

        imagem = Image.open(io.BytesIO(conteudo))
        return pytesseract.image_to_string(imagem, lang="por+eng")

    raise ExtracaoNaoSuportadaError(
        "Formato não suportado. Envie um arquivo .txt, .pdf, .png, .jpg ou .webp."
    )


# Valor com indício real de moeda: prefixo R$/$, ou formato decimal
# (vírgula/ponto + 2 casas). Um número solto como "1" ou "2" NUNCA
# conta como valor — isso quase sempre é a quantidade vazando pra
# dentro do valor.
_PADRAO_VALOR = re.compile(
    r"R?\$\s?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})|"
    r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})"
)
_PADRAO_VALOR_FINAL = re.compile(
    r"(?:R?\$\s?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})|"
    r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2}))\s*$"
)
_PADRAO_VALOR_PURO = re.compile(
    r"^R?\$\s?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})$|"
    r"^(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})$"
)
# Quantidade no final da linha: "x 1", "x1", "× 2" (o × costuma virar
# "x" depois do OCR), ou — como fallback — um número pequeno solto no
# final (o OCR às vezes engole o "x" e sobra só o número).
_PADRAO_QTD_FINAL = re.compile(r"[x×]\s*(\d{1,4})\s*$|(?:^|\s)(\d{1,2})\s*$", re.IGNORECASE)

# Linhas que são só ruído de cabeçalho/rodapé/navegador — não são item.
_LINHAS_IGNORADAS = {
    "produto", "total", "produto total", "detalhes do pedido",
    "atualizações do pedido", "painel", "pedidos", "endereços",
    "detalhes da conta", "sair",
}


def _normalizar_valor(bruto: str) -> Decimal:
    bruto = bruto.strip().replace("R$", "").replace("$", "").strip()
    if "," in bruto and "." in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif "," in bruto:
        bruto = bruto.replace(",", ".")
    try:
        return Decimal(bruto)
    except InvalidOperation:
        return Decimal("0")


def _tem_qtd_final(linha):
    return _PADRAO_QTD_FINAL.search(linha) is not None


def _tem_valor(linha):
    return _PADRAO_VALOR_FINAL.search(linha) is not None


def _eh_valor_puro(linha):
    return _PADRAO_VALOR_PURO.match(linha) is not None


def _extrair_qtd_do_final(texto):
    match = _PADRAO_QTD_FINAL.search(texto)
    if not match:
        return texto.strip(), 1
    grupo = match.group(1) or match.group(2)
    try:
        quantidade = max(int(grupo), 1)
    except (ValueError, TypeError):
        quantidade = 1
    return texto[: match.start()].strip(), quantidade


def _limpar_nome(texto):
    return re.sub(r"\s{2,}", " ", texto).strip(" -–—:xX")


def parse_linhas(texto: str):
    """
    Devolve uma lista de dicts {nome, quantidade, valor_total}.

    Passo 1 — junta fragmentos: nomes de produto que o OCR quebrou em
    2+ linhas (comum quando o nome é longo) são unidos até encontrar
    uma linha "de fechamento" (com quantidade e/ou valor).

    Passo 2 — cobre dois formatos de print:
    a) nome + quantidade + valor tudo na mesma linha visual final;
    b) nome/quantidade de um lado e uma lista de valores separada
       (acontece quando o print é recortado só na tabela) — nesse
       caso só pareia se a quantidade de blocos bater exatamente com
       a quantidade de valores soltos, pra nunca arriscar casar errado.
    """
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    linhas = [l for l in linhas if l.lower() not in _LINHAS_IGNORADAS and len(l) >= 2]

    # --- Passo 1: junta fragmentos quebrados em várias linhas -------------------
    entradas = []  # lista de ("linha", texto_mesclado) ou ("valor_puro", Decimal)
    buffer = []
    for linha in linhas:
        if _eh_valor_puro(linha):
            valor = _normalizar_valor(linha)
            if valor > 0:
                entradas.append(("valor_puro", valor))
            continue

        if _tem_valor(linha) or _tem_qtd_final(linha):
            texto_mesclado = " ".join(buffer + [linha]).strip()
            buffer = []
            entradas.append(("linha", texto_mesclado))
        else:
            buffer.append(linha)
            buffer = buffer[-2:]  # nomes reais não quebram em mais de 2 linhas
    # fragmento que nunca fechou (sobrou no buffer) — descarta, não dá pra saber

    # --- Passo 2a: linhas completas (nome + quantidade + valor) -----------------
    itens = []
    blocos_sem_valor = []

    for tipo, conteudo in entradas:
        if tipo == "valor_puro":
            continue

        match_valor = _PADRAO_VALOR_FINAL.search(conteudo)
        if match_valor:
            valor_bruto = match_valor.group(1) or match_valor.group(2)
            valor = _normalizar_valor(valor_bruto)
            resto = conteudo[: match_valor.start()].strip()
            nome, quantidade = _extrair_qtd_do_final(resto)
            nome = _limpar_nome(nome)
            if nome and valor > 0:
                itens.append({"nome": nome, "quantidade": quantidade, "valor_total": valor})
        else:
            nome, quantidade = _extrair_qtd_do_final(conteudo)
            nome = _limpar_nome(nome)
            if nome:
                blocos_sem_valor.append({"nome": nome, "quantidade": quantidade})

    # --- Passo 2b: pareia blocos sem valor com valores soltos, só se a
    # contagem bater certinho (senão não arrisca casar errado) ------------------
    valores_soltos = [valor for tipo, valor in entradas if tipo == "valor_puro"]
    if blocos_sem_valor and len(blocos_sem_valor) == len(valores_soltos):
        for bloco, valor in zip(blocos_sem_valor, valores_soltos):
            itens.append({
                "nome": bloco["nome"],
                "quantidade": bloco["quantidade"],
                "valor_total": valor,
            })

    return itens
