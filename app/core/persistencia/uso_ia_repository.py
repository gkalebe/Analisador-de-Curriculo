import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.persistencia.models.assinatura import Assinatura
from app.core.persistencia.models.uso_ia import UsoIA
from app.core.persistencia.models.usuario import Usuario

DIAS_JANELA_COTA = 30
MINUTOS_EXPIRACAO_RESERVA = 15


class UsuarioUsoNaoEncontradoError(Exception):
    pass


class LimiteUsoIAExcedidoError(Exception):
    def __init__(self, tipo_operacao: str, renovacao_em: datetime):
        self.tipo_operacao = tipo_operacao
        self.renovacao_em = renovacao_em
        super().__init__("A cota desta operação foi atingida.")


class JanelaCobrancaExpiradaError(Exception):
    pass


class UsoIARepository:
    def __init__(self, db: Session):
        self.db = db

    def obter_janela_assinatura(self, id_usuario: uuid.UUID) -> tuple[datetime, datetime] | None:
        assinatura = self.db.execute(
            select(Assinatura).where(Assinatura.id_usuario == id_usuario)
        ).scalar_one_or_none()
        if (
            assinatura
            and assinatura.status in {"active", "trialing"}
            and (inicio := (assinatura.inicio_cota or assinatura.periodo_inicio))
            and (fim := (assinatura.fim_cota or assinatura.periodo_fim))
        ):
            return inicio, fim
        return None

    def obter_inicio_plano_gratis(self, id_usuario: uuid.UUID) -> datetime | None:
        assinatura = self.db.execute(
            select(Assinatura).where(Assinatura.id_usuario == id_usuario)
        ).scalar_one_or_none()
        if assinatura and assinatura.status in {"canceled", "refunded", "unpaid", "incomplete_expired"}:
            return assinatura.periodo_fim
        return None

    def reservar(
        self,
        id_usuario: uuid.UUID,
        tipo_operacao: str,
        categoria_orcamento: str,
        creditos: int,
        limite_operacao: int,
        limite_creditos: int,
    ) -> UsoIA:
        agora = datetime.now(timezone.utc)
        usuario = self.db.execute(
            select(Usuario).where(Usuario.id_usuario == id_usuario).with_for_update()
        ).scalar_one_or_none()
        if usuario is None:
            raise UsuarioUsoNaoEncontradoError
        janela_assinatura = self.obter_janela_assinatura(id_usuario)
        inicio_plano_gratis = self.obter_inicio_plano_gratis(id_usuario) if not janela_assinatura else None
        if janela_assinatura and janela_assinatura[1] <= agora:
            self.db.rollback()
            raise JanelaCobrancaExpiradaError

        self.db.execute(
            update(UsoIA)
            .where(
                UsoIA.id_usuario == id_usuario,
                UsoIA.estado == "reservado",
                UsoIA.expira_em <= agora,
            )
            .values(estado="liberado", finalizado_em=agora)
        )

        usos_ativos = list(
            self.db.execute(
                select(UsoIA)
                .where(
                    UsoIA.id_usuario == id_usuario,
                    or_(
                        UsoIA.estado == "consumido",
                        (UsoIA.estado == "reservado") & (UsoIA.expira_em > agora),
                    ),
                    UsoIA.fim_janela > agora,
                )
                .order_by(UsoIA.inicio_janela, UsoIA.criado_em)
            )
            .scalars()
            .all()
        )

        if janela_assinatura:
            inicio_janela, fim_janela = janela_assinatura
            usos_janela = [
                uso
                for uso in usos_ativos
                if uso.inicio_janela == inicio_janela and uso.fim_janela == fim_janela
            ]
        elif usos_ativos:
            inicio_janela = usos_ativos[0].inicio_janela
            fim_janela = usos_ativos[0].fim_janela
            usos_janela = [
                uso
                for uso in usos_ativos
                if uso.inicio_janela == inicio_janela and uso.fim_janela == fim_janela
            ]
        else:
            if inicio_plano_gratis:
                usos_ativos = [uso for uso in usos_ativos if uso.inicio_janela >= inicio_plano_gratis]
            if usos_ativos:
                inicio_janela = usos_ativos[0].inicio_janela
                fim_janela = usos_ativos[0].fim_janela
                usos_janela = [
                    uso
                    for uso in usos_ativos
                    if uso.inicio_janela == inicio_janela and uso.fim_janela == fim_janela
                ]
            else:
                inicio_janela = agora
                fim_janela = agora + timedelta(days=DIAS_JANELA_COTA)
                usos_janela = []

        usos_operacao = sum(uso.tipo_operacao == tipo_operacao for uso in usos_janela)
        creditos_usados = sum(
            uso.creditos for uso in usos_janela if uso.categoria_orcamento == categoria_orcamento
        )
        if usos_operacao >= limite_operacao or creditos_usados + creditos > limite_creditos:
            self.db.rollback()
            raise LimiteUsoIAExcedidoError(tipo_operacao, fim_janela)

        reserva = UsoIA(
            id_usuario=id_usuario,
            tipo_operacao=tipo_operacao,
            categoria_orcamento=categoria_orcamento,
            creditos=creditos,
            estado="reservado",
            inicio_janela=inicio_janela,
            fim_janela=fim_janela,
            expira_em=agora + timedelta(minutes=MINUTOS_EXPIRACAO_RESERVA),
        )
        self.db.add(reserva)
        self.db.commit()
        self.db.refresh(reserva)
        return reserva

    def finalizar(self, id_uso: uuid.UUID, estado: str) -> UsoIA:
        uso = self.db.get(UsoIA, id_uso)
        if uso is None or uso.estado != "reservado":
            raise ValueError("A reserva de uso de IA não está mais ativa.")
        uso.estado = estado
        uso.finalizado_em = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(uso)
        return uso

    def listar_usos_ativos(self, id_usuario: uuid.UUID) -> list[UsoIA]:
        agora = datetime.now(timezone.utc)
        return list(
            self.db.execute(
                select(UsoIA)
                .where(
                    UsoIA.id_usuario == id_usuario,
                    or_(
                        UsoIA.estado == "consumido",
                        (UsoIA.estado == "reservado") & (UsoIA.expira_em > agora),
                    ),
                    UsoIA.fim_janela > agora,
                )
                .order_by(UsoIA.inicio_janela, UsoIA.criado_em)
            )
            .scalars()
            .all()
        )

    def obter_usuario(self, id_usuario: uuid.UUID) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)
