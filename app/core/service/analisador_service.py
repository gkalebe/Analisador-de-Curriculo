import json
import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.curriculo_parser.curriculo_parser import CurriculoParser
from app.core.config import get_settings
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models.analise import Analise
from app.core.persistencia.models.candidato import Candidato
from app.core.persistencia.models.curriculo import Curriculo
from app.core.persistencia.models.vaga import Vaga
from app.core.persistencia.vaga_repository import VagaRepository
from app.core.service.extracao_curriculo import (
    aplicar_sugestoes_em_dados_curriculo,
    extrair_dados_estruturados_curriculo,
    normalizar_dados_editados,
    obter_dados_curriculo_com_cache,
)

# Mesmos 4 campos estruturados usados na tela de edição (EditarCurriculo.jsx) — a IA já
# devolve qual desses campos cada sugestão de reescrita tem como alvo (ver
# AIServiceAdapter._montar_prompt_comparacao), então o front não precisa mais adivinhar o
# bloco certo por sobreposição de palavras.
CAMPOS_CURRICULO_VALIDOS = {"resumo", "formacao", "experiencia_profissional", "habilidades"}


class DescricaoVagaObrigatoriaError(Exception):
    pass


class DescricaoVagaMuitoLongaError(Exception):
    pass


class VagaDuplicadaError(Exception):
    pass


class VagaNaoEncontradaError(Exception):
    pass


class CurriculoNaoEncontradoError(Exception):
    pass


class CurriculoArquivoNaoEncontradoError(Exception):
    pass


class NenhumaSugestaoDisponivelError(Exception):
    pass


