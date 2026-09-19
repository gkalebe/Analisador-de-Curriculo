import json
import logging
import time
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 30
TEMPERATURA_PADRAO = 0.4
MAX_TENTATIVAS_GEMINI = 3
ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = 3

PERSONA_ESPECIALISTA_RH = (
    "Você é uma IA especialista sênior em Recursos Humanos, Recrutamento & Seleção e otimização de "
    "currículos para sistemas ATS (Applicant Tracking Systems), com o equivalente a mais de 15 anos de "
    "vivência avaliando currículos e conduzindo processos seletivos, atuando como o motor de "
    "inteligência do sistema Analisador de Currículos. Você combina o rigor técnico de um recrutador "
    "experiente com a didática de um mentor de carreira: suas avaliações são precisas, justas e "
    "acionáveis.\n"
    "REGRAS INEGOCIÁVEIS:\n"
    "- Baseie-se ESTRITA e SOMENTE nas informações fornecidas (currículo, vaga, conversa). Nunca invente "
    "empresas, cargos, ferramentas, certificações, anos de experiência ou qualquer outro dado ausente.\n"
    "- Toda sugestão de melhoria ou reescrita deve ser algo que o candidato consiga DEFENDER com "
    "segurança numa entrevista — nunca sugira embelezar o currículo com algo que ele não saiba explicar "
    "na prática.\n"
    "- Seja honesto mesmo quando a avaliação não for positiva: se o currículo estiver fraco ou pouco "
    "aderente à vaga, diga isso claramente e com justificativa. Elogio vazio não ajuda o candidato a "
    "conseguir a vaga.\n"
    "- Seja objetivo, profissional e específico — evite generalidades vagas como 'currículo bom' ou "
    "'precisa melhorar' sem dizer exatamente o quê e como.\n"
    "- Responda sempre em português do Brasil.\n"
)


class IAConfiguracaoAusenteError(Exception):
    pass


class IAIndisponivelError(Exception):
    pass


class AIServiceClient(ABC):
    @abstractmethod
    def gerar_resposta(self, prompt: str, temperatura: float = TEMPERATURA_PADRAO) -> str: ...


class GeminiClient(AIServiceClient):
    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def gerar_resposta(self, prompt: str, temperatura: float = TEMPERATURA_PADRAO) -> str:
        if not self.api_key:
            raise IAConfiguracaoAusenteError(
                "Defina GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env para usar a análise por IA."
            )
        import google.api_core.exceptions
        import google.generativeai as genai
        import requests.exceptions

        genai.configure(api_key=self.api_key, transport="rest")
        modelo = genai.GenerativeModel(self.model_name)

        ultimo_erro: Exception | None = None
        for tentativa in range(1, MAX_TENTATIVAS_GEMINI + 1):
            try:
                resposta = modelo.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(temperature=temperatura),
                    request_options={"timeout": TIMEOUT_SEGUNDOS, "retry": None},
                )
                return resposta.text
            except (
                google.api_core.exceptions.ServiceUnavailable,
                google.api_core.exceptions.TooManyRequests,
            ) as erro:
                # Erros transitórios de sobrecarga momentânea do modelo: vale uma nova tentativa rápida.
                ultimo_erro = erro
                logger.warning(
                    "Gemini indisponível (tentativa %d/%d): %r", tentativa, MAX_TENTATIVAS_GEMINI, erro
                )
                if tentativa < MAX_TENTATIVAS_GEMINI:
                    time.sleep(ESPERA_ENTRE_TENTATIVAS_SEGUNDOS * tentativa)
            except (google.api_core.exceptions.GoogleAPICallError, requests.exceptions.RequestException) as erro:
                # Demais erros (chave inválida, rede fora do ar etc.) não se beneficiam de retry: falha já.
                logger.error("Falha ao chamar a API do Gemini: %r", erro, exc_info=True)
                raise IAIndisponivelError(
                    f"O serviço de IA (Gemini) não respondeu em {TIMEOUT_SEGUNDOS}s ou recusou a requisição. "
                    "Tente novamente em instantes."
                ) from erro

        logger.error(
            "Falha ao chamar a API do Gemini após %d tentativas: %r",
            MAX_TENTATIVAS_GEMINI,
            ultimo_erro,
            exc_info=True,
        )
        raise IAIndisponivelError(
            f"O serviço de IA (Gemini) não respondeu em {TIMEOUT_SEGUNDOS}s ou recusou a requisição. "
            "Tente novamente em instantes."
        ) from ultimo_erro


