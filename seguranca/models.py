from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models


class Area(models.Model):
    """Uma 'tela'/seção do sistema, usada pra controlar o que cada perfil pode acessar."""
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=80)

    class Meta:
        verbose_name = "Área do sistema"
        verbose_name_plural = "Áreas do sistema"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class PerfilAcesso(models.Model):
    """
    Liga um Grupo (perfil, ex: 'Financeiro', 'Estoquista') às áreas
    do sistema que esse perfil pode acessar. Editável em Admin →
    Grupos, sem precisar mexer em código.
    """
    grupo = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="perfil_acesso")
    areas = models.ManyToManyField(Area, blank=True)
    acesso_total = models.BooleanField(
        "Acesso total (todas as áreas, inclusive futuras)", default=False
    )

    class Meta:
        verbose_name = "Perfil de acesso"
        verbose_name_plural = "Perfis de acesso"

    def __str__(self):
        return f"Perfil de acesso — {self.grupo.name}"


class SessaoAtiva(models.Model):
    """Uma sessão de login ativa — pra você ver quem está logado agora, de onde, e derrubar se precisar."""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessoes_ativas"
    )
    session_key = models.CharField(max_length=40, unique=True)
    ip = models.CharField(max_length=45, blank=True)
    dispositivo = models.CharField(max_length=255, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    ultima_atividade = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sessão ativa"
        verbose_name_plural = "Sessões ativas"
        ordering = ["-ultima_atividade"]

    def __str__(self):
        return f"{self.usuario} — {self.ip} ({self.ultima_atividade:%d/%m %H:%M})"


class IPBloqueado(models.Model):
    """IPs banidos manualmente — qualquer requisição vinda daqui é recusada."""
    ip = models.CharField(max_length=45, unique=True, db_index=True)
    motivo = models.CharField(max_length=200, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "IP bloqueado"
        verbose_name_plural = "IPs bloqueados"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.ip} — {self.motivo or 'sem motivo informado'}"


class DoisFatores(models.Model):
    """Configuração de autenticação em duas etapas (TOTP) por usuário."""
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dois_fatores"
    )
    secret = models.CharField(max_length=32)
    ativado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Autenticação em duas etapas"
        verbose_name_plural = "Autenticação em duas etapas"

    def __str__(self):
        status = "ativado" if self.ativado else "não ativado"
        return f"2FA de {self.usuario} ({status})"


class TentativaLogin(models.Model):
    """
    Histórico de tentativas de login — usado pra bloquear
    temporariamente depois de muitas tentativas erradas seguidas
    (proteção contra força bruta).
    """
    username = models.CharField(max_length=150)
    ip = models.CharField(max_length=45, blank=True)
    sucesso = models.BooleanField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tentativa de login"
        verbose_name_plural = "Tentativas de login"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.username} — {'ok' if self.sucesso else 'falhou'} ({self.criado_em:%d/%m %H:%M})"
