from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator
import uuid

from app.core.persistencia.models.uso_ia import UsoIA
from app.core.persistencia.uso_ia_repository import (
    JanelaCobrancaExpiradaError,
    LimiteUsoIAExcedidoError,
    UsoIARepository,
)
from app.core.service.catalogo_planos import (
    LIMITES_OPERACAO,
    OPERACOES_ANALISE,
    PESO_CREDITOS_OPERACAO,
    obter_plano,
)


class CotaIAExcedidaError(Exception):
    def __init__(self, tipo_operacao: str, renovacao_em: datetime):
        self.tipo_operacao = tipo_operacao
        self.renovacao_em = renovacao_em
        super().__init__("A cota desta operação foi atingida.")


class CotaIATemporariamenteIndisponivelError(Exception):
    pass


class UsoIAService:
    def __init__(self, db):
        self.repository = UsoIARepository(db)

    @contextmanager
    def reservar(self, id_usuario: uuid.UUID, tipo_operacao: str) -> Iterator[UsoIA]:
        if tipo_operacao not in PESO_CREDITOS_OPERACAO:
            raise ValueError(f"Operação de IA desconhecida: {tipo_operacao}")

        usuario = self.repository.obter_usuario(id_usuario)
        if usuario is None:
            raise ValueError("Usuário não encontrado para contabilizar uso de IA.")
        plano = obter_plano(usuario.plano_codigo)
        categoria_orcamento = "analise" if tipo_operacao in OPERACOES_ANALISE else "demais"
        limite_creditos = (
            plano.creditos_analise
            if categoria_orcamento == "analise"
            else plano.creditos_demais_operacoes
        )
        try:
            reserva = self.repository.reservar(
                id_usuario=id_usuario,
                tipo_operacao=tipo_operacao,
                categoria_orcamento=categoria_orcamento,
                creditos=PESO_CREDITOS_OPERACAO[tipo_operacao],
                limite_operacao=getattr(plano, LIMITES_OPERACAO[tipo_operacao]),
                limite_creditos=limite_creditos,
            )
        except LimiteUsoIAExcedidoError as erro:
            raise CotaIAExcedidaError(erro.tipo_operacao, erro.renovacao_em) from erro
        except JanelaCobrancaExpiradaError as erro:
            raise CotaIATemporariamenteIndisponivelError from erro

        try:
            yield reserva
        except BaseException:
            self.liberar(reserva)
            raise
        else:
            if reserva.estado == "reservado":
                self.repository.finalizar(reserva.id_uso, "consumido")

    def liberar(self, reserva: UsoIA) -> None:
        if reserva.estado == "reservado":
            self.repository.finalizar(reserva.id_uso, "liberado")

    def obter_resumo(self, id_usuario: uuid.UUID) -> dict:
        usuario = self.repository.obter_usuario(id_usuario)
        if usuario is None:
            raise ValueError("Usuário não encontrado para consultar o uso de IA.")
        plano = obter_plano(usuario.plano_codigo)
        usos_ativos = self.repository.listar_usos_ativos(id_usuario)
        janela_assinatura = self.repository.obter_janela_assinatura(id_usuario)
        if janela_assinatura:
            inicio_janela, fim_janela = janela_assinatura
            usos_ativos = [
                uso
                for uso in usos_ativos
                if uso.inicio_janela == inicio_janela and uso.fim_janela == fim_janela
            ]
            janela = None
        else:
            inicio_plano_gratis = self.repository.obter_inicio_plano_gratis(id_usuario)
            if inicio_plano_gratis:
                usos_ativos = [uso for uso in usos_ativos if uso.inicio_janela >= inicio_plano_gratis]
            janela = usos_ativos[0] if usos_ativos else None
        contagens = Counter(
            uso.tipo_operacao
            for uso in usos_ativos
            if uso.estado in {"reservado", "consumido"}
        )
        return {
            "plano": plano,
            "inicio_janela": inicio_janela if janela_assinatura else janela.inicio_janela if janela else None,
            "fim_janela": fim_janela if janela_assinatura else janela.fim_janela if janela else None,
            "usos": dict(contagens),
        }
