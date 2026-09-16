import json
import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.curriculo_parser.curriculo_parser import CurriculoParser
from app.core.config import get_settings
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models import Analise, Curriculo, Vaga
from app.core.persistencia.vaga_repository import VagaRepository


class DescricaoVagaObrigatoriaError(Exception):
    pass


class DescricaoVagaMuitoLongaError(Exception):
    pass


class VagaNaoEncontradaError(Exception):
    pass


class CurriculoNaoEncontradoError(Exception):
    pass


class CurriculoArquivoNaoEncontradoError(Exception):
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

        return {
            "id_curriculo": str(novo_curriculo.id_curriculo),
            "nome_arquivo": nome_arquivo,
            "tamanho_texto_extraido": len(texto_extraido),
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

        return {
            "id_curriculo": curriculo.id_curriculo,
            "nome_arquivo": curriculo.nome_arquivo,
            "data_upload": curriculo.data_upload,
            "status_processamento": curriculo.status_processamento,
            "texto_extraido": curriculo.texto_extraido,
        }

    def obter_arquivo_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> tuple[bytes, str]:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        if not curriculo.conteudo_arquivo:
            raise CurriculoArquivoNaoEncontradoError

        return curriculo.conteudo_arquivo, curriculo.nome_arquivo

    def listar_analises_usuario(self, id_usuario: uuid.UUID) -> list[Analise]:
        return self.analise_repository.listar_por_usuario(id_usuario)

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
