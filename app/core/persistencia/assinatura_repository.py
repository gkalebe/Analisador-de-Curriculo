from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.persistencia.models.assinatura import Assinatura, EventoStripe
from app.core.persistencia.models.usuario import Usuario


class AssinaturaRepository:
    PRAZO_RESERVA_EVENTO_MINUTOS = 10

    def __init__(self, db: Session):
        self.db = db

    def buscar_por_usuario(self, id_usuario: UUID) -> Assinatura | None:
        return self.db.execute(select(Assinatura).where(Assinatura.id_usuario == id_usuario)).scalar_one_or_none()

    def bloquear_usuario(self, id_usuario: UUID) -> None:
        self.db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario).with_for_update()).scalar_one()

    def buscar_por_customer(self, customer_id: str) -> Assinatura | None:
        return self.db.execute(
            select(Assinatura).where(Assinatura.stripe_customer_id == customer_id)
        ).scalar_one_or_none()

    def buscar_por_subscription(self, subscription_id: str) -> Assinatura | None:
        return self.db.execute(
            select(Assinatura).where(Assinatura.stripe_subscription_id == subscription_id)
        ).scalar_one_or_none()

    def buscar_por_checkout(self, session_id: str) -> Assinatura | None:
        return self.db.execute(
            select(Assinatura).where(Assinatura.stripe_checkout_session_id == session_id)
        ).scalar_one_or_none()

    def salvar(self, assinatura: Assinatura) -> Assinatura:
        self.db.add(assinatura)
        self.db.commit()
        self.db.refresh(assinatura)
        return assinatura

    def salvar_com_usuario(self, assinatura: Assinatura, usuario: Usuario) -> Assinatura:
        self.db.add(usuario)
        self.db.add(assinatura)
        self.db.commit()
        self.db.refresh(assinatura)
        return assinatura

    def buscar_usuario(self, id_usuario: UUID) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)

    def reservar_evento(self, event_id: str, event_type: str) -> bool | None:
        resultado = self.db.execute(
            insert(EventoStripe)
            .values(id_evento=event_id, tipo_evento=event_type, estado="processing")
            .on_conflict_do_nothing(index_elements=[EventoStripe.id_evento])
        )
        if resultado.rowcount:
            self.db.commit()
            return True

        evento = self.db.execute(
            select(EventoStripe).where(EventoStripe.id_evento == event_id).with_for_update()
        ).scalar_one_or_none()
        if evento is None or evento.estado == "processed":
            self.db.rollback()
            return False
        if (
            evento.estado == "processing"
            and evento.recebido_em
            and evento.recebido_em > datetime.now(timezone.utc) - timedelta(minutes=self.PRAZO_RESERVA_EVENTO_MINUTOS)
        ):
            self.db.rollback()
            return None
        evento.estado = "processing"
        evento.recebido_em = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def finalizar_evento(self, event_id: str, estado: str) -> None:
        evento = self.db.get(EventoStripe, event_id)
        if evento is not None:
            evento.estado = estado
            evento.processado_em = datetime.now(timezone.utc) if estado == "processed" else None
            self.db.commit()
