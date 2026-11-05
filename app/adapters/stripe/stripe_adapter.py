import stripe

from app.core.config import Settings


class StripeConfiguracaoInvalidaError(Exception):
    pass


class StripeAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _configurar(self) -> None:
        chave = self.settings.stripe_secret_key
        modo = self.settings.stripe_mode.lower()
        if modo not in {"test", "live"}:
            raise StripeConfiguracaoInvalidaError("STRIPE_MODE precisa ser test ou live.")
        if not chave:
            raise StripeConfiguracaoInvalidaError("STRIPE_SECRET_KEY não foi configurada.")
        prefixo_esperado = "sk_test_" if modo == "test" else "sk_live_"
        if not chave.startswith(prefixo_esperado):
            raise StripeConfiguracaoInvalidaError("A chave Stripe não corresponde a STRIPE_MODE.")
        stripe.api_key = chave

    def criar_checkout(
        self,
        *,
        price_id: str,
        user_id: str,
        email: str,
        customer_id: str | None,
    ):
        self._configurar()
        metadata = {"user_id": user_id}
        parametros = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": self.settings.stripe_success_url,
            "cancel_url": self.settings.stripe_cancel_url,
            "client_reference_id": user_id,
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
            "allow_promotion_codes": True,
        }
        if customer_id:
            parametros["customer"] = customer_id
        else:
            parametros["customer_email"] = email
        return stripe.checkout.Session.create(**parametros)

    def obter_checkout(self, session_id: str):
        self._configurar()
        return stripe.checkout.Session.retrieve(session_id)

    def criar_portal(self, customer_id: str):
        self._configurar()
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=self.settings.stripe_portal_return_url,
        )

    def obter_assinatura(self, subscription_id: str):
        self._configurar()
        return stripe.Subscription.retrieve(subscription_id)

    def alterar_plano_imediatamente(self, subscription_id: str, price_id: str):
        self._configurar()
        subscription = stripe.Subscription.retrieve(subscription_id)
        if schedule_id := self._id_expandido(subscription.get("schedule")):
            stripe.SubscriptionSchedule.release(schedule_id)
        item = subscription["items"]["data"][0]
        return stripe.Subscription.modify(
            subscription_id,
            items=[{"id": item["id"], "price": price_id}],
            proration_behavior="always_invoice",
            payment_behavior="pending_if_incomplete",
        )

    def agendar_reducao_plano(self, subscription_id: str, price_id: str):
        self._configurar()
        subscription = stripe.Subscription.retrieve(subscription_id)
        item = subscription["items"]["data"][0]
        period_start, period_end = self._periodo_atual(subscription)
        if period_start is None or period_end is None:
            raise StripeConfiguracaoInvalidaError("A assinatura Stripe não informou o ciclo atual.")
        schedule_id = self._id_expandido(subscription.get("schedule"))
        if schedule_id:
            schedule = stripe.SubscriptionSchedule.retrieve(schedule_id)
        else:
            schedule = stripe.SubscriptionSchedule.create(from_subscription=subscription_id)
        return stripe.SubscriptionSchedule.modify(
            schedule["id"],
            end_behavior="release",
            phases=[
                {
                    "items": [{"price": item["price"]["id"], "quantity": item.get("quantity", 1)}],
                    "start_date": period_start,
                    "end_date": period_end,
                },
                {
                    "items": [{"price": price_id, "quantity": 1}],
                    "start_date": period_end,
                },
            ],
        )

    def cancelar_ao_fim_do_ciclo(self, subscription_id: str):
        self._configurar()
        subscription = stripe.Subscription.retrieve(subscription_id)
        if schedule_id := self._id_expandido(subscription.get("schedule")):
            stripe.SubscriptionSchedule.release(schedule_id)
        return stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)

    def cancelar_imediatamente(self, subscription_id: str):
        self._configurar()
        subscription = stripe.Subscription.retrieve(subscription_id)
        if schedule_id := self._id_expandido(subscription.get("schedule")):
            stripe.SubscriptionSchedule.release(schedule_id)
        return stripe.Subscription.cancel(subscription_id)

    def obter_fatura(self, invoice_id: str):
        self._configurar()
        return stripe.Invoice.retrieve(invoice_id)

    def validar_evento(self, payload: bytes, signature: str):
        secret = self.settings.stripe_webhook_secret
        if not secret:
            raise StripeConfiguracaoInvalidaError("STRIPE_WEBHOOK_SECRET não foi configurado.")
        return stripe.Webhook.construct_event(payload, signature, secret)

    @staticmethod
    def _id_expandido(value):
        return value if isinstance(value, str) else value.get("id") if value else None

    @staticmethod
    def _periodo_atual(subscription):
        inicio = subscription.get("current_period_start")
        fim = subscription.get("current_period_end")
        items = subscription.get("items", {}).get("data", [])
        if items:
            inicio = inicio or items[0].get("current_period_start")
            fim = fim or items[0].get("current_period_end")
        return inicio, fim
