import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.adapters.stripe.stripe_adapter import StripeAdapter, StripeConfiguracaoInvalidaError
from app.core.config import Settings
from app.core.persistencia.models.assinatura import Assinatura
from app.core.service.assinatura_service import (
    AssinaturaInvalidaError,
    AssinaturaService,
    StripeEventoEmProcessamentoError,
    StripeEventoInvalidoError,
)


class FakeRepository:
    def __init__(self):
        self.assinatura = None
        self.evento_reservado = True
        self.salvas = []
        self.evento_estado = None

    def buscar_por_usuario(self, _user_id):
        if self.assinatura and self.assinatura.id_usuario == _user_id:
            return self.assinatura
        return None

    def bloquear_usuario(self, _user_id):
        return None

    def buscar_por_subscription(self, _subscription_id):
        if self.assinatura and self.assinatura.stripe_subscription_id == _subscription_id:
            return self.assinatura
        return None

    def buscar_por_checkout(self, _session_id):
        if self.assinatura and self.assinatura.stripe_checkout_session_id == _session_id:
            return self.assinatura
        return None

    def buscar_por_customer(self, _customer_id):
        if self.assinatura and self.assinatura.stripe_customer_id == _customer_id:
            return self.assinatura
        return None

    def buscar_usuario(self, _user_id):
        return self.usuario

    def salvar(self, assinatura):
        self.assinatura = assinatura
        self.salvas.append(assinatura)
        return assinatura

    def salvar_com_usuario(self, assinatura, _usuario):
        return self.salvar(assinatura)

    def reservar_evento(self, _event_id, _event_type):
        return self.evento_reservado

    def finalizar_evento(self, _event_id, state):
        self.evento_estado = state


class FakeDatabase:
    def __init__(self):
        self.rollback_count = 0

    def rollback(self):
        self.rollback_count += 1


def build_service(monkeypatch, adapter, repository, settings=None):
    monkeypatch.setattr(
        "app.core.service.assinatura_service.AssinaturaRepository",
        lambda _db: repository,
    )
    return AssinaturaService(FakeDatabase(), adapter, settings or Settings())


def test_checkout_cria_sessao_com_preco_configurado(monkeypatch):
    adapter = SimpleNamespace(
        criar_checkout=lambda **kwargs: {
            "id": "cs_test_123",
            "url": "https://checkout.stripe.test/session",
            "customer": None,
        }
    )
    repository = FakeRepository()
    user = SimpleNamespace(id_usuario=uuid.uuid4(), email="demo@example.com", plano_codigo="free")
    settings = Settings(stripe_price_pro="price_pro_test")
    service = build_service(monkeypatch, adapter, repository, settings)

    url = service.iniciar_checkout(user, "pro")

    assert url == "https://checkout.stripe.test/session"
    assert repository.assinatura.stripe_checkout_session_id == "cs_test_123"
    assert repository.assinatura.checkout_plano_codigo == "pro"
    assert repository.assinatura.status == "checkout_started"


def test_checkout_nao_cria_assinatura_duplicada(monkeypatch):
    repository = FakeRepository()
    repository.assinatura = Assinatura(
        id_usuario=uuid.uuid4(),
        plano_codigo="pro",
        status="active",
        stripe_subscription_id="sub_active",
    )
    service = build_service(monkeypatch, SimpleNamespace(), repository, Settings(stripe_price_max="price_max"))
    user = SimpleNamespace(id_usuario=repository.assinatura.id_usuario, email="a@example.com", plano_codigo="pro")

    with pytest.raises(AssinaturaInvalidaError, match="já possui uma assinatura"):
        service.iniciar_checkout(user, "max")