class AnalisadorService:
    def __init__(self, db: Session):
        self.curriculo_repository = CurriculoRepository(db)
        self.vaga_repository = VagaRepository(db)
        self.analise_repository = AnaliseRepository(db)
        self.curriculo_parser = CurriculoParser()
        self.ai_service_adapter = AIServiceAdapter()
        self.settings = get_settings()

    def processar_upload_curriculo(self, conteudo: bytes, nome_arquivo: str, extensao: str, id_usuario) -> dict:
        texto_extraido = self.curriculo_parser.extrair_texto(conteudo, extensao)

        novo_curriculo = Curriculo(
            nome_arquivo=nome_arquivo,
            id_usuario=id_usuario,
            status_processamento="concluido",
            texto_extraido=texto_extraido,
            conteudo_arquivo=conteudo,
        )
        self.curriculo_repository.criar(novo_curriculo)

        dados_estruturados = self._extrair_dados_estruturados(texto_extraido)
        if dados_estruturados:
            self.curriculo_repository.salvar_candidato(novo_curriculo.id_curriculo, dados_estruturados)

        return {
            "id_curriculo": str(novo_curriculo.id_curriculo),
            "nome_arquivo": nome_arquivo,
            "tamanho_texto_extraido": len(texto_extraido),
            "dados": dados_estruturados,
        }

    def cadastrar_vaga(
        self,
        id_usuario: uuid.UUID,
        descricao: str,
        titulo: str | None = None,
        requisitos: str | None = None,
        area: str | None = None,
    ) -> Vaga:
        descricao_normalizada = (descricao or "").strip()
        if not descricao_normalizada:
            raise DescricaoVagaObrigatoriaError
        if len(descricao_normalizada) > self.settings.max_vaga_description_chars:
            raise DescricaoVagaMuitoLongaError

        # Compara com as vagas já salvas do usuário para recusar duplicata exata (mesma
        # descrição, ignorando maiúsculas/minúsculas e espaços nas pontas) — evita que o
        # mesmo texto colado duas vezes (ex.: formulário que não limpa após salvar) vire
        # duas vagas idênticas no histórico do usuário.
        descricao_para_comparacao = descricao_normalizada.lower()
        vagas_existentes = self.vaga_repository.listar_por_usuario(id_usuario)
        if any((vaga_existente.descricao or "").strip().lower() == descricao_para_comparacao for vaga_existente in vagas_existentes):
            raise VagaDuplicadaError

        vaga = Vaga(
            titulo=(titulo or "").strip() or None,
            descricao=descricao_normalizada,
            requisitos=(requisitos or "").strip() or None,
            area=(area or "").strip() or None,
            id_usuario=id_usuario,
        )
        return self.vaga_repository.criar(vaga)

    def listar_vagas_usuario(self, id_usuario: uuid.UUID) -> list[Vaga]:
        return self.vaga_repository.listar_por_usuario(id_usuario)

    def analisar_curriculo_para_vaga(
        self,
        id_usuario: uuid.UUID,
        id_vaga: uuid.UUID,
        conteudo: bytes,
        nome_arquivo: str,
        extensao: str,
    ) -> Analise:
        vaga = self.vaga_repository.buscar_por_id(id_vaga)
        if vaga is None or vaga.id_usuario != id_usuario:
            raise VagaNaoEncontradaError

        texto_curriculo = self.curriculo_parser.extrair_texto(conteudo, extensao)

        novo_curriculo = Curriculo(
            nome_arquivo=nome_arquivo,
            id_usuario=id_usuario,
            status_processamento="processando",
            texto_extraido=texto_curriculo,
            conteudo_arquivo=conteudo,
        )
        self.curriculo_repository.criar(novo_curriculo)

        resultado_ia = self.ai_service_adapter.comparar_curriculo_vaga(texto_curriculo, vaga.descricao)
        pontuacao, observacoes = self._interpretar_resultado_ia(resultado_ia)

        analise = Analise(
            id_curriculo=novo_curriculo.id_curriculo,
            id_vaga=vaga.id_vaga,
            id_usuario=id_usuario,
            pontuacao=pontuacao,
            observacoes=observacoes,
        )
        analise = self.analise_repository.criar(analise)
        self.curriculo_repository.atualizar_status(novo_curriculo, "concluido")
        return analise

    def analisar_curriculo_salvo_para_vaga(
        self,
        id_usuario: uuid.UUID,
        id_vaga: uuid.UUID,
        id_curriculo: uuid.UUID,
    ) -> Analise:
        vaga = self.vaga_repository.buscar_por_id(id_vaga)
        if vaga is None or vaga.id_usuario != id_usuario:
            raise VagaNaoEncontradaError

        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        texto_curriculo = curriculo.texto_extraido
        if not texto_curriculo:
            if curriculo.conteudo_arquivo:
                extensao = curriculo.nome_arquivo.rsplit(".", 1)[-1] if "." in curriculo.nome_arquivo else ""
                texto_curriculo = self.curriculo_parser.extrair_texto(curriculo.conteudo_arquivo, extensao)
                curriculo.texto_extraido = texto_curriculo
                self.db.commit()
            else:
                raise CurriculoArquivoNaoEncontradoError

        resultado_ia = self.ai_service_adapter.comparar_curriculo_vaga(texto_curriculo, vaga.descricao)
        pontuacao, observacoes = self._interpretar_resultado_ia(resultado_ia)

        analise = Analise(
            id_curriculo=curriculo.id_curriculo,
            id_vaga=vaga.id_vaga,
            id_usuario=id_usuario,
            pontuacao=pontuacao,
            observacoes=observacoes,
        )
        analise = self.analise_repository.criar(analise)
        return analise

    def listar_curriculos_usuario(self, id_usuario: uuid.UUID) -> list[Curriculo]:
        return self.curriculo_repository.listar_por_usuario(id_usuario)

    def obter_detalhes_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> dict:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        candidato = self.curriculo_repository.buscar_candidato(curriculo.id_curriculo)
        dados = None
        if candidato is not None:
            dados = {
                "nome": candidato.nome,
                "email": candidato.email,
                "telefone": candidato.telefone,
                "resumo": candidato.resumo,
                "formacao": candidato.formacao,
                "experiencia_profissional": candidato.experiencia_profissional,
                "habilidades": candidato.habilidades,
            }

        return {
            "id_curriculo": curriculo.id_curriculo,
            "nome_arquivo": curriculo.nome_arquivo,
            "data_upload": curriculo.data_upload,
            "status_processamento": curriculo.status_processamento,
            "texto_extraido": curriculo.texto_extraido,
            "dados": dados,
        }

    def atualizar_dados_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID, dados: dict) -> dict:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        payload = {chave: (valor if valor is not None else "") for chave, valor in (dados or {}).items()}
        self.curriculo_repository.salvar_candidato(curriculo.id_curriculo, payload)
        return self.obter_detalhes_curriculo(id_usuario, id_curriculo)

    def obter_arquivo_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> tuple[bytes, str]:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        if not curriculo.conteudo_arquivo:
            raise CurriculoArquivoNaoEncontradoError

        return curriculo.conteudo_arquivo, curriculo.nome_arquivo

    def listar_analises_usuario(self, id_usuario: uuid.UUID) -> list[Analise]:
        return self.analise_repository.listar_por_usuario(id_usuario)

    def obter_dados_edicao_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> dict:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        dados = obter_dados_curriculo_com_cache(curriculo, self.ai_service_adapter, self.curriculo_repository)

        return {
            "id_curriculo": curriculo.id_curriculo,
            "dados": dados,
            "possui_edicao": curriculo.dados_editados is not None,
            "editado_em": curriculo.editado_em,
            "sugestoes": self._obter_sugestoes_mais_recentes(id_usuario, id_curriculo),
        }

    def salvar_edicao_estruturada_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID, dados: dict) -> Curriculo:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        dados_completos = normalizar_dados_editados(dados, curriculo.texto_extraido or "")
        return self.curriculo_repository.salvar_edicao(curriculo, dados_completos)

    def salvar_edicao_texto_livre_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID, texto: str) -> Curriculo:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        dados = extrair_dados_estruturados_curriculo(self.ai_service_adapter, texto)
        dados["texto_bruto"] = texto
        return self.curriculo_repository.salvar_edicao(curriculo, dados)

    def aplicar_sugestoes_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> Curriculo:
        """Pede à IA uma versão dos dados do currículo com as sugestões da última análise
        (palavras-chave faltantes, itens a remover/reorganizar, reescritas) já aplicadas, e
        salva o resultado como `dados_editados` — pronto para revisão/exportação, sem
        precisar o usuário reescrever campo a campo manualmente.

        Levanta `NenhumaSugestaoDisponivelError` se este currículo ainda não tem nenhuma
        análise com diagnóstico salvo.
        """
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        sugestoes = self._obter_sugestoes_mais_recentes(id_usuario, id_curriculo)
        if not sugestoes:
            raise NenhumaSugestaoDisponivelError

        dados_atuais = obter_dados_curriculo_com_cache(curriculo, self.ai_service_adapter, self.curriculo_repository)
        dados_aplicados = aplicar_sugestoes_em_dados_curriculo(
            self.ai_service_adapter, dados_atuais, sugestoes, curriculo.texto_extraido or ""
        )
        return self.curriculo_repository.salvar_edicao(curriculo, dados_aplicados)

    def _obter_sugestoes_mais_recentes(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> dict | None:
        # Mesma normalização de chaves usada em NovaAnalise.jsx/HistoricoAnalises.jsx: a IA
        # (ver AIServiceAdapter._montar_prompt_comparacao) devolve "correspondentes"/"ausentes",
        # "o_que_reorganizar"/"o_que_retirar" e "sugestao_otimizada"/"motivo" — normalizamos
        # para os nomes amigáveis usados na tela de edição, com fallback para os nomes crus.
        analise = self.analise_repository.buscar_mais_recente_por_curriculo(id_usuario, id_curriculo)
        if analise is None or not analise.observacoes:
            return None
        try:
            dados = json.loads(analise.observacoes)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(dados, dict):
            return None

        palavras_chave = dados.get("palavras_chave") or {}
        diagnostico = dados.get("diagnostico_ats") or {}
        sugestoes = dados.get("sugestoes_reescrita") or []
        if not isinstance(sugestoes, list):
            sugestoes = []

        return {
            "resumo": dados.get("resumo") or dados.get("explicacao_ats") or dados.get("observacoes"),
            "palavras_chave_faltantes": palavras_chave.get("faltantes") or palavras_chave.get("ausentes") or [],
            "diagnostico_ats": {
                "pontos_fortes": diagnostico.get("pontos_fortes") or [],
                "a_reorganizar": diagnostico.get("a_reorganizar") or diagnostico.get("o_que_reorganizar") or [],
                "a_remover": diagnostico.get("a_remover") or diagnostico.get("o_que_retirar") or [],
            },
            "sugestoes_reescrita": [
                {
                    "campo": s.get("campo") if s.get("campo") in CAMPOS_CURRICULO_VALIDOS else "",
                    "trecho_original": s.get("trecho_original") or "",
                    "versao_otimizada": s.get("versao_otimizada") or s.get("sugestao_otimizada") or "",
                    "justificativa": s.get("justificativa") or s.get("motivo") or "",
                }
                for s in sugestoes
                if isinstance(s, dict)
            ],
        }

    def _interpretar_resultado_ia(self, resultado_ia: str) -> tuple[float | None, str]:
        texto = (resultado_ia or "").strip()
        if texto.startswith("```"):
            texto = texto.strip("`").strip()
            if texto.lower().startswith("json"):
                texto = texto[4:].strip()
        try:
            dados = json.loads(texto)
            pontuacao_bruta = dados.get("pontuacao")
            pontuacao = float(pontuacao_bruta) if pontuacao_bruta is not None else None
            if any(k in dados for k in ("palavras_chave", "diagnostico_ats", "sugestoes_reescrita", "resumo")):
                observacoes = json.dumps(dados, ensure_ascii=False)
            else:
                observacoes = str(dados.get("observacoes") or resultado_ia)
            return pontuacao, observacoes
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
            return None, resultado_ia
