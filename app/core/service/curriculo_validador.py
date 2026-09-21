"""Etapa 2 do pipeline: validação do JSON da IA (determinística, sem IA).

A validação em si (`validar`) é 100% determinística — só usa o schema
Pydantic, nunca chama a IA — para poder ser testada e mantida sem precisar de
`GEMINI_API_KEY`. Ela é isolada da Etapa 1 (não sabe nada de Gemini/prompt) e
da Etapa 3 (não sabe nada de docxtpl/LibreOffice): só entende o contrato
`DadosCurriculoEstruturado`.

`validar_e_reparar` é o único ponto deste módulo que ainda toca em IA, e de
forma isolada e opcional: quando um campo de texto obrigatório volta vazio,
faz UM retry cirúrgico (só daquele campo, nunca do currículo inteiro) via
`GeradorCurriculoEstruturadoIA.regenerar_campo`. Isso é bem mais barato que
regenerar tudo de novo e deixa claro, nos logs, quais campos do prompt da
Etapa 1 estão precisando de reforço — útil para monitorar a qualidade do
prompt ao longo do tempo.
"""

import logging

from pydantic import ValidationError

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.adapters.ai_service.curriculo_estruturado_client import (
    GeradorCurriculoEstruturadoIA,
    IARespostaInvalidaError,
)
from app.adapters.ai_service.curriculo_schema import CAMPOS_TEXTO_OBRIGATORIOS, DadosCurriculoEstruturado

logger = logging.getLogger(__name__)


class CurriculoInvalidoError(Exception):
    """JSON que não corresponde ao schema, mesmo antes de qualquer retry."""


class ValidadorCurriculoEstruturado:
    def __init__(self, gerador: GeradorCurriculoEstruturadoIA | None = None):
        # `gerador` é opcional de propósito: quem só precisa validar (sem
        # nenhuma chance de retry por IA) pode instanciar sem ele e usar só
        # `validar()`, que nunca importa nada de IA em tempo de execução.
        self._gerador = gerador

    def validar(self, dados_brutos: dict) -> tuple[DadosCurriculoEstruturado | None, list[str]]:
        """Valida `dados_brutos` contra o schema. Nunca chama IA.

        Retorna (dados, campos_obrigatorios_vazios). `dados` vem `None` só
        quando o JSON nem sequer corresponde ao schema (tipos errados,
        campos com nome diferente etc.) — nesse caso todos os campos
        obrigatórios contam como vazios.
        """
        try:
            dados = DadosCurriculoEstruturado.model_validate(dados_brutos)
        except ValidationError as erro:
            logger.warning("JSON retornado pela IA não corresponde ao schema: %s", erro)
            return None, list(CAMPOS_TEXTO_OBRIGATORIOS)

        campos_vazios = [campo for campo in CAMPOS_TEXTO_OBRIGATORIOS if not getattr(dados, campo).strip()]
        return dados, campos_vazios

    def validar_e_reparar(
        self, dados_brutos: dict, informacoes_brutas: str
    ) -> tuple[DadosCurriculoEstruturado, list[str]]:
        """Valida e tenta reparar campos obrigatórios vazios com retry cirúrgico.

        Retorna (dados_finais, campos_que_precisaram_de_retry) — a segunda
        parte é o que deve ser logado/monitorado para acompanhar a qualidade
        do prompt da Etapa 1 ao longo do tempo.

        Levanta `CurriculoInvalidoError` se o JSON nem sequer corresponder ao
        schema (nada a reparar campo a campo nesse caso).
        """
        dados, campos_vazios = self.validar(dados_brutos)
        if dados is None:
            raise CurriculoInvalidoError("JSON retornado pela IA não corresponde ao schema esperado.")

        campos_que_precisaram_retry: list[str] = []
        for campo in campos_vazios:
            campos_que_precisaram_retry.append(campo)
            if self._gerador is None:
                logger.warning("Campo obrigatório '%s' veio vazio e nenhum gerador foi configurado para retry.", campo)
                continue
            try:
                valor_reparado = self._gerador.regenerar_campo(informacoes_brutas, campo)
            except (IAConfiguracaoAusenteError, IAIndisponivelError, IARespostaInvalidaError) as erro:
                logger.warning("Retry cirúrgico do campo '%s' falhou: %s", campo, erro)
                continue

            if valor_reparado.strip():
                setattr(dados, campo, valor_reparado.strip())
                logger.info("Campo '%s' reparado com sucesso via retry cirúrgico.", campo)
            else:
                logger.warning("Campo '%s' continua vazio mesmo após retry cirúrgico (sem informação na fonte).", campo)

        return dados, campos_que_precisaram_retry
