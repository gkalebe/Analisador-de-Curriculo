import json
import uuid

import pytest

from app.core.persistencia.models.analise import Analise
from app.core.persistencia.models.curriculo import Curriculo
from app.core.persistencia.models.vaga import Vaga
from app.core.service.analisador_service import (
    AnalisadorService,
    CurriculoNaoEncontradoError,
    DescricaoVagaMuitoLongaError,
    DescricaoVagaObrigatoriaError,
    VagaDuplicadaError,
    VagaNaoEncontradaError,
)


class VagaRepositorioFalso:
    def __init__(self):
        self.vagas: list[Vaga] = []

    def criar(self, vaga: Vaga) -> Vaga:
        vaga.id_vaga = uuid.uuid4()
        self.vagas.append(vaga)
        return vaga

    def buscar_por_id(self, id_vaga: uuid.UUID) -> Vaga | None:
        return next((vaga for vaga in self.vagas if vaga.id_vaga == id_vaga), None)

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Vaga]:
        return [vaga for vaga in self.vagas if vaga.id_usuario == id_usuario]


class CurriculoRepositorioFalso:
    def __init__(self):
        self.curriculos: list[Curriculo] = []

    def criar(self, curriculo: Curriculo) -> Curriculo:
        curriculo.id_curriculo = uuid.uuid4()
        self.curriculos.append(curriculo)
        return curriculo

    def buscar_por_id(self, id_curriculo: uuid.UUID) -> Curriculo | None:
        return next((c for c in self.curriculos if c.id_curriculo == id_curriculo), None)

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Curriculo]:
        return [c for c in self.curriculos if c.id_usuario == id_usuario]

    def atualizar_status(self, curriculo: Curriculo, status: str) -> Curriculo:
        curriculo.status_processamento = status
        return curriculo

    def salvar_edicao(self, curriculo: Curriculo, dados_editados: dict) -> Curriculo:
        curriculo.dados_editados = dados_editados
        curriculo.editado_em = "2026-09-18T00:00:00+00:00"
        return curriculo

    def salvar_dados_extraidos(self, curriculo: Curriculo, dados_extraidos: dict) -> Curriculo:
        curriculo.dados_extraidos = dados_extraidos
        return curriculo


class AnaliseRepositorioFalso:
    def __init__(self):
        self.analises: list[Analise] = []

    def criar(self, analise: Analise) -> Analise:
        analise.id_analise = uuid.uuid4()
        self.analises.append(analise)
        return analise

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Analise]:
        return [analise for analise in self.analises if analise.id_usuario == id_usuario]

    def buscar_mais_recente_por_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> Analise | None:
        candidatas = [
            a
            for a in self.analises
            if a.id_usuario == id_usuario and a.id_curriculo == id_curriculo
        ]
        if not candidatas:
            return None
        return sorted(candidatas, key=lambda a: a.data_analise or "", reverse=True)[0]


class AIServiceAdapterFalso:
    def __init__(self, resposta: str = '{"pontuacao": 90, "observacoes": "Ótimo encaixe."}'):
        self.resposta = resposta

    def comparar_curriculo_vaga(self, texto_curriculo: str, texto_vaga: str) -> str:
        return self.resposta


class CurriculoParserFalso:
    def extrair_texto(self, conteudo: bytes, extensao: str) -> str:
        return conteudo.decode("utf-8", errors="ignore")


def _criar_service_com_fake() -> tuple[AnalisadorService, VagaRepositorioFalso]:
    service = AnalisadorService(db=None)
    fake = VagaRepositorioFalso()
    service.vaga_repository = fake
    return service, fake


def _criar_service_completo_com_fakes() -> AnalisadorService:
    service = AnalisadorService(db=None)
    service.vaga_repository = VagaRepositorioFalso()
    service.curriculo_repository = CurriculoRepositorioFalso()
    service.analise_repository = AnaliseRepositorioFalso()
    service.ai_service_adapter = AIServiceAdapterFalso()
    service.curriculo_parser = CurriculoParserFalso()
    return service


def test_cadastrar_vaga_persiste_com_dados_completos():
    service, fake = _criar_service_com_fake()
    id_usuario = uuid.uuid4()

    vaga = service.cadastrar_vaga(
        id_usuario=id_usuario,
        descricao="Vaga para desenvolvedor Python.",
        titulo="Dev Python",
        requisitos="Python, SQL",
        area="Tecnologia",
    )

    assert vaga in fake.vagas
    assert vaga.titulo == "Dev Python"
    assert vaga.id_usuario == id_usuario


def test_cadastrar_vaga_aceita_apenas_descricao_obrigatoria():
    service, _ = _criar_service_com_fake()

    vaga = service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="Descrição mínima da vaga.")

    assert vaga.titulo is None
    assert vaga.requisitos is None
    assert vaga.area is None