def test_upgrade_sincroniza_imediatamente_assinatura_atualizada(monkeypatch):
    repository = FakeRepository()
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="pro")
    repository.usuario = user
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        plano_codigo="pro",
        plano_pendente_codigo="free",
        status="active",
        stripe_subscription_id="sub_upgrade",
    )
    subscription = {
        "id": "sub_upgrade",
        "customer": "cus_upgrade",
        "status": "active",
        "current_period_start": 100,
        "current_period_end": 200,
        "items": {"data": [{"price": {"id": "price_max_test"}}]},
        "metadata": {"user_id": str(user_id)},
    }
    adapter = SimpleNamespace(
        alterar_plano_imediatamente=lambda subscription_id, price_id: subscription
    )
    service = build_service(
        monkeypatch,
        adapter,
        repository,
        Settings(stripe_price_pro="price_pro_test", stripe_price_max="price_max_test"),
    )

    mensagem = service.alterar_plano(user, "max")

    assert mensagem == "Upgrade confirmado e plano atualizado."
    assert user.plano_codigo == "max"
    assert repository.assinatura.plano_codigo == "max"
    assert repository.assinatura.plano_pendente_codigo is None
    assert repository.assinatura.stripe_schedule_id is None


def test_upgrade_pendente_mantem_plano_anterior(monkeypatch):
    repository = FakeRepository()
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="pro")
    repository.usuario = user
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        plano_codigo="pro",
        status="active",
        stripe_subscription_id="sub_upgrade_pending",
    )
    subscription = {
        "id": "sub_upgrade_pending",
        "customer": "cus_upgrade_pending",
        "status": "active",
        "current_period_start": 100,
        "current_period_end": 200,
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
        "pending_update": {"expires_at": 200},
    }
    service = build_service(
        monkeypatch,
        SimpleNamespace(alterar_plano_imediatamente=lambda _subscription_id, _price_id: subscription),
        repository,
        Settings(stripe_price_pro="price_pro_test", stripe_price_max="price_max_test"),
    )

    mensagem = service.alterar_plano(user, "max")

    assert mensagem == "O pagamento do upgrade ainda está pendente; seu plano atual não foi alterado."
    assert user.plano_codigo == "pro"
    assert repository.assinatura.plano_codigo == "pro"


def test_reducao_de_plano_e_agendada_para_o_proximo_ciclo(monkeypatch):
    repository = FakeRepository()
    repository.assinatura = Assinatura(
        id_usuario=uuid.uuid4(),
        plano_codigo="max",
        status="active",
        stripe_subscription_id="sub_downgrade",
    )
    adapter = SimpleNamespace(
        agendar_reducao_plano=lambda subscription_id, price_id: {
            "id": f"schedule:{subscription_id}:{price_id}"
        }
    )
    service = build_service(
        monkeypatch,
        adapter,
        repository,
        Settings(stripe_price_pro="price_pro_test"),
    )

    mensagem = service.alterar_plano(
        SimpleNamespace(id_usuario=repository.assinatura.id_usuario),
        "pro",
    )

    assert mensagem == "A redução do plano foi agendada para o fim do ciclo atual."
    assert repository.assinatura.plano_pendente_codigo == "pro"
    assert repository.assinatura.stripe_schedule_id == "schedule:sub_downgrade:price_pro_test"


def test_chave_live_e_bloqueada_quando_modo_e_teste():
    adapter = StripeAdapter(Settings(stripe_mode="test", stripe_secret_key="sk_live_secret"))

    with pytest.raises(StripeConfiguracaoInvalidaError, match="não corresponde"):
        adapter.criar_portal("cus_test")


def test_periodo_stripe_suporta_datas_no_item_da_assinatura():
    period = StripeAdapter._periodo_atual(
        {"items": {"data": [{"current_period_start": 100, "current_period_end": 200}]}}
    )

    assert period == (100, 200)


def test_evento_webhook_repetido_e_ignorado(monkeypatch):
    repository = FakeRepository()
    repository.evento_reservado = False
    adapter = SimpleNamespace(obter_assinatura=lambda _subscription_id: pytest.fail("não deve consultar Stripe"))
    service = build_service(monkeypatch, adapter, repository)

    processado = service.processar_evento(
        {"id": "evt_duplicate", "type": "customer.subscription.updated", "data": {"object": {}}}
    )

    assert not processado
    assert repository.evento_estado is None


