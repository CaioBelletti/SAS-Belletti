"""Validação RC10 em homologação: dados sintéticos VAL-RC10 (setup / cleanup por IDs exatos).
Uso: VAL_RC10_ACTION=setup|cleanup python manage.py shell < scripts/val_rc10.py
Nada ocorre sem BELLETTI_HOMOLOGACAO=1. Nunca imprime a senha."""
import json, os, uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

action = os.environ.get("VAL_RC10_ACTION", "none")
if action != "none":
    if os.environ.get("BELLETTI_HOMOLOGACAO") != "1":
        raise RuntimeError("somente homologação")
    from cozinha.models import CategoriaPrato, Prato, Mesa, PedidoCozinha, ChamadoAtendente, Comanda, RequisicaoPedido
    from seguranca.models import Area, PerfilAcesso, TentativaLogin, SessaoAtiva
    User = get_user_model()
    TAG = "VAL-RC10"
    MESA_NUM = 9910
    MESA_TOKEN = uuid.UUID("5a1c0de0-0c10-4c10-9c10-000000009910")

    if action == "setup":
        pwd = os.environ["VAL_RC10_PASSWORD"]
        ids = {"users": [], "groups": [], "areas_criadas": []}
        with transaction.atomic():
            def area(cod, nome):
                a, novo = Area.objects.get_or_create(codigo=cod, defaults={"nome": nome})
                if novo: ids["areas_criadas"].append(a.pk)
                return a
            def perfil(nome, total=False, areas=()):
                g = Group.objects.create(name=f"{TAG} {nome}")
                p = PerfilAcesso.objects.create(grupo=g, acesso_total=total)
                p.areas.set([area(c, c) for c in areas])
                ids["groups"].append(g.pk)
                return g
            def usuario(nome, grupo, staff):
                assert not User.objects.filter(username=nome).exists()
                u = User.objects.create_user(nome, password=pwd, is_staff=staff)
                u.groups.add(grupo); ids["users"].append(u.pk)
            usuario("val_rc10_admin", perfil("Gerente", total=True), True)
            usuario("val_rc10_cozinha", perfil("Cozinha", areas=["cozinha"]), True)
            usuario("val_rc10_garcom", perfil("Garcom", areas=["cozinha"]), True)
            usuario("val_rc10_vendas", perfil("Vendas", areas=["pdv"]), False)
            cat = CategoriaPrato.objects.create(nome=f"{TAG} Categoria")
            prato = Prato.objects.create(nome=f"{TAG} Prato", preco=Decimal("10.00"), categoria=cat)
            mesa = Mesa.objects.create(numero=MESA_NUM, token_publico=MESA_TOKEN)
            ids.update(categoria=cat.pk, prato=prato.pk, mesa=mesa.pk, mesa_token=str(MESA_TOKEN))
        print("VAL_RC10_IDS=" + json.dumps(ids))

    elif action == "cleanup":
        ids = json.loads(os.environ["VAL_RC10_IDS"])
        ped, cha, com, req = ids.get("pedidos", []), ids.get("chamados", []), ids.get("comandas", []), ids.get("requisicoes", [])
        with transaction.atomic():
            mesa = Mesa.objects.get(pk=ids["mesa"], numero=MESA_NUM, token_publico=MESA_TOKEN)
            # defesa: tudo que existe na mesa de teste precisa estar na lista de IDs exatos
            assert set(PedidoCozinha.objects.filter(mesa=mesa).values_list("pk", flat=True)) <= set(ped)
            assert set(ChamadoAtendente.objects.filter(mesa=mesa).values_list("pk", flat=True)) <= set(cha)
            assert set(Comanda.objects.filter(mesa=mesa).values_list("pk", flat=True)) <= set(com)
            n = {}
            n["pedidos"] = PedidoCozinha.objects.filter(pk__in=ped, mesa=mesa, nome_para_chamar__startswith=TAG).delete()[0]
            n["chamados"] = ChamadoAtendente.objects.filter(pk__in=cha, mesa=mesa).delete()[0]
            n["comandas"] = Comanda.objects.filter(pk__in=com, mesa=mesa).delete()[0]
            n["requisicoes"] = RequisicaoPedido.objects.filter(chave__in=req).delete()[0]
            n["mesa"] = Mesa.objects.filter(pk=mesa.pk).delete()[0]
            n["prato"] = Prato.objects.filter(pk=ids["prato"], nome=f"{TAG} Prato").delete()[0]
            n["categoria"] = CategoriaPrato.objects.filter(pk=ids["categoria"], nome=f"{TAG} Categoria").delete()[0]
            users = User.objects.filter(pk__in=ids["users"], username__startswith="val_rc10_")
            names = list(users.values_list("username", flat=True))
            n["tentativas"] = TentativaLogin.objects.filter(username__in=names).delete()[0]
            n["usuarios"] = users.delete()[0]
            n["grupos"] = Group.objects.filter(pk__in=ids["groups"], name__startswith=f"{TAG} ").delete()[0]
            n["areas"] = Area.objects.filter(pk__in=ids.get("areas_criadas", [])).delete()[0]
        print("VAL_RC10_CLEANUP=" + json.dumps(n))
