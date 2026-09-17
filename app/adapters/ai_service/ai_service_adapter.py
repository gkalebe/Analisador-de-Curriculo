from abc import ABC, abstractmethod

from app.core.config import get_settings

TIMEOUT_SEGUNDOS = 30
TEMPERATURA_PADRAO = 0.4

PERSONA_ESPECIALISTA_RH = (
    "Você é uma IA especialista sênior em Recursos Humanos, Recrutamento & Seleção e otimização de "
    "currículos para sistemas ATS (Applicant Tracking Systems), atuando como o motor de inteligência "
    "do sistema Analisador de Currículos. Você combina o rigor técnico de um recrutador experiente com "
    "a didática de um mentor de carreira: suas avaliações são precisas, justas e acionáveis.\n"
    "REGRAS INEGOCIÁVEIS:\n"
    "- Baseie-se ESTRITA e SOMENTE nas informações fornecidas (currículo, vaga, conversa). Nunca invente "
    "empresas, cargos, ferramentas, certificações, anos de experiência ou qualquer outro dado ausente.\n"
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
        try:
            resposta = modelo.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperatura),
                request_options={"timeout": TIMEOUT_SEGUNDOS},
            )
        except (google.api_core.exceptions.GoogleAPICallError, requests.exceptions.RequestException) as erro:
            raise IAIndisponivelError(
                f"O serviço de IA (Gemini) não respondeu em {TIMEOUT_SEGUNDOS}s ou recusou a requisição. "
                "Tente novamente em instantes."
            ) from erro
        return resposta.text


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

        cliente = anthropic.Anthropic(api_key=self.api_key, timeout=TIMEOUT_SEGUNDOS)
        try:
            resposta = cliente.messages.create(
                model=self.model_name,
                max_tokens=1536,
                temperature=temperatura,
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
        return self.cliente.gerar_resposta(prompt, temperatura=0.3)

    def comparar_curriculo_vaga(self, texto_curriculo: str, texto_vaga: str) -> str:
        prompt = self._montar_prompt_comparacao(texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.3)

    def extrair_dados_estruturados(self, texto_curriculo: str) -> str:
        prompt = self._montar_prompt_extracao(texto_curriculo)
        return self.cliente.gerar_resposta(prompt, temperatura=0.2)

    def responder_chat(
        self,
        texto_curriculo: str | None,
        historico: list[tuple[str, str]],
        pergunta: str,
        texto_vaga: str | None = None,
    ) -> str:
        prompt = self._montar_prompt_chat(texto_curriculo, historico, pergunta, texto_vaga=texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.5)

    def responder_chat_curriculo(
        self, texto_curriculo: str, historico: list[tuple[str, str]], pergunta: str
    ) -> str:
        return self.responder_chat(texto_curriculo, historico, pergunta, texto_vaga=None)

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

    def _montar_prompt_chat(
        self,
        texto_curriculo: str | None,
        historico: list[tuple[str, str]],
        pergunta: str,
        texto_vaga: str | None = None,
    ) -> str:
        linhas_historico = "\n".join(
            f"{'Candidato' if autor == 'usuario' else 'Assistente'}: {conteudo}" for autor, conteudo in historico
        )
        historico_formatado = (
            f"Conversa até aqui:\n{linhas_historico or '(nenhuma mensagem anterior)'}\n\n"
            f"Nova pergunta do candidato: {pergunta}"
        )

        if texto_curriculo and texto_vaga:
            return (
                f"{PERSONA_ESPECIALISTA_RH}\n"
                "TAREFA: Converse diretamente com o candidato dono do currículo abaixo sobre a vaga de "
                "interesse informada. Oriente-o de forma personalizada correlacionando o perfil dele com os "
                "requisitos e qualificações da vaga. Aponte pontos fortes, competências ausentes ou que precisam "
                "ser desenvolvidas, sugestões de como destacar suas experiências para esta vaga específica e "
                "possíveis perguntas técnicas e comportamentais que ele poderá enfrentar no processo seletivo.\n"
                "Responda de forma direta, encorajadora, objetiva e natural, como em uma conversa de chat.\n\n"
                "REGRAS ADICIONAIS:\n"
                "1. Se a pergunta não tiver relação com o currículo, a vaga selecionada ou a carreira do candidato, "
                "explique educadamente que você só pode orientar sobre esta oportunidade e a preparação profissional dele.\n"
                "2. Responda apenas com o texto da sua resposta, sem JSON e sem blocos de código markdown desnecessários.\n\n"
                f"Currículo do candidato:\n{texto_curriculo}\n\n"
                f"Vaga de interesse:\n{texto_vaga}\n\n"
                f"{historico_formatado}"
            )
        elif texto_vaga:
            return (
                f"{PERSONA_ESPECIALISTA_RH}\n"
                "TAREFA: Converse diretamente com o candidato tirando dúvidas sobre a vaga de emprego cadastrada abaixo. "
                "Esclareça o perfil ideal exigido pela empresa, os principais requisitos e tecnologias, responsabilidades "
                "do cargo e forneça dicas estratégicas de como o candidato deve se preparar para o processo seletivo dessa vaga.\n"
                "Responda de forma direta, objetiva e natural, como em uma conversa de chat.\n\n"
                "REGRAS ADICIONAIS:\n"
                "1. Se a pergunta não tiver relação com a vaga cadastrada ou processos seletivos nessa área, explique "
                "educadamente que você está disponível para tirar dúvidas sobre essa oportunidade de carreira.\n"
                "2. Responda apenas com o texto da sua resposta, sem JSON e sem blocos markdown desnecessários.\n\n"
                f"Vaga cadastrada:\n{texto_vaga}\n\n"
                f"{historico_formatado}"
            )
        else:
            return (
                f"{PERSONA_ESPECIALISTA_RH}\n"
                "TAREFA: Converse diretamente com o candidato dono do currículo abaixo, tirando dúvidas e "
                "dando orientações de carreira baseadas nesse currículo. Responda de forma direta, objetiva "
                "e natural, como em uma conversa de chat — sem soar robótico ou genérico.\n"
                "REGRAS ADICIONAIS:\n"
                "1. Se a pergunta não tiver relação com o currículo ou a carreira do candidato, explique "
                "educadamente que você só pode ajudar com isso.\n"
                "2. Responda apenas com o texto da sua resposta, sem JSON e sem blocos markdown.\n\n"
                f"Currículo do candidato:\n{texto_curriculo or ''}\n\n"
                f"{historico_formatado}"
            )
