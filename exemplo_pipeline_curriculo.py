"""Exemplo de uso de ponta a ponta do pipeline de geração estruturada de currículo.

Roda as 3 etapas em sequência com dados fictícios de teste:

    Etapa 1 (IA)         -> GeradorCurriculoEstruturadoIA.gerar
    Etapa 2 (validação)  -> ValidadorCurriculoEstruturado.validar_e_reparar
    Etapa 3 (montagem)   -> MontadorDocumentoCurriculo.gerar_docx / converter_para_pdf

Uso:

    python exemplo_pipeline_curriculo.py

Se `GEMINI_API_KEY` estiver configurada no `.env` (ver `app/core/config.py`),
a Etapa 1 chama a API do Gemini de verdade. Sem a chave configurada, ou se o
Gemini estiver fora do ar, o exemplo cai para um `GeradorFalso` local (só
para esta demonstração rodar em qualquer ambiente, inclusive CI, sem precisar
de credenciais) — o pipeline em si (Etapas 2 e 3) é sempre exercido de
verdade, sem nenhum mock.
"""

import sys
import tempfile
from pathlib import Path

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.adapters.ai_service.curriculo_estruturado_client import GeradorCurriculoEstruturadoIA
from app.adapters.ai_service.curriculo_schema import (
    ContatoCurriculo,
    DadosCurriculoEstruturado,
    ExperienciaCurriculo,
    FormacaoCurriculo,
    IdiomaCurriculo,
)
from app.adapters.curriculo_exporter.curriculo_template_exporter import ConversaoPdfError
from app.core.service.curriculo_estruturado_service import CurriculoEstruturadoService

# Currículo fictício "cru" — texto livre e desorganizado, como um usuário
# real costuma colar num formulário. É exatamente esse tipo de entrada que
# hoje faz a IA "reescrever" e cortar informação; aqui ela só estrutura.
INFORMACOES_BRUTAS_FICTICIAS = """
Nome: Ana Beatriz Souza. Moro em Brasília/DF. Email ana.souza@email.com,
telefone (61) 99999-0000, linkedin.com/in/anabsouza.

Sou desenvolvedora backend pleno, com 4 anos de experiência em Python e
sistemas distribuídos, focada em performance e confiabilidade de APIs.

Trabalho como Desenvolvedora Backend Pleno na Empresa XPTO desde 2023 até
hoje. Lá eu liderei a migração de um monólito para microsserviços e reduzi o
tempo de resposta da API principal em 40%. Também implementei um pipeline de
CI/CD do zero.

Antes disso fui Desenvolvedora Backend Júnior na Empresa ABC, de 2021 a 2023.
Nessa época implementei testes automatizados que subiram a cobertura de 20%
para 85% e dei suporte a incidentes de produção.

Formação: Bacharelado em Ciência da Computação pela Universidade Exemplo,
2017 a 2021.

Habilidades: Python, FastAPI, PostgreSQL, Docker, SQLAlchemy, Kubernetes.

Idiomas: Inglês avançado, Espanhol intermediário.

Certificações: AWS Certified Developer - Associate.
"""