def test_cadastrar_vaga_rejeita_descricao_vazia():
    service, _ = _criar_service_com_fake()

    with pytest.raises(DescricaoVagaObrigatoriaError):
        service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="   ")


def test_cadastrar_vaga_rejeita_descricao_acima_do_limite():
    service, _ = _criar_service_com_fake()
    service.settings = type("Settings", (), {"max_vaga_description_chars": 10})()

    with pytest.raises(DescricaoVagaMuitoLongaError):
        service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="a" * 11)


def test_cadastrar_vaga_rejeita_descricao_duplicada_do_mesmo_usuario():
    service, _ = _criar_service_com_fake()
    id_usuario = uuid.uuid4()
    service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga para desenvolvedor Python.")

    with pytest.raises(VagaDuplicadaError):
        service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga para desenvolvedor Python.")


def test_cadastrar_vaga_rejeita_descricao_duplicada_ignorando_maiusculas_e_espacos():
    service, _ = _criar_service_com_fake()
    id_usuario = uuid.uuid4()
    service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga para desenvolvedor Python.")

    with pytest.raises(VagaDuplicadaError):
        service.cadastrar_vaga(id_usuario=id_usuario, descricao="  VAGA PARA DESENVOLVEDOR PYTHON.  ")


def test_cadastrar_vaga_permite_mesma_descricao_para_usuarios_diferentes():
    service, fake = _criar_service_com_fake()

    service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="Vaga para desenvolvedor Python.")
    service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="Vaga para desenvolvedor Python.")

    assert len(fake.vagas) == 2


def test_listar_vagas_usuario_retorna_apenas_do_usuario():
    service, fake = _criar_service_com_fake()
    id_usuario = uuid.uuid4()
    outro_usuario = uuid.uuid4()
    service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga do usuário")
    service.cadastrar_vaga(id_usuario=outro_usuario, descricao="Vaga de outro usuário")

    vagas = service.listar_vagas_usuario(id_usuario)

    assert len(vagas) == 1
    assert vagas[0].id_usuario == id_usuario


def test_analisar_curriculo_para_vaga_com_sucesso():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga para dev Python.")

    analise = service.analisar_curriculo_para_vaga(
        id_usuario=id_usuario,
        id_vaga=vaga.id_vaga,
        conteudo=b"Experiencia com Python",
        nome_arquivo="curriculo.pdf",
        extensao="pdf",
    )

    assert analise.pontuacao == 90.0
    assert analise.observacoes == "Ótimo encaixe."
    assert analise.id_vaga == vaga.id_vaga
    assert analise.id_usuario == id_usuario


def test_analisar_curriculo_para_vaga_com_vaga_de_outro_usuario_lanca_erro():
    service = _criar_service_completo_com_fakes()
    dono_vaga = uuid.uuid4()
    outro_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=dono_vaga, descricao="Vaga qualquer.")

    with pytest.raises(VagaNaoEncontradaError):
        service.analisar_curriculo_para_vaga(
            id_usuario=outro_usuario,
            id_vaga=vaga.id_vaga,
            conteudo=b"conteudo",
            nome_arquivo="curriculo.pdf",
            extensao="pdf",
        )


def test_analisar_curriculo_para_vaga_com_vaga_inexistente_lanca_erro():
    service = _criar_service_completo_com_fakes()

    with pytest.raises(VagaNaoEncontradaError):
        service.analisar_curriculo_para_vaga(
            id_usuario=uuid.uuid4(),
            id_vaga=uuid.uuid4(),
            conteudo=b"conteudo",
            nome_arquivo="curriculo.pdf",
            extensao="pdf",
        )


def test_listar_analises_usuario_retorna_apenas_do_usuario():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    outro_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga.")
    service.analisar_curriculo_para_vaga(
        id_usuario=id_usuario, id_vaga=vaga.id_vaga, conteudo=b"x", nome_arquivo="a.pdf", extensao="pdf"
    )
    outra_vaga = service.cadastrar_vaga(id_usuario=outro_usuario, descricao="Vaga 2.")
    service.analisar_curriculo_para_vaga(
        id_usuario=outro_usuario, id_vaga=outra_vaga.id_vaga, conteudo=b"y", nome_arquivo="b.pdf", extensao="pdf"
    )

    analises = service.listar_analises_usuario(id_usuario)

    assert len(analises) == 1
    assert analises[0].id_usuario == id_usuario


def test_interpretar_resultado_ia_remove_bloco_markdown():
    service = _criar_service_completo_com_fakes()

    pontuacao, observacoes = service._interpretar_resultado_ia(
        '```json\n{"pontuacao": 55, "observacoes": "Parcial."}\n```'
    )

    assert pontuacao == 55.0
    assert observacoes == "Parcial."