def test_webhook_repetido_durante_processamento_pede_tentativa_posterior(monkeypatch):
    repository = FakeRepository()
    repository.evento_reservado = None
    service = build_service(monkeypatch, SimpleNamespace(), repository)

    with pytest.raises(StripeEventoEmProcessamentoError):
        service.processar_evento(
            {"id": "evt_processing", "type": "customer.subscription.updated", "data": {"object": {}}}
        )


def test_upgrade_concede_nova_janela_de_cota_completa(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="pro")
    repository = FakeRepository()
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        plano_codigo="pro",
        status="active",
        stripe_subscription_id="sub_upgrade",
    )
    repository.usuario = user
    period_end = int((datetime.now(timezone.utc) + timedelta(days=20)).timestamp())
    subscription = {
        "id": "sub_upgrade",
        "customer": "cus_demo",
        "status": "active",
        "current_period_start": int((datetime.now(timezone.utc) - timedelta(days=10)).timestamp()),
        "current_period_end": period_end,
        "items": {"data": [{"price": {"id": "price_max_test"}}]},
        "metadata": {"user_id": str(user_id)},
    }
    adapter = SimpleNamespace(obter_assinatura=lambda _subscription_id: subscription)
    settings = Settings(stripe_price_pro="price_pro_test", stripe_price_max="price_max_test")
    service = build_service(monkeypatch, adapter, repository, settings)

    processed = service.processar_evento(
        {
            "id": "evt_upgrade",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_upgrade"}},
        }
    )

    assert processed
    assert user.plano_codigo == "max"
    assert repository.assinatura.inicio_cota is not None
    assert repository.assinatura.inicio_cota > repository.assinatura.periodo_inicio
    assert repository.assinatura.fim_cota == repository.assinatura.periodo_fim
    assert repository.evento_estado == "processed"


def test_refresh_sincroniza_checkout_pago_sem_webhook(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="free")
    repository = FakeRepository()
    checkout_pendente = Assinatura(
        id_usuario=user_id,
        status="checkout_started",
        checkout_plano_codigo="pro",
        stripe_checkout_session_id="cs_paid",
    )
    repository.assinatura = checkout_pendente
    repository.usuario = user
    subscription = {
        "id": "sub_paid",
        "customer": "cus_demo",
        "status": "active",
        "current_period_start": 100,
        "current_period_end": 200,
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
        "metadata": {"user_id": str(user_id)},
    }
    adapter = SimpleNamespace(
        obter_checkout=lambda session_id: {
            "id": session_id,
            "status": "complete",
            "payment_status": "paid",
            "mode": "subscription",
            "client_reference_id": str(user_id),
            "subscription": "sub_paid",
        },
        obter_assinatura=lambda _subscription_id: subscription,
    )
    service = build_service(
        monkeypatch,
        adapter,
        repository,
        Settings(stripe_price_pro="price_pro_test"),
    )

    synced = service.sincronizar_checkout_pendente(user)

    assert synced
    assert repository.assinatura is checkout_pendente
    assert user.plano_codigo == "pro"
    assert repository.assinatura.status == "active"
    assert repository.assinatura.checkout_plano_codigo is None


def test_refresh_sincroniza_upgrade_pago_que_aguardava_webhook(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="max")
    repository = FakeRepository()
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        stripe_customer_id="cus_upgrade",
        stripe_subscription_id="sub_upgrade",
        plano_codigo="max",
        status="active",
    )
    repository.usuario = user
    subscription = {
        "id": "sub_upgrade",
        "customer": "cus_upgrade",
        "status": "active",
        "current_period_start": 100,
        "current_period_end": 200,
        "items": {"data": [{"price": {"id": "price_ultimate_test"}}]},
        "metadata": {"user_id": str(user_id)},
    }
    service = build_service(
        monkeypatch,
        SimpleNamespace(obter_assinatura=lambda _subscription_id: subscription),
        repository,
        Settings(
            stripe_price_pro="price_pro_test",
            stripe_price_max="price_max_test",
            stripe_price_ultimate="price_ultimate_test",
        ),
    )

    synced = service.sincronizar_assinatura_atual(user)

    assert synced
    assert user.plano_codigo == "ultimate"
    assert repository.assinatura.plano_codigo == "ultimate"


