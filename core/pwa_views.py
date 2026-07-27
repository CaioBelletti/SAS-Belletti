from django.conf import settings
from django.http import HttpResponse


def sw_view(request):
    """Serve o service worker na raiz do site (não em /static/), pra ele poder controlar o site inteiro."""
    caminho = settings.BASE_DIR / "static" / "sw.js"
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
    response = HttpResponse(conteudo, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