class GeradorFalso:
    """Substitui a Etapa 1 real só quando não há `GEMINI_API_KEY` configurada
    (ou a API está fora do ar), para este exemplo rodar em qualquer máquina.
    Simula uma resposta de IA imperfeita de propósito (título profissional
    vazio) para também exercitar o retry cirúrgico da Etapa 2."""

    def gerar(self, informacoes_brutas: str) -> DadosCurriculoEstruturado:
        return DadosCurriculoEstruturado(
            nome_completo="Ana Beatriz Souza",
            titulo_profissional="",  # propositalmente vazio: aciona o retry da Etapa 2
            contato=ContatoCurriculo(
                email="ana.souza@email.com",
                telefone="(61) 99999-0000",
                linkedin="linkedin.com/in/anabsouza",
                cidade="Brasília/DF",
            ),
            resumo_profissional=(
                "Desenvolvedora backend pleno com 4 anos de experiência em Python e "
                "sistemas distribuídos, focada em performance e confiabilidade de APIs."
            ),
            experiencias=[
                ExperienciaCurriculo(
                    cargo="Desenvolvedora Backend Pleno",
                    empresa="Empresa XPTO",
                    periodo_inicio="2023",
                    periodo_fim="atual",
                    descricao_bullets=[
                        "Liderou a migração de um monólito para microsserviços",
                        "Reduziu o tempo de resposta da API principal em 40%",
                        "Implementou um pipeline de CI/CD do zero",
                    ],
                ),
                ExperienciaCurriculo(
                    cargo="Desenvolvedora Backend Júnior",
                    empresa="Empresa ABC",
                    periodo_inicio="2021",
                    periodo_fim="2023",
                    descricao_bullets=[
                        "Implementou testes automatizados, subindo a cobertura de 20% para 85%",
                        "Deu suporte a incidentes de produção",
                    ],
                ),
            ],
            formacao=[
                FormacaoCurriculo(
                    curso="Bacharelado em Ciência da Computação",
                    instituicao="Universidade Exemplo",
                    periodo="2017-2021",
                )
            ],
            habilidades_tecnicas=["Python", "FastAPI", "PostgreSQL", "Docker", "SQLAlchemy", "Kubernetes"],
            idiomas=[
                IdiomaCurriculo(idioma="Inglês", nivel="Avançado"),
                IdiomaCurriculo(idioma="Espanhol", nivel="Intermediário"),
            ],
            certificacoes=["AWS Certified Developer - Associate"],
        )

    def regenerar_campo(self, informacoes_brutas: str, nome_campo: str) -> str:
        # Simula o retry cirúrgico encontrando a informação que "faltou" na
        # primeira geração — na vida real, isso é uma segunda chamada barata
        # à API do Gemini feita por GeradorCurriculoEstruturadoIA.regenerar_campo.
        if nome_campo == "titulo_profissional":
            return "Desenvolvedora Backend Pleno"
        return ""


def _obter_service() -> CurriculoEstruturadoService:
    from app.core.config import get_settings

    if get_settings().gemini_api_key:
        print("[info] GEMINI_API_KEY configurada — Etapa 1 vai chamar a API do Gemini de verdade.\n")
        return CurriculoEstruturadoService(gerador=GeradorCurriculoEstruturadoIA())

    print("[info] GEMINI_API_KEY não configurada; usando GeradorFalso só para este exemplo rodar sem credenciais.\n")
    return CurriculoEstruturadoService(gerador=GeradorFalso())


def _gerar_com_fallback(service: CurriculoEstruturadoService, diretorio_saida: str, **kwargs):
    """Tenta a Etapa 1 real; se o Gemini estiver fora do ar, cai para o
    GeradorFalso local só para este exemplo terminar de rodar."""
    try:
        return service.gerar_curriculo_documento(diretorio_saida=diretorio_saida, **kwargs)
    except (IAConfiguracaoAusenteError, IAIndisponivelError) as erro:
        print(f"[info] Etapa 1 real falhou ({erro}); repetindo com GeradorFalso.\n")
        service_fallback = CurriculoEstruturadoService(gerador=GeradorFalso())
        return service_fallback.gerar_curriculo_documento(diretorio_saida=diretorio_saida, **kwargs)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="curriculo_exemplo_") as diretorio_saida:
        service = _obter_service()

        print("Rodando as 3 etapas do pipeline (template 'moderno', formato docx)...")
        caminho_docx, campos_com_retry = _gerar_com_fallback(
            service,
            diretorio_saida,
            informacoes_brutas=INFORMACOES_BRUTAS_FICTICIAS,
            id_template="moderno",
            formato="docx",
        )
        print(f"-> .docx gerado em: {caminho_docx}")
        print(f"-> Campos que precisaram de retry cirúrgico (Etapa 2): {campos_com_retry or 'nenhum'}")

        destino_docx = Path.cwd() / "exemplo_curriculo_gerado.docx"
        destino_docx.write_bytes(Path(caminho_docx).read_bytes())
        print(f"-> Cópia salva em: {destino_docx}")

        print("\nRodando o pipeline de novo, agora pedindo formato pdf diretamente...")
        try:
            caminho_pdf, _ = _gerar_com_fallback(
                service,
                diretorio_saida,
                informacoes_brutas=INFORMACOES_BRUTAS_FICTICIAS,
                id_template="classico",
                formato="pdf",
            )
        except ConversaoPdfError as erro:
            print(f"[info] Conversão para PDF não disponível neste ambiente: {erro}")
        else:
            destino_pdf = Path.cwd() / "exemplo_curriculo_gerado.pdf"
            destino_pdf.write_bytes(Path(caminho_pdf).read_bytes())
            print(f"-> PDF gerado em: {destino_pdf}")


if __name__ == "__main__":
    sys.exit(main() or 0)
