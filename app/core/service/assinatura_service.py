import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.stripe.stripe_adapter import StripeAdapter, StripeConfiguracaoInvalidaError
from app.core.config import Settings, get_settings
from app.core.persistencia.assinatura_repository import AssinaturaRepository
from app.core.persistencia.models.assinatura import Assinatura
from app.core.persistencia.models.usuario import Usuario

logger = logging.getLogger(__name__)
PLANOS_PAGOS = ("pro", "max", "ultimate")
ORDEM_PLANOS = {"free": 0, "pro": 1, "max": 2, "ultimate": 3}
EVENTOS_PROCESSADOS = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "charge.refunded",
    "charge.dispute.created",
}


class AssinaturaInvalidaError(Exception):
    pass


class StripeEventoInvalidoError(Exception):
    pass


class StripeEventoEmProcessamentoError(Exception):
    pass


class AssinaturaService:
    def __init__(
        self,
        db: Session,
        stripe_adapter: StripeAdapter | None = None,
        settings: Settings | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.stripe = stripe_adapter or StripeAdapter(self.settings)
        self.repository = AssinaturaRepository(db)

    def iniciar_checkout(self, usuario: Usuario, plano_codigo: str) -> str:
        if plano_codigo not in PLANOS_PAGOS:
            raise AssinaturaInvalidaError("Escolha um plano pago válido.")
        price_id = self.settings.stripe_price_ids.get(plano_codigo)
        if not price_id:
            raise StripeConfiguracaoInvalidaError(f"STRIPE_PRICE_{plano_codigo.upper()} não foi configurado.")

        self.repository.bloquear_usuario(usuario.id_usuario)
        assinatura = self.repository.buscar_por_usuario(usuario.id_usuario)
        if assinatura and assinatura.status in {"active", "trialing", "past_due", "unpaid"}:
            raise AssinaturaInvalidaError("Você já possui uma assinatura. Use a opção de alterar plano.")
        if assinatura and assinatura.status == "incomplete" and assinatura.stripe_subscription_id:
            raise AssinaturaInvalidaError("Seu pagamento está sendo confirmado. Acesse o portal para regularizá-lo.")

        if assinatura and assinatura.status == "checkout_started" and assinatura.stripe_checkout_session_id:
            checkout = self.stripe.obter_checkout(assinatura.stripe_checkout_session_id)
            if checkout["status"] == "open":
                if assinatura.checkout_plano_codigo and assinatura.checkout_plano_codigo != plano_codigo:
                    raise AssinaturaInvalidaError(
                        "Há um checkout aberto para outro plano; retome esse pagamento antes de escolher outro."
                    )
                return checkout["url"]
            if checkout["status"] == "complete":
                raise AssinaturaInvalidaError("Seu pagamento está sendo confirmado. Atualize a página em instantes.")

        checkout = self.stripe.criar_checkout(
            price_id=price_id,
            user_id=str(usuario.id_usuario),
            email=usuario.email,
            customer_id=assinatura.stripe_customer_id if assinatura else None,
        )
        if assinatura is None:
            assinatura = Assinatura(
                id_usuario=usuario.id_usuario,
                plano_codigo=usuario.plano_codigo,
            )
        assinatura.status = "checkout_started"
        assinatura.checkout_plano_codigo = plano_codigo
        assinatura.stripe_checkout_session_id = checkout["id"]
        if checkout.get("customer"):
            assinatura.stripe_customer_id = self._id_expandido(checkout["customer"])
        self.repository.salvar(assinatura)
        return checkout["url"]

    def criar_portal(self, usuario: Usuario) -> str:
        assinatura = self.repository.buscar_por_usuario(usuario.id_usuario)
        if not assinatura or not assinatura.stripe_customer_id:
            raise AssinaturaInvalidaError("Ainda não há uma assinatura Stripe para esta conta.")
        return self.stripe.criar_portal(assinatura.stripe_customer_id)["url"]

    def sincronizar_checkout_pendente(self, usuario: Usuario) -> bool:
        assinatura = self.repository.buscar_por_usuario(usuario.id_usuario)
        if (
            not assinatura
            or assinatura.status != "checkout_started"
            or not assinatura.stripe_checkout_session_id
        ):
            return False

        checkout = self.stripe.obter_checkout(assinatura.stripe_checkout_session_id)
        if checkout.get("status") == "expired":
            assinatura.status = "checkout_expired"
            assinatura.checkout_plano_codigo = None
            self.repository.salvar(assinatura)
            return False
        if (
            checkout.get("status") != "complete"
            or checkout.get("payment_status") not in {"paid", "no_payment_required"}
        ):
            return False
        if (
            checkout.get("mode") != "subscription"
            or checkout.get("client_reference_id") != str(usuario.id_usuario)
        ):
            raise StripeEventoInvalidoError("A sessão Stripe não corresponde a esta conta ou assinatura.")

        subscription_id = self._id_expandido(checkout.get("subscription"))
        if not subscription_id:
            raise StripeEventoInvalidoError("A sessão Stripe concluída não contém uma assinatura.")
        self._sincronizar_assinatura(subscription_id, str(usuario.id_usuario))
        return True

    def sincronizar_assinatura_atual(self, usuario: Usuario) -> bool:
        assinatura = self.repository.buscar_por_usuario(usuario.id_usuario)
        if (
            not assinatura
            or not assinatura.stripe_subscription_id
            or assinatura.status == "checkout_started"
        ):
            return False
        self._sincronizar_assinatura(assinatura.stripe_subscription_id)
        return True

    def alterar_plano(self, usuario: Usuario, plano_codigo: str) -> str:
        if plano_codigo not in PLANOS_PAGOS:
            raise AssinaturaInvalidaError("Escolha um plano pago válido.")
        price_id = self.settings.stripe_price_ids.get(plano_codigo)
        if not price_id:
            raise StripeConfiguracaoInvalidaError(f"STRIPE_PRICE_{plano_codigo.upper()} não foi configurado.")
        assinatura = self.repository.buscar_por_usuario(usuario.id_usuario)
        if (
            not assinatura
            or not assinatura.stripe_subscription_id
            or assinatura.status not in {"active", "trialing"}
        ):
            raise AssinaturaInvalidaError("Não há assinatura ativa para alterar.")
        if assinatura.plano_codigo == plano_codigo:
            raise AssinaturaInvalidaError("Este já é o seu plano atual.")

        if ORDEM_PLANOS[plano_codigo] > ORDEM_PLANOS[assinatura.plano_codigo]:
            subscription = self.stripe.alterar_plano_imediatamente(
                assinatura.stripe_subscription_id,
                price_id,
            )
            assinatura.plano_pendente_codigo = None
            assinatura.stripe_schedule_id = None
            self._sincronizar_assinatura(assinatura.stripe_subscription_id, subscription=subscription)
            assinatura_atualizada = self.repository.buscar_por_usuario(usuario.id_usuario)
            if assinatura_atualizada and assinatura_atualizada.plano_codigo == plano_codigo:
                return "Upgrade confirmado e plano atualizado."
            return "O pagamento do upgrade ainda está pendente; seu plano atual não foi alterado."

        schedule = self.stripe.agendar_reducao_plano(assinatura.stripe_subscription_id, price_id)
        assinatura.stripe_schedule_id = schedule["id"]
        assinatura.plano_pendente_codigo = plano_codigo
        self.repository.salvar(assinatura)
        return "A redução do plano foi agendada para o fim do ciclo atual."

    def cancelar_renovacao(self, usuario: Usuario) -> None:
        assinatura = self.repository.buscar_por_usuario(usuario.id_usuario)
        if not assinatura or not assinatura.stripe_subscription_id or assinatura.status not in {
            "active",
            "trialing",
        }:
            raise AssinaturaInvalidaError("Não há assinatura ativa para cancelar.")
        subscription = self.stripe.cancelar_ao_fim_do_ciclo(assinatura.stripe_subscription_id)
        assinatura.cancelamento_agendado = bool(subscription["cancel_at_period_end"])
        assinatura.plano_pendente_codigo = None
        assinatura.stripe_schedule_id = None
        self.repository.salvar(assinatura)

    def processar_evento(self, event: Any) -> bool:
        event_id = self._campo(event, "id")
        event_type = self._campo(event, "type")
        if not event_id or not event_type:
            raise StripeEventoInvalidoError("Evento Stripe sem identificador ou tipo.")
        reserva = self.repository.reservar_evento(event_id, event_type)
        if reserva is False:
            return False
        if reserva is None:
            raise StripeEventoEmProcessamentoError("O evento Stripe ainda está sendo processado.")

        try:
            if event_type in EVENTOS_PROCESSADOS:
                self._processar_evento_assinatura(event_type, self._campo(self._campo(event, "data"), "object"))
            self.repository.finalizar_evento(event_id, "processed")
        except Exception:
            self.db.rollback()
            self.repository.finalizar_evento(event_id, "failed")
            raise
        return True

    def _processar_evento_assinatura(self, event_type: str, objeto: Any) -> None:
        if event_type == "checkout.session.expired":
            session_id = self._campo(objeto, "id")
            assinatura = self.repository.buscar_por_checkout(session_id) if session_id else None
            if assinatura and assinatura.status == "checkout_started":
                assinatura.status = "checkout_expired"
                assinatura.checkout_plano_codigo = None
                self.repository.salvar(assinatura)
            return

        if event_type.startswith("checkout.session."):
            subscription_id = self._id_expandido(self._campo(objeto, "subscription"))
            user_hint = self._campo(objeto, "client_reference_id")
            if subscription_id:
                self._sincronizar_assinatura(subscription_id, user_hint)
            return

        if event_type.startswith("customer.subscription."):
            if event_type == "customer.subscription.deleted":
                self._revogar_assinatura(objeto)
            else:
                self._sincronizar_assinatura(self._campo(objeto, "id"))
            return

        if event_type in {"invoice.paid", "invoice.payment_failed"}:
            subscription_id = self._id_expandido(self._campo(objeto, "subscription"))
            if not subscription_id:
                parent = self._campo(objeto, "parent")
                details = self._campo(parent, "subscription_details")
                subscription_id = self._id_expandido(self._campo(details, "subscription"))
            if subscription_id:
                self._sincronizar_assinatura(subscription_id)
            return

        if event_type == "charge.refunded":
            if self._campo(objeto, "amount_refunded", 0) < self._campo(objeto, "amount", 0):
                return
            invoice_id = self._id_expandido(self._campo(objeto, "invoice"))
            if invoice_id:
                invoice = self.stripe.obter_fatura(invoice_id)
                subscription_id = self._id_expandido(self._campo(invoice, "subscription"))
                if not subscription_id:
                    details = self._campo(self._campo(invoice, "parent"), "subscription_details")
                    subscription_id = self._id_expandido(self._campo(details, "subscription"))
                if subscription_id:
                    subscription = self.stripe.obter_assinatura(subscription_id)
                    if self._campo(subscription, "status") != "canceled":
                        self.stripe.cancelar_imediatamente(subscription_id)
                        subscription = self.stripe.obter_assinatura(subscription_id)
                    self._revogar_assinatura(subscription, "refunded")
            return

        if event_type == "charge.dispute.created":
            logger.warning("Disputa Stripe recebida; não há política de chargeback configurada.")

    def _sincronizar_assinatura(
        self,
        subscription_id: str,
        user_hint: str | None = None,
        subscription: Any | None = None,
    ) -> None:
        if subscription is None:
            subscription = self.stripe.obter_assinatura(subscription_id)
        status = self._campo(subscription, "status", "unknown")
        customer_id = self._id_expandido(self._campo(subscription, "customer"))
        metadata = self._campo(subscription, "metadata", {})
        user_hint = user_hint or self._campo(metadata, "user_id")

        assinatura = self.repository.buscar_por_subscription(subscription_id)
        if assinatura is None and customer_id:
            assinatura = self.repository.buscar_por_customer(customer_id)

        if assinatura is not None:
            id_usuario = assinatura.id_usuario
        else:
            usuario = self._usuario_por_hint(user_hint)
            if usuario is None:
                logger.warning("Assinatura Stripe %s sem usuário local correspondente.", subscription_id)
                return
            id_usuario = usuario.id_usuario

        self.repository.bloquear_usuario(id_usuario)
        assinatura = self.repository.buscar_por_subscription(subscription_id)
        if assinatura is None and customer_id:
            assinatura = self.repository.buscar_por_customer(customer_id)
        if assinatura is None:
            assinatura = self.repository.buscar_por_usuario(id_usuario)
        if assinatura is not None and assinatura.id_usuario != id_usuario:
            raise StripeEventoInvalidoError("A assinatura Stripe está vinculada a outra conta.")
        if (
            assinatura
            and assinatura.status == "checkout_started"
            and assinatura.stripe_checkout_session_id
            and assinatura.stripe_subscription_id == subscription_id
        ):
            logger.info(
                "Mantendo o Checkout pendente da conta enquanto sincroniza a assinatura anterior %s.",
                subscription_id,
            )
            return
        if (
            assinatura
            and assinatura.stripe_subscription_id
            and assinatura.stripe_subscription_id != subscription_id
            and assinatura.status != "checkout_started"
        ):
            logger.warning(
                "Ignorando assinatura Stripe %s; a conta já está vinculada a outra assinatura.",
                subscription_id,
            )
            return

        usuario = self.repository.buscar_usuario(id_usuario)
        if usuario is None:
            logger.warning("Assinatura Stripe %s sem usuário local correspondente.", subscription_id)
            return

        if assinatura is None:
            assinatura = Assinatura(id_usuario=usuario.id_usuario)
        plano_anterior = assinatura.plano_codigo
        inicio_periodo_anterior = assinatura.periodo_inicio
        assinatura.stripe_subscription_id = subscription_id
        assinatura.stripe_customer_id = customer_id or assinatura.stripe_customer_id
        assinatura.status = status
        assinatura.cancelamento_agendado = bool(self._campo(subscription, "cancel_at_period_end", False))
        period_start, period_end = self._periodo_atual(subscription)
        assinatura.periodo_inicio = self._timestamp(period_start)
        assinatura.periodo_fim = self._timestamp(period_end)
        price_id = self._preco_atual(subscription)
        if price_id:
            assinatura.stripe_price_id = price_id
        plano_novo = next(
            (codigo for codigo, configurado in self.settings.stripe_price_ids.items() if configurado and configurado == price_id),
            None,
        )

        if status in {"active", "trialing"} and not plano_novo:
            raise StripeEventoInvalidoError("O preço da assinatura Stripe não corresponde a um plano configurado.")

        if status in {"active", "trialing"}:
            if not period_start or not period_end:
                raise StripeEventoInvalidoError("A assinatura Stripe não informou o ciclo atual.")
            period_start = assinatura.periodo_inicio
            period_end = assinatura.periodo_fim
            if plano_novo != plano_anterior:
                mudou_para_plano_maior = ORDEM_PLANOS[plano_novo] > ORDEM_PLANOS.get(plano_anterior, 0)
                assinatura.inicio_cota = datetime.now(timezone.utc) if mudou_para_plano_maior else period_start
                assinatura.fim_cota = period_end
            elif period_start != inicio_periodo_anterior or not assinatura.inicio_cota:
                assinatura.inicio_cota = period_start
                assinatura.fim_cota = period_end
            usuario.plano_codigo = plano_novo
            assinatura.plano_codigo = plano_novo
            assinatura.checkout_plano_codigo = None
            if plano_novo == assinatura.plano_pendente_codigo:
                assinatura.plano_pendente_codigo = None
                assinatura.stripe_schedule_id = None
        elif status in {"canceled", "unpaid", "incomplete_expired"}:
            usuario.plano_codigo = "free"
            assinatura.plano_codigo = "free"
            assinatura.plano_pendente_codigo = None
            assinatura.stripe_schedule_id = None
            assinatura.periodo_fim = datetime.now(timezone.utc)
        self.repository.salvar_com_usuario(assinatura, usuario)

    def _revogar_assinatura(self, subscription: Any, status: str = "canceled") -> None:
        subscription_id = self._campo(subscription, "id")
        customer_id = self._id_expandido(self._campo(subscription, "customer"))
        assinatura = self.repository.buscar_por_subscription(subscription_id) if subscription_id else None
        if assinatura is None and customer_id:
            assinatura = self.repository.buscar_por_customer(customer_id)
        if assinatura is None:
            return
        if (
            subscription_id
            and assinatura.stripe_subscription_id
            and assinatura.stripe_subscription_id != subscription_id
        ):
            logger.warning(
                "Ignorando revogação Stripe %s; a conta já está vinculada a outra assinatura.",
                subscription_id,
            )
            return
        usuario = self.repository.buscar_usuario(assinatura.id_usuario)
        if usuario is not None:
            usuario.plano_codigo = "free"
        assinatura.plano_codigo = "free"
        assinatura.plano_pendente_codigo = None
        checkout_pendente = assinatura.status == "checkout_started" and bool(
            assinatura.stripe_checkout_session_id
        )
        if not checkout_pendente:
            assinatura.status = status
        assinatura.cancelamento_agendado = False
        assinatura.periodo_fim = datetime.now(timezone.utc)
        if usuario is not None:
            self.repository.salvar_com_usuario(assinatura, usuario)
        else:
            self.repository.salvar(assinatura)

    def _usuario_por_hint(self, user_hint: str | None) -> Usuario | None:
        if not user_hint:
            return None
        try:
            return self.repository.buscar_usuario(uuid.UUID(user_hint))
        except ValueError:
            logger.warning("Evento Stripe contém referência local inválida: %s", user_hint)
            return None

    @staticmethod
    def _campo(objeto: Any, nome: str, padrao: Any = None) -> Any:
        if isinstance(objeto, dict) or hasattr(objeto, "get"):
            return objeto.get(nome, padrao)
        return getattr(objeto, nome, padrao)

    @classmethod
    def _id_expandido(cls, value: Any) -> str | None:
        if isinstance(value, str):
            return value
        return cls._campo(value, "id")

    @classmethod
    def _preco_atual(cls, subscription: Any) -> str | None:
        items = cls._campo(cls._campo(subscription, "items", {}), "data", [])
        if not items:
            return None
        price = cls._campo(items[0], "price")
        return cls._id_expandido(price)

    @classmethod
    def _periodo_atual(cls, subscription: Any) -> tuple[int | None, int | None]:
        inicio = cls._campo(subscription, "current_period_start")
        fim = cls._campo(subscription, "current_period_end")
        items = cls._campo(cls._campo(subscription, "items", {}), "data", [])
        if items:
            inicio = inicio or cls._campo(items[0], "current_period_start")
            fim = fim or cls._campo(items[0], "current_period_end")
        return inicio, fim

    @staticmethod
    def _timestamp(value: int | None) -> datetime | None:
        return datetime.fromtimestamp(value, timezone.utc) if value else None