def test_interpretar_resultado_ia_com_texto_invalido_cai_no_fallback():
    service = _criar_service_completo_com_fakes()

    pontuacao, observacoes = service._interpretar_resultado_ia("resposta que não é JSON")

    assert pontuacao is None
    assert observacoes == "resposta que não é JSON"


def test_analisar_curriculo_salvo_para_vaga_com_sucesso():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga dev Python.")

    curriculo = Curriculo(
        nome_arquivo="curriculo_salvo.pdf",
        id_usuario=id_usuario,
        status_processamento="concluido",
        texto_extraido="Texto extraído do currículo salvo",
        conteudo_arquivo=b"Conteudo do arquivo",
    )
    service.curriculo_repository.criar(curriculo)

    analise = service.analisar_curriculo_salvo_para_vaga(
        id_usuario=id_usuario,
        id_vaga=vaga.id_vaga,
        id_curriculo=curriculo.id_curriculo,
    )

    assert analise.id_curriculo == curriculo.id_curriculo
    assert analise.id_vaga == vaga.id_vaga
    assert analise.pontuacao == 90.0


def test_analisar_curriculo_salvo_curriculo_inexistente_lanca_erro():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga dev.")

    with pytest.raises(CurriculoNaoEncontradoError):
        service.analisar_curriculo_salvo_para_vaga(
            id_usuario=id_usuario,
            id_vaga=vaga.id_vaga,
            id_curriculo=uuid.uuid4(),
        )


def test_analisar_curriculo_salvo_de_outro_usuario_lanca_erro():
    service = _criar_service_completo_com_fakes()
    dono = uuid.uuid4()
    outro = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=dono, descricao="Vaga dev.")
    curriculo = Curriculo(
        nome_arquivo="c.pdf",
        id_usuario=outro,
        status_processamento="concluido",
    )
    service.curriculo_repository.criar(curriculo)

    with pytest.raises(CurriculoNaoEncontradoError):
        service.analisar_curriculo_salvo_para_vaga(
            id_usuario=dono,
            id_vaga=vaga.id_vaga,
            id_curriculo=curriculo.id_curriculo,
        )


def test_interpretar_resultado_ia_preserva_estrutura_completa_ats():
    service, _ = _criar_service_com_fake()
    payload_ia = json.dumps({
        "pontuacao": 85,
        "resumo": "Alta compatibilidade com os requisitos técnicos.",
        "observacoes": "Currículo bem estruturado.",
        "palavras_chave": {
            "correspondentes": ["Python", "FastAPI"],
            "ausentes": ["Kubernetes"],
        },
        "diagnostico_ats": {
            "pontos_fortes": ["Experiência sólida"],
            "o_que_reorganizar": ["Mover resumo para o topo"],
            "o_que_retirar": ["Clichês genéricos"],
        },
        "sugestoes_reescrita": [
            {
                "trecho_original": "Fiz deploy de backend",
                "sugestao_otimizada": "Orquestrei implantações de microsserviços",
                "motivo": "Uso de verbo de ação",
            }
        ],
    })

    pontuacao, observacoes = service._interpretar_resultado_ia(payload_ia)

    assert pontuacao == 85.0
    dados_interpretados = json.loads(observacoes)
    assert dados_interpretados["pontuacao"] == 85
    assert dados_interpretados["palavras_chave"]["correspondentes"] == ["Python", "FastAPI"]
    assert len(dados_interpretados["sugestoes_reescrita"]) == 1


def test_obter_dados_edicao_curriculo_sem_edicao_extrai_via_ia():
    service = _criar_service_completo_com_fakes()
    service.ai_service_adapter.extrair_dados_estruturados = lambda texto: (
        '{"nome": "Ana Silva", "email": "", "telefone": "", "resumo": "", '
        '"formacao": "", "experiencia_profissional": "", "habilidades": ""}'
    )
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        nome_arquivo="c.pdf", id_usuario=id_usuario, status_processamento="concluido", texto_extraido="texto bruto"
    )
    service.curriculo_repository.criar(curriculo)

    resultado = service.obter_dados_edicao_curriculo(id_usuario, curriculo.id_curriculo)

    assert resultado["possui_edicao"] is False
    assert resultado["dados"]["nome"] == "Ana Silva"
    assert resultado["sugestoes"] is None


