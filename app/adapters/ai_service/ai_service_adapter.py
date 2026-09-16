from abc import ABC, abstractmethod

from app.core.config import get_settings

TIMEOUT_SEGUNDOS = 30


class IAConfiguracaoAusenteError(Exception):
    pass


class IAIndisponivelError(Exception):
    pass


class AIServiceClient(ABC):
    @abstractmethod
    def gerar_resposta(self, prompt: str) -> str: ...


class GeminiClient(AIServiceClient):
    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def gerar_resposta(self, prompt: str) -> str:
        if not self.api_key:
            raise IAConfiguracaoAusenteError(
                "Defina GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env para usar a análise por IA."
            )
        import google.api_core.exceptions
        import google.generativeai as genai

        genai.configure(api_key=self.api_key, transport="rest")
        modelo = genai.GenerativeModel(self.model_name)
        try:
            resposta = modelo.generate_content(prompt, request_options={"timeout": TIMEOUT_SEGUNDOS})
        except google.api_core.exceptions.GoogleAPICallError as erro:
            raise IAIndisponivelError(
                f"O serviço de IA (Gemini) não respondeu em {TIMEOUT_SEGUNDOS}s ou recusou a requisição. "
                "Tente novamente em instantes."
            ) from erro
        return resposta.text


class ClaudeClient(AIServiceClient):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self.model_name = model_name

    def gerar_resposta(self, prompt: str) -> str:
        if not self.api_key:
            raise IAConfiguracaoAusenteError(
                "Defina GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env para usar a análise por IA."
            )
        import anthropic

        cliente = anthropic.Anthropic(api_key=self.api_key, timeout=TIMEOUT_SEGUNDOS)
        try:
            resposta = cliente.messages.create(
                model=self.model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as erro:
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
        return self.cliente.gerar_resposta(prompt)

    def comparar_curriculo_vaga(self, texto_curriculo: str, texto_vaga: str) -> str:
        prompt = self._montar_prompt_comparacao(texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt)

    def extrair_dados_estruturados(self, texto_curriculo: str) -> str:
        prompt = self._montar_prompt_extracao(texto_curriculo)
        return self.cliente.gerar_resposta(prompt)

    def _montar_prompt_analise(self, texto_curriculo: str) -> str:
        return (
            "Você é um recrutador experiente. Analise o currículo abaixo e responda ESTRITAMENTE em "
            "JSON válido, sem nenhum texto fora do JSON e sem markdown, no formato exato "
            '{"pontuacao": <número de 0 a 100 avaliando a qualidade geral do currículo>, '
            '"observacoes": "<3 a 5 frases em português com pontos fortes, pontos a melhorar e '
            'sugestões objetivas>"}.\n\n'
            f"Currículo:\n{texto_curriculo}"
        )

    def _montar_prompt_comparacao(self, texto_curriculo: str, texto_vaga: str) -> str:
        return (
            "Você é um especialista em recrutamento técnico e algoritmos de triagem ATS (Applicant Tracking Systems).\n"
            "Compare o currículo do candidato com os requisitos da vaga e elabore um diagnóstico técnico de otimização ATS.\n\n"
            "DIRETRIZES FUNDAMENTAIS DE VERACIDADE (REGRAS ESTRITAS):\n"
            "1. NUNCA invente ferramentas, empresas, cargos, anos de experiência ou fatos não citados no currículo original.\n"
            "2. Seu objetivo é ajudar o candidato a expressar o que ele JÁ SABE ou JÁ FEZ da melhor forma (usando verbos de ação fortes, palavras-chave precisas da vaga e quantificação de impactos).\n"
            "3. Aponte termos técnicos da vaga que estão presentes e os que estão ausentes.\n"
            "4. Forneça sugestões concretas de reescrita lado a lado (trecho original vs trecho otimizado para ATS).\n\n"
            "Responda ESTRITAMENTE em JSON válido, sem nenhum texto fora do JSON e sem blocos markdown extras, seguindo este formato exato:\n"
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
            "Você é um assistente de RH. A partir do texto de currículo abaixo, extraia os dados em "
            "JSON válido, sem nenhum texto fora do JSON e sem markdown, no formato exato "
            '{"nome": "<nome completo ou string vazia>", "email": "<e-mail ou string vazia>", '
            '"telefone": "<telefone ou string vazia>", "resumo": "<2 a 3 frases de resumo profissional>", '
            '"formacao": "<formação acadêmica, um item por linha, separados por \\n, ou string vazia>", '
            '"experiencia_profissional": "<experiências profissionais, um item por linha, separados '
            'por \\n, ou string vazia>", "habilidades": "<habilidades técnicas e comportamentais '
            'separadas por vírgula, ou string vazia>"}.\n\n'
            f"Currículo:\n{texto_curriculo}"
        )
