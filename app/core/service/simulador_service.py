import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.ai_service.response_contracts import interpretar_avaliacao_entrevista
from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista, calcular_nota_final
from app.core.persistencia.simulacao_repository import SimulacaoRepository
from app.core.persistencia.vaga_repository import VagaRepository
from app.core.service.uso_ia_service import UsoIAService

TIPOS_OBRIGATORIOS = ("comportamental", "tecnica", "situacional")
MAXIMO_PERGUNTAS_POR_SIMULACAO = 20


class VagaNaoEncontradaError(Exception):
    pass


class SimulacaoNaoEncontradaError(Exception):
    pass


class SimulacaoJaAvaliadaError(Exception):
    pass


class SimulacaoEmAvaliacaoError(Exception):
    pass


class RespostasInvalidasError(Exception):
    pass


class SimuladorService:
    def __init__(
        self,
        db: Session,
        ai_service_adapter: AIServiceAdapter | None = None,
        uso_ia_service: UsoIAService | None = None,
    ):
        self.db = db
        self.uso_ia_service = uso_ia_service or UsoIAService(db)
        self.vaga_repository = VagaRepository(db)
        self.simulacao_repository = SimulacaoRepository(db)
        self.ai_service_adapter = ai_service_adapter or AIServiceAdapter()

    @staticmethod
    def _montar_texto_vaga(vaga) -> str:
        partes = []
        if getattr(vaga, "titulo", None):
            partes.append(f"Título da Vaga: {vaga.titulo}")
        if getattr(vaga, "empresa", None):
            partes.append(f"Empresa: {vaga.empresa}")
        if getattr(vaga, "area", None):
            partes.append(f"Área: {vaga.area}")
        if getattr(vaga, "localizacao", None):
            partes.append(f"Localização: {vaga.localizacao}")
        if getattr(vaga, "modalidade", None):
            partes.append(f"Modalidade: {vaga.modalidade}")
        if getattr(vaga, "senioridade", None):
            partes.append(f"Senioridade: {vaga.senioridade}")
        if getattr(vaga, "descricao", None):
            partes.append(f"Descrição da Vaga:\n{vaga.descricao}")
        if getattr(vaga, "responsabilidades", None):
            partes.append(f"Responsabilidades:\n{vaga.responsabilidades}")
        if getattr(vaga, "requisitos", None):
            partes.append(f"Requisitos:\n{vaga.requisitos}")
        if getattr(vaga, "requisitos_obrigatorios", None):
            partes.append(f"Requisitos Obrigatórios:\n{vaga.requisitos_obrigatorios}")
        if getattr(vaga, "requisitos_desejaveis", None):
            partes.append(f"Requisitos Desejáveis:\n{vaga.requisitos_desejaveis}")
        if getattr(vaga, "competencias", None):
            partes.append(f"Competências:\n{vaga.competencias}")
        return "\n\n".join(partes)

    def iniciar_simulacao(self, id_usuario: uuid.UUID, id_vaga: uuid.UUID) -> SimulacaoEntrevista:
        # RN-004: não é possível iniciar uma simulação sem uma vaga definida.
        if id_vaga is None:
            raise VagaNaoEncontradaError

        vaga = self.vaga_repository.buscar_por_id(id_vaga)
        if vaga is None or vaga.id_usuario != id_usuario:
            raise VagaNaoEncontradaError

        texto_vaga = self._montar_texto_vaga(vaga)
        with self.uso_ia_service.reservar(id_usuario, "entrevista_inicio"):
            resultado_ia = self.ai_service_adapter.gerar_perguntas_entrevista(texto_vaga)
            perguntas_geradas = self._interpretar_perguntas(resultado_ia)

            perguntas = [
                {
                    "id_pergunta": str(uuid.uuid4()),
                    "tipo": p["tipo"],
                    "texto": p["texto"],
                    "resposta": None,
                    "feedback": None,
                    "respondida_em": None,
                }
                for p in perguntas_geradas
            ]

            simulacao = SimulacaoEntrevista(id_usuario=id_usuario, id_vaga=id_vaga, perguntas=perguntas)
            return self.simulacao_repository.criar(simulacao)

    def obter_simulacao(self, id_usuario: uuid.UUID, id_simulacao: uuid.UUID) -> SimulacaoEntrevista:
        simulacao = self.simulacao_repository.buscar_por_id(id_simulacao)
        if simulacao is None or simulacao.id_usuario != id_usuario:
            raise SimulacaoNaoEncontradaError
        return simulacao

    def excluir_simulacao(self, id_usuario: uuid.UUID, id_simulacao: uuid.UUID) -> None:
        """Exclusão definitiva, pedida pelo próprio usuário. Não devolve cota: a entrevista
        (e a avaliação, se houve) já foi consumida no ciclo. Trava a linha filtrando pelo dono e
        com NOWAIT: se a entrevista estiver sendo avaliada nesse instante, responde 409 sem
        pendurar o DELETE nem arriscar apagar a linha antes da serialização da resposta."""
        try:
            simulacao = self.simulacao_repository.buscar_por_id_para_atualizacao(
                id_simulacao, id_usuario=id_usuario, nowait=True
            )
        except OperationalError as erro:
            self.simulacao_repository.db.rollback()
            if getattr(getattr(erro, "orig", None), "pgcode", None) == "55P03" or "lock" in str(erro).lower():
                raise SimulacaoEmAvaliacaoError(
                    "Esta entrevista está sendo avaliada; tente excluir quando terminar."
                ) from erro
            raise
        if simulacao is None or simulacao.id_usuario != id_usuario:
            self.simulacao_repository.db.rollback()
            raise SimulacaoNaoEncontradaError
        self.simulacao_repository.excluir(simulacao)

    def repetir_simulacao(self, id_usuario: uuid.UUID, id_simulacao: uuid.UUID) -> SimulacaoEntrevista:
        """Cria uma NOVA simulação para a mesma vaga (novas perguntas, consome 1 entrevista da
        cota). A simulação original, com respostas e feedback, não é alterada."""
        original = self.obter_simulacao(id_usuario, id_simulacao)
        return self.iniciar_simulacao(id_usuario, original.id_vaga)

    def avaliar_simulacao(
        self,
        id_usuario: uuid.UUID,
        id_simulacao: uuid.UUID,
        respostas: dict[str, str],
    ) -> SimulacaoEntrevista:
        """Avalia todas as respostas de uma vez (uma única chamada de IA, uma reserva de cota).

        `respostas` mapeia id_pergunta -> texto; precisa conter exatamente as perguntas da
        simulação. Concorrência: a linha da simulação é travada (FOR UPDATE) durante a chamada
        de IA e re-verificada depois da reserva de cota, então duas requisições simultâneas nunca
        avaliam (nem cobram) a mesma simulação duas vezes. A reserva é liberada se a IA falhar ou
        devolver algo inválido.

        Trade-off conhecido: o `FOR UPDATE` mantém a transação aberta durante a chamada de IA. Na
        escala atual isso é aceitável e evita uma coluna extra de estado; se a contenção de
        conexões ou o tempo de fallback da IA crescer, basta substituir por uma marca curta
        (`avaliando_desde` + `UPDATE ... WHERE avaliada_em IS NULL`)."""
        simulacao = self.obter_simulacao(id_usuario, id_simulacao)
        self._validar_avaliacao_possivel(simulacao, respostas)

        with self.uso_ia_service.reservar(id_usuario, "entrevista_avaliacao"):
            # O commit da reserva soltou qualquer lock anterior: trava a linha agora e confere de
            # novo, porque outra requisição pode ter concluído a avaliação nesse intervalo.
            simulacao = self.simulacao_repository.buscar_por_id_para_atualizacao(
                id_simulacao, id_usuario=id_usuario
            )
            if simulacao is None or simulacao.id_usuario != id_usuario:
                raise SimulacaoNaoEncontradaError
            self._validar_avaliacao_possivel(simulacao, respostas)

            perguntas = list(simulacao.perguntas or [])
            vaga = self.vaga_repository.buscar_por_id(simulacao.id_vaga)
            texto_vaga = self._montar_texto_vaga(vaga) if vaga else ""
            itens = [
                {
                    "ordem": posicao,
                    "tipo": pergunta["tipo"],
                    "pergunta": pergunta["texto"],
                    "resposta": respostas[pergunta["id_pergunta"]],
                }
                for posicao, pergunta in enumerate(perguntas, start=1)
            ]

            resultado_ia = self.ai_service_adapter.avaliar_respostas_entrevista(texto_vaga, itens)
            avaliacao = interpretar_avaliacao_entrevista(resultado_ia, len(perguntas))
            por_ordem = {item.ordem: item for item in avaliacao.avaliacoes}

            agora = datetime.now(timezone.utc)
            perguntas_avaliadas = []
            for posicao, pergunta in enumerate(perguntas, start=1):
                item = por_ordem[posicao]
                perguntas_avaliadas.append(
                    {
                        **pergunta,
                        "resposta": respostas[pergunta["id_pergunta"]],
                        "feedback": {
                            dimensao: {
                                "nota": getattr(item, dimensao).nota,
                                "comentario": getattr(item, dimensao).comentario.strip(),
                            }
                            for dimensao in ("clareza", "objetividade", "coerencia", "alinhamento")
                        }
                        | {"feedback_geral": item.feedback_geral.strip()},
                        "respondida_em": agora.isoformat(),
                    }
                )

            return self.simulacao_repository.salvar_avaliacao(
                simulacao,
                perguntas_avaliadas,
                feedback_geral=avaliacao.feedback_geral.strip(),
                nota_final=calcular_nota_final(perguntas_avaliadas),
                avaliada_em=agora,
            )

    @staticmethod
    def _validar_avaliacao_possivel(simulacao: SimulacaoEntrevista, respostas: dict[str, str]) -> None:
        if simulacao.status == "avaliada":
            raise SimulacaoJaAvaliadaError
        ids_esperados = {p["id_pergunta"] for p in (simulacao.perguntas or [])}
        if not ids_esperados or set(respostas) != ids_esperados:
            raise RespostasInvalidasError(
                "Responda todas as perguntas da simulação, sem faltar nem incluir perguntas de outra entrevista."
            )

    def listar_simulacoes_usuario(
        self, id_usuario: uuid.UUID, limit: int | None = None, offset: int = 0
    ) -> list[SimulacaoEntrevista]:
        return self.simulacao_repository.listar_por_usuario(id_usuario, limit=limit, offset=offset)

    def contar_simulacoes_usuario(self, id_usuario: uuid.UUID) -> int:
        return self.simulacao_repository.contar_por_usuario(id_usuario)

    def _interpretar_perguntas(self, resultado_ia: str) -> list[dict]:
        dados = self._extrair_json(resultado_ia)
        perguntas_brutas = dados.get("perguntas") if isinstance(dados, dict) else None
        perguntas: list[dict] = []
        if isinstance(perguntas_brutas, list):
            for item in perguntas_brutas:
                if not isinstance(item, dict):
                    continue
                tipo = str(item.get("tipo") or "").strip().lower()
                texto = str(item.get("texto") or "").strip()
                if tipo in TIPOS_OBRIGATORIOS and texto:
                    perguntas.append({"tipo": tipo, "texto": texto})

        # Garante a cobertura mínima exigida (RN de aceite: ao menos 1 comportamental, 1
        # técnica e 1 situacional) e limita ao teto aceito pelo schema de avaliação (20), mesmo
        # que a IA devolva algo incompleto ou em excesso.
        if len(perguntas) > MAXIMO_PERGUNTAS_POR_SIMULACAO:
            perguntas = perguntas[:MAXIMO_PERGUNTAS_POR_SIMULACAO]
        tipos_presentes = {p["tipo"] for p in perguntas}
        faltantes = [tipo for tipo in TIPOS_OBRIGATORIOS if tipo not in tipos_presentes]
        if faltantes and len(perguntas) + len(faltantes) > MAXIMO_PERGUNTAS_POR_SIMULACAO:
            perguntas = perguntas[: MAXIMO_PERGUNTAS_POR_SIMULACAO - len(faltantes)]
            tipos_presentes = {p["tipo"] for p in perguntas}
            faltantes = [tipo for tipo in TIPOS_OBRIGATORIOS if tipo not in tipos_presentes]
        perguntas_reserva = {
            "comportamental": "Conte sobre uma situação em que você precisou lidar com um conflito em equipe.",
            "tecnica": "Descreva sua experiência com as principais ferramentas exigidas por esta vaga.",
            "situacional": "Como você agiria se recebesse uma tarefa com prazo apertado e prioridades conflitantes?",
        }
        for tipo in faltantes:
            perguntas.append({"tipo": tipo, "texto": perguntas_reserva[tipo]})

        return perguntas

    @staticmethod
    def _extrair_json(resultado_ia: str):
        texto = (resultado_ia or "").strip()
        if texto.startswith("```"):
            texto = texto.strip("`").strip()
            if texto.lower().startswith("json"):
                texto = texto[4:].strip()
        try:
            return json.loads(texto)
        except (json.JSONDecodeError, TypeError):
            return {}