def test_obter_dados_edicao_curriculo_com_edicao_usa_dados_salvos_e_sugestoes():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga dev Python.")
    curriculo = Curriculo(
        nome_arquivo="c.pdf",
        id_usuario=id_usuario,
        status_processamento="concluido",
        texto_extraido="texto bruto",
        dados_editados={"nome": "Ana Editada"},
    )
    service.curriculo_repository.criar(curriculo)

    observacoes = json.dumps(
        {
            "resumo": "Boa aderência.",
            "palavras_chave": {"correspondentes": ["Python"], "ausentes": ["Docker"]},
            "diagnostico_ats": {
                "pontos_fortes": ["Experiência sólida"],
                "o_que_reorganizar": ["Mover resumo para o topo"],
                "o_que_retirar": ["Clichês"],
            },
            "sugestoes_reescrita": [
                {
                    "trecho_original": "Fiz deploy",
                    "sugestao_otimizada": "Orquestrei implantações",
                    "motivo": "Verbo de ação",
                }
            ],
        }
    )
    analise = Analise(
        id_curriculo=curriculo.id_curriculo,
        id_vaga=vaga.id_vaga,
        id_usuario=id_usuario,
        pontuacao=80.0,
        observacoes=observacoes,
    )
    service.analise_repository.criar(analise)

    resultado = service.obter_dados_edicao_curriculo(id_usuario, curriculo.id_curriculo)

    assert resultado["possui_edicao"] is True
    assert resultado["dados"]["nome"] == "Ana Editada"
    assert resultado["sugestoes"]["palavras_chave_faltantes"] == ["Docker"]
    assert resultado["sugestoes"]["diagnostico_ats"]["a_reorganizar"] == ["Mover resumo para o topo"]
    assert resultado["sugestoes"]["diagnostico_ats"]["a_remover"] == ["Clichês"]
    assert resultado["sugestoes"]["sugestoes_reescrita"][0]["versao_otimizada"] == "Orquestrei implantações"
    assert resultado["sugestoes"]["sugestoes_reescrita"][0]["justificativa"] == "Verbo de ação"


def test_obter_dados_edicao_curriculo_inexistente_lanca_erro():
    service = _criar_service_completo_com_fakes()

    with pytest.raises(CurriculoNaoEncontradoError):
        service.obter_dados_edicao_curriculo(uuid.uuid4(), uuid.uuid4())


def test_obter_dados_edicao_curriculo_reaproveita_extracao_em_cache_sem_chamar_ia_de_novo():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        nome_arquivo="c.pdf", id_usuario=id_usuario, status_processamento="concluido", texto_extraido="texto bruto"
    )
    service.curriculo_repository.criar(curriculo)
    chamadas = []
    service.ai_service_adapter.extrair_dados_estruturados = lambda texto: (
        chamadas.append(texto)
        or '{"nome": "Ana Silva", "email": "", "telefone": "", "resumo": "", '
        '"formacao": "", "experiencia_profissional": "", "habilidades": ""}'
    )

    primeiro = service.obter_dados_edicao_curriculo(id_usuario, curriculo.id_curriculo)
    segundo = service.obter_dados_edicao_curriculo(id_usuario, curriculo.id_curriculo)

    assert primeiro["dados"]["nome"] == "Ana Silva"
    assert segundo["dados"]["nome"] == "Ana Silva"
    assert len(chamadas) == 1
    assert curriculo.dados_extraidos["nome"] == "Ana Silva"


def test_salvar_edicao_estruturada_curriculo_persiste_dados_completos():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        nome_arquivo="c.pdf", id_usuario=id_usuario, status_processamento="concluido", texto_extraido="texto bruto"
    )
    service.curriculo_repository.criar(curriculo)

    resultado = service.salvar_edicao_estruturada_curriculo(
        id_usuario, curriculo.id_curriculo, {"nome": "Ana Nova", "resumo": "Resumo novo"}
    )

    assert resultado.dados_editados["nome"] == "Ana Nova"
    assert resultado.dados_editados["resumo"] == "Resumo novo"
    assert resultado.dados_editados["texto_bruto"] == "texto bruto"


def test_salvar_edicao_estruturada_curriculo_inexistente_lanca_erro():
    service = _criar_service_completo_com_fakes()

    with pytest.raises(CurriculoNaoEncontradoError):
        service.salvar_edicao_estruturada_curriculo(uuid.uuid4(), uuid.uuid4(), {"nome": "X"})


def test_salvar_edicao_texto_livre_curriculo_extrai_via_ia_e_persiste():
    service = _criar_service_completo_com_fakes()
    service.ai_service_adapter.extrair_dados_estruturados = lambda texto: (
        '{"nome": "Ana via texto", "email": "", "telefone": "", "resumo": "", '
        '"formacao": "", "experiencia_profissional": "", "habilidades": ""}'
    )
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        nome_arquivo="c.pdf", id_usuario=id_usuario, status_processamento="concluido", texto_extraido="texto antigo"
    )
    service.curriculo_repository.criar(curriculo)

    resultado = service.salvar_edicao_texto_livre_curriculo(id_usuario, curriculo.id_curriculo, "texto colado novo")

    assert resultado.dados_editados["nome"] == "Ana via texto"
    assert resultado.dados_editados["texto_bruto"] == "texto colado novo"