def test_assinatura_ativa_com_preco_nao_configurado_nao_sincroniza_como_sucesso(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="free")
    repository = FakeRepository()
    repository.usuario = user
    subscription = {
        "id": "sub_unknown_price",
        "customer": "cus_unknown_price",
        "status": "active",
        "current_period_start": 100,
        "current_period_end": 200,
        "items": {"data": [{"price": {"id": "price_not_configured"}}]},
        "metadata": {"user_id": str(user_id)},
    }
    service = build_service(
        monkeypatch,
        SimpleNamespace(obter_assinatura=lambda _subscription_id: subscription),
        repository,
        Settings(stripe_price_pro="price_pro_test"),
    )

    with pytest.raises(StripeEventoInvalidoError, match="não corresponde a um plano configurado"):
        service.processar_evento(
            {
                "id": "evt_unknown_price",
                "type": "customer.subscription.updated",
                "data": {"object": {"id": "sub_unknown_price"}},
            }
        )

    assert repository.assinatura is None
    assert user.plano_codigo == "free"
    assert repository.evento_estado == "failed"
    assert service.db.rollback_count == 1


def test_evento_de_assinatura_antiga_nao_substitui_assinatura_atual(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="max")
    repository = FakeRepository()
    repository.usuario = user
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        stripe_customer_id="cus_reused",
        stripe_subscription_id="sub_current",
        plano_codigo="max",
        status="active",
    )
    old_subscription = {
        "id": "sub_old",
        "customer": "cus_reused",
        "status": "canceled",
        "metadata": {"user_id": str(user_id)},
    }
    service = build_service(
        monkeypatch,
        SimpleNamespace(obter_assinatura=lambda _subscription_id: old_subscription),
        repository,
        Settings(stripe_price_max="price_max_test"),
    )

    service._sincronizar_assinatura("sub_old")
    service._revogar_assinatura(old_subscription)

    assert repository.assinatura.stripe_subscription_id == "sub_current"
    assert repository.assinatura.status == "active"
    assert user.plano_codigo == "max"


def test_evento_da_assinatura_anterior_preserva_checkout_novo_pendente(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id_usuario=user_id, plano_codigo="free")
    repository = FakeRepository()
    repository.usuario = user
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        stripe_customer_id="cus_reused",
        stripe_subscription_id="sub_previous",
        stripe_checkout_session_id="cs_new",
        checkout_plano_codigo="pro",
        plano_codigo="free",
        status="checkout_started",
    )
    subscription = {
        "id": "sub_previous",
        "customer": "cus_reused",
        "status": "canceled",
    }
    service = build_service(
        monkeypatch,
        SimpleNamespace(obter_assinatura=lambda _subscription_id: subscription),
        repository,
    )

    service._revogar_assinatura(subscription)
    service._sincronizar_assinatura("sub_previous")

    assert repository.assinatura.status == "checkout_started"
    assert repository.assinatura.stripe_checkout_session_id == "cs_new"
    assert repository.assinatura.checkout_plano_codigo == "pro"
    assert user.plano_codigo == "free"


def test_checkout_nao_concluido_permanece_pendente(monkeypatch):
    user_id = uuid.uuid4()
    repository = FakeRepository()
    repository.assinatura = Assinatura(
        id_usuario=user_id,
        status="checkout_started",
        stripe_checkout_session_id="cs_open",
    )
    adapter = SimpleNamespace(
        obter_checkout=lambda _session_id: {
            "status": "complete",
            "payment_status": "unpaid",
            "mode": "subscription",
            "client_reference_id": str(user_id),
            "subscription": "sub_pending",
        },
        obter_assinatura=lambda _subscription_id: pytest.fail("não deve sincronizar"),
    )
    service = build_service(monkeypatch, adapter, repository)

    assert not service.sincronizar_checkout_pendente(SimpleNamespace(id_usuario=user_id))
    assert repository.assinatura.status == "checkout_started"