class ClaudeClient(AIServiceClient):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self.model_name = model_name

    def gerar_resposta(self, prompt: str, temperatura: float = TEMPERATURA_PADRAO) -> str:
        if not self.api_key:
            raise IAConfiguracaoAusenteError(
                "Defina GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env para usar a análise por IA."
            )
        import anthropic

        cliente = anthropic.Anthropic(api_key=self.api_key, timeout=TIMEOUT_SEGUNDOS, max_retries=0)
        try:
            resposta = cliente.messages.create(
                model=self.model_name,
                max_tokens=1536,
                temperature=temperatura,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as erro:
            logger.error("Falha ao chamar a API do Claude: %r", erro, exc_info=True)
            raise IAIndisponivelError(
                f"O serviço de IA (Claude) não respondeu em {TIMEOUT_SEGUNDOS}s ou recusou a requisição. "
                "Tente novamente em instantes."
            ) from erro
        return "".join(bloco.text for bloco in resposta.content if bloco.type == "text")


class AIServiceAdapter:
    def __init__(self, cliente: AIServiceClient | None = None):
        if cliente is not None:
            self.cliente = cliente
        else:
            settings = get_settings()
            if settings.anthropic_api_key:
                self.cliente = ClaudeClient(settings.anthropic_api_key, settings.anthropic_model_name)
            else:
                self.cliente = GeminiClient(settings.gemini_api_key, settings.gemini_model_name)

    def analisar_curriculo(self, texto_curriculo: str) -> str:
        prompt = self._montar_prompt_analise(texto_curriculo)
        return self.cliente.gerar_resposta(prompt, temperatura=0.3)

    def comparar_curriculo_vaga(self, texto_curriculo: str, texto_vaga: str) -> str:
        prompt = self._montar_prompt_comparacao(texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.3)

    def extrair_dados_estruturados(self, texto_curriculo: str) -> str:
        prompt = self._montar_prompt_extracao(texto_curriculo)
        return self.cliente.gerar_resposta(prompt, temperatura=0.2)

    def aplicar_sugestoes_curriculo(self, dados_atuais: dict, sugestoes: dict) -> str:
        prompt = self._montar_prompt_aplicar_sugestoes(dados_atuais, sugestoes)
        return self.cliente.gerar_resposta(prompt, temperatura=0.3)

    def responder_chat(
        self,
        historico: list[tuple[str, str]],
        pergunta: str,
        texto_curriculo: str | None = None,
        texto_vaga: str | None = None,
    ) -> str:
        prompt = self._montar_prompt_chat(historico, pergunta, texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.5)

    def _montar_prompt_analise(self, texto_curriculo: str) -> str:
        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Analise o currículo abaixo e responda ESTRITAMENTE em JSON válido, sem nenhum "
            "texto fora do JSON e sem markdown, no formato exato "
            '{"pontuacao": <número de 0 a 100 avaliando a qualidade geral do currículo>, '
            '"observacoes": "<3 a 5 frases em português com pontos fortes, pontos a melhorar e '
            'sugestões objetivas>"}.\n\n'
            f"Currículo:\n{texto_curriculo}"
        )

    def _montar_prompt_comparacao(self, texto_curriculo: str, texto_vaga: str) -> str:
        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Compare o currículo do candidato com os requisitos da vaga e elabore um diagnóstico "
            "técnico de otimização ATS.\n\n"
            "DIRETRIZES ADICIONAIS:\n"
            "1. Seu objetivo é ajudar o candidato a expressar o que ele JÁ SABE ou JÁ FEZ da melhor forma "
            "(usando verbos de ação fortes, palavras-chave precisas da vaga e quantificação de impactos).\n"
            "2. Aponte termos técnicos da vaga que estão presentes e os que estão ausentes.\n"
            "3. Forneça sugestões concretas de reescrita lado a lado (trecho original vs trecho "
            "otimizado para ATS).\n\n"
            "Responda ESTRITAMENTE em JSON válido, sem nenhum texto fora do JSON e sem blocos markdown "
            "extras, seguindo este formato exato:\n"
            "{\n"
            '  "pontuacao": <número inteiro de 0 a 100 avaliando a aderência técnica do currículo à vaga>,\n'
            '  "resumo": "<2 a 3 frases explicando de forma transparente o critério da pontuação e o nível de alinhamento>",\n'
            '  "observacoes": "<resumo consolidado da análise em 3 a 5 frases>",\n'
            '  "palavras_chave": {\n'
            '    "correspondentes": ["<termo 1>", "<termo 2>"],\n'
            '    "ausentes": ["<termo 1>", "<termo 2>"]\n'
            "  },\n"
            '  "diagnostico_ats": {\n'
            '    "pontos_fortes": ["<ponto 1>", "<ponto 2>"],\n'
            '    "o_que_reorganizar": ["<orientação prática de destaque ou ordem>"],\n'
            '    "o_que_retirar": ["<termos vagos, clichês ou elementos irrelevantes para cortar>"]\n'
            "  },\n"
            '  "sugestoes_reescrita": [\n'
            "    {\n"
            '      "trecho_original": "<trecho exato do currículo original que está genérico ou fraco>",\n'
            '      "sugestao_otimizada": "<versão reescrita com verbos de ação e foco em ATS, SEM inventar fatos>",\n'
            '      "motivo": "<por que essa versão melhora a pontuação em robôs ATS e recrutadores>"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Descrição da vaga:\n{texto_vaga}\n\n"
            f"Currículo do candidato:\n{texto_curriculo}"
        )

    def _montar_prompt_extracao(self, texto_curriculo: str) -> str:
        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: A partir do texto de currículo abaixo, extraia os dados em JSON válido, sem nenhum "
            "texto fora do JSON e sem markdown, no formato exato "
            '{"nome": "<nome completo ou string vazia>", "email": "<e-mail ou string vazia>", '
            '"telefone": "<telefone ou string vazia>", "resumo": "<2 a 3 frases de resumo profissional>", '
            '"formacao": "<formação acadêmica, um item por linha, separados por \\n, ou string vazia>", '
            '"experiencia_profissional": "<experiências profissionais, um item por linha, separados '
            'por \\n, ou string vazia>", "habilidades": "<habilidades técnicas e comportamentais '
            'separadas por vírgula, ou string vazia>"}.\n\n'
            f"Currículo:\n{texto_curriculo}"
        )

    def _montar_prompt_aplicar_sugestoes(self, dados_atuais: dict, sugestoes: dict) -> str:
        diagnostico = sugestoes.get("diagnostico_ats") or {}
        reescritas = sugestoes.get("sugestoes_reescrita") or []
        linhas_reescritas = "\n".join(
            f'- Trecho original: "{item.get("trecho_original", "")}" → '
            f'Versão sugerida: "{item.get("versao_otimizada", "")}"'
            for item in reescritas
            if isinstance(item, dict) and (item.get("trecho_original") or item.get("versao_otimizada"))
        ) or "(nenhuma)"

        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Você já analisou este currículo antes e deu o diagnóstico abaixo. Agora, aplique "
            "esse diagnóstico DIRETAMENTE nos campos do currículo — não descreva o que deveria mudar, "
            "entregue os campos já corrigidos.\n\n"
            "REGRAS ESTRITAS:\n"
            "1. Remova do currículo os itens listados em 'A remover' (ex.: se for uma formação, tire a "
            "linha inteira de 'formacao'; se for um termo vago numa frase, reescreva a frase sem ele).\n"
            "2. Reorganize conforme 'A reorganizar' (ex.: ordem de destaque, agrupamento).\n"
            "3. Troque cada trecho original pela versão otimizada listada em 'Reescritas sugeridas', "
            "quando esse trecho aparecer no campo correspondente.\n"
            "4. Incorpore as 'Palavras-chave faltantes' de forma natural e verdadeira nos campos onde "
            "fizer sentido (resumo, experiência, habilidades) — SOMENTE se algo no currículo atual já "
            "sustentar aquilo; NUNCA invente uma ferramenta, empresa, cargo ou tempo de experiência que "
            "o candidato não tenha.\n"
            "5. Preserve tudo que não foi mencionado no diagnóstico exatamente como está.\n"
            "6. Responda ESTRITAMENTE em JSON válido, sem texto fora do JSON e sem markdown, no mesmo "
            "formato exato dos campos de entrada: "
            '{"nome": "...", "email": "...", "telefone": "...", "resumo": "...", "formacao": "...", '
            '"experiencia_profissional": "...", "habilidades": "..."}.\n\n'
            f"CAMPOS ATUAIS DO CURRÍCULO:\n{json.dumps(dados_atuais, ensure_ascii=False, indent=2)}\n\n"
            f"PONTOS FORTES (manter): {diagnostico.get('pontos_fortes') or []}\n"
            f"A REORGANIZAR: {diagnostico.get('a_reorganizar') or []}\n"
            f"A REMOVER: {diagnostico.get('a_remover') or []}\n"
            f"PALAVRAS-CHAVE FALTANTES: {sugestoes.get('palavras_chave_faltantes') or []}\n"
            f"REESCRITAS SUGERIDAS:\n{linhas_reescritas}\n"
        )

    def _montar_prompt_chat(
        self,
        historico: list[tuple[str, str]],
        pergunta: str,
        texto_curriculo: str | None = None,
        texto_vaga: str | None = None,
    ) -> str:
        linhas_historico = "\n".join(
            f"{'Candidato' if autor == 'usuario' else 'Assistente'}: {conteudo}" for autor, conteudo in historico
        )

        blocos_contexto = []
        if texto_curriculo:
            blocos_contexto.append(f"Currículo do candidato:\n{texto_curriculo}")
        if texto_vaga:
            blocos_contexto.append(f"Vaga em discussão:\n{texto_vaga}")
        contexto = "\n\n".join(blocos_contexto) if blocos_contexto else "(nenhum currículo ou vaga selecionado)"

        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Converse diretamente com o candidato, tirando dúvidas e dando orientações de carreira "
            "com base no contexto abaixo (currículo e/ou vaga, conforme disponível). Responda de forma "
            "direta, objetiva e natural, como em uma conversa de chat — sem soar robótico ou genérico.\n"
            "REGRAS ADICIONAIS:\n"
            "1. Se a pergunta não tiver relação com o currículo, a vaga ou a carreira do candidato, "
            "explique educadamente que você só pode ajudar com isso.\n"
            "2. Se houver currículo e vaga ao mesmo tempo, correlacione os dois na resposta quando fizer "
            "sentido (aderência, lacunas, como se preparar).\n"
            "3. Responda apenas com o texto da sua resposta, sem JSON e sem blocos markdown.\n\n"
            f"{contexto}\n\n"
            f"Conversa até aqui:\n{linhas_historico or '(nenhuma mensagem anterior)'}\n\n"
            f"Nova pergunta do candidato: {pergunta}"
        )
