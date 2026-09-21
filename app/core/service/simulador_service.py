import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista
from app.core.persistencia.simulacao_repository import SimulacaoRepository
from app.core.persistencia.vaga_repository import VagaRepository

TIPOS_OBRIGATORIOS = ("comportamental", "tecnica", "situacional")


class VagaNaoEncontradaError(Exception):
    pass


class SimulacaoNaoEncontradaError(Exception):
    pass


class PerguntaNaoEncontradaError(Exception):
    pass


class RespostaVaziaError(Exception):
    pass


class SimuladorService:
    def __init__(self, db: Session, ai_service_adapter: AIServiceAdapter | None = None):
        self.db = db
        self.vaga_repository = VagaRepository(db)
        self.simulacao_repository = SimulacaoRepository(db)
        self.ai_service_adapter = ai_service_adapter or AIServiceAdapter()

    @staticmethod
    def _montar_texto_vaga(vaga) -> str:
        partes = []
        if getattr(vaga, "titulo", None):
            partes.append(f"Título da Vaga: {vaga.titulo}")
        if getattr(vaga, "area", None):
            partes.append(f"Área: {vaga.area}")
        if getattr(vaga, "requisitos", None):
            partes.append(f"Requisitos:\n{vaga.requisitos}")
        if getattr(vaga, "descricao", None):
            partes.append(f"Descrição da Vaga:\n{vaga.descricao}")
        return "\n\n".join(partes)

    def iniciar_simulacao(self, id_usuario: uuid.UUID, id_vaga: uuid.UUID) -> SimulacaoEntrevista:
        # RN-004: não é possível iniciar uma simulação sem uma vaga definida.
        if id_vaga is None:
            raise VagaNaoEncontradaError

        vaga = self.vaga_repository.buscar_por_id(id_vaga)
        if vaga is None or vaga.id_usuario != id_usuario:
            raise VagaNaoEncontradaError

        texto_vaga = self._montar_texto_vaga(vaga)
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

    def responder_pergunta(
        self,
        id_usuario: uuid.UUID,
        id_simulacao: uuid.UUID,
        id_pergunta: uuid.UUID | str,
        resposta: str,
    ) -> SimulacaoEntrevista:
        simulacao = self.obter_simulacao(id_usuario, id_simulacao)

        resposta_normalizada = (resposta or "").strip()
        if not resposta_normalizada:
            raise RespostaVaziaError("Digite uma resposta antes de enviar.")

        perguntas = list(simulacao.perguntas or [])
        indice = next((i for i, p in enumerate(perguntas) if p.get("id_pergunta") == str(id_pergunta)), None)
        if indice is None:
            raise PerguntaNaoEncontradaError

        pergunta = perguntas[indice]
        vaga = self.vaga_repository.buscar_por_id(simulacao.id_vaga)
        texto_vaga = self._montar_texto_vaga(vaga) if vaga else ""

        resultado_ia = self.ai_service_adapter.avaliar_resposta_entrevista(
            texto_vaga=texto_vaga,
            pergunta=pergunta["texto"],
            tipo=pergunta["tipo"],
            resposta=resposta_normalizada,
        )
        feedback = self._interpretar_feedback(resultado_ia)

        pergunta_atualizada = {
            **pergunta,
            "resposta": resposta_normalizada,
            "feedback": feedback,
            "respondida_em": datetime.now(timezone.utc).isoformat(),
        }
        novas_perguntas = [*perguntas[:indice], pergunta_atualizada, *perguntas[indice + 1 :]]

        return self.simulacao_repository.salvar_perguntas(simulacao, novas_perguntas)

    def listar_simulacoes_usuario(self, id_usuario: uuid.UUID) -> list[SimulacaoEntrevista]:
        return self.simulacao_repository.listar_por_usuario(id_usuario)

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
        # técnica e 1 situacional), mesmo que a IA devolva algo incompleto ou fora do formato.
        tipos_presentes = {p["tipo"] for p in perguntas}
        perguntas_reserva = {
            "comportamental": "Conte sobre uma situação em que você precisou lidar com um conflito em equipe.",
            "tecnica": "Descreva sua experiência com as principais ferramentas exigidas por esta vaga.",
            "situacional": "Como você agiria se recebesse uma tarefa com prazo apertado e prioridades conflitantes?",
        }
        for tipo in TIPOS_OBRIGATORIOS:
            if tipo not in tipos_presentes:
                perguntas.append({"tipo": tipo, "texto": perguntas_reserva[tipo]})

        return perguntas

    def _interpretar_feedback(self, resultado_ia: str) -> dict:
        dados = self._extrair_json(resultado_ia)
        if not isinstance(dados, dict):
            dados = {}

        def _dimensao(chave: str) -> dict:
            bruto = dados.get(chave)
            if isinstance(bruto, dict):
                try:
                    nota = float(bruto.get("nota"))
                except (TypeError, ValueError):
                    nota = None
                comentario = str(bruto.get("comentario") or "").strip()
                return {"nota": nota, "comentario": comentario}
            return {"nota": None, "comentario": ""}

        return {
            "clareza": _dimensao("clareza"),
            "objetividade": _dimensao("objetividade"),
            "coerencia": _dimensao("coerencia"),
            "alinhamento": _dimensao("alinhamento"),
            "feedback_geral": str(dados.get("feedback_geral") or "").strip(),
        }

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
