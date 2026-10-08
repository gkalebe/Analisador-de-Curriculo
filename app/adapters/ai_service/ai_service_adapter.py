import logging
import time
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 30
# Chamadas cujas respostas são grandes (análise + currículo estruturado, extração completa)
# precisam de mais tempo de leitura: com o modelo sob carga, 30s virava ReadTimeout.
TIMEOUT_RESPOSTA_LONGA_SEGUNDOS = 90
# Um currículo completo em JSON estruturado (experiências com bullets, formação, idiomas,
# seções adicionais) passa fácil de 1.5k tokens; cortar a resposta no meio invalida o JSON
# inteiro e a extração cai silenciosamente em campos vazios.
MAX_TOKENS_RESPOSTA = 4096
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
    def gerar_resposta(
        self, prompt: str, temperatura: float = TEMPERATURA_PADRAO, timeout_segundos: int = TIMEOUT_SEGUNDOS
    ) -> str: ...


class GeminiClient(AIServiceClient):
    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def gerar_resposta(
        self, prompt: str, temperatura: float = TEMPERATURA_PADRAO, timeout_segundos: int = TIMEOUT_SEGUNDOS
    ) -> str:
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
                    request_options={"timeout": timeout_segundos, "retry": None},
                )
                return resposta.text
            except (
                google.api_core.exceptions.ServiceUnavailable,
                google.api_core.exceptions.TooManyRequests,
                google.api_core.exceptions.DeadlineExceeded,
                requests.exceptions.Timeout,
            ) as erro:
                # Erros transitórios (sobrecarga momentânea ou timeout de leitura): vale nova tentativa.
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
                    f"O serviço de IA (Gemini) não respondeu em {timeout_segundos}s ou recusou a requisição. "
                    "Tente novamente em instantes."
                ) from erro

        logger.error(
            "Falha ao chamar a API do Gemini após %d tentativas: %r",
            MAX_TENTATIVAS_GEMINI,
            ultimo_erro,
            exc_info=True,
        )
        raise IAIndisponivelError(
            f"O serviço de IA (Gemini) não respondeu em {timeout_segundos}s ou recusou a requisição. "
            "Tente novamente em instantes."
        ) from ultimo_erro


class ClaudeClient(AIServiceClient):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self.model_name = model_name

    def gerar_resposta(
        self, prompt: str, temperatura: float = TEMPERATURA_PADRAO, timeout_segundos: int = TIMEOUT_SEGUNDOS
    ) -> str:
        if not self.api_key:
            raise IAConfiguracaoAusenteError(
                "Defina GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env para usar a análise por IA."
            )
        import anthropic

        cliente = anthropic.Anthropic(api_key=self.api_key, timeout=timeout_segundos, max_retries=0)
        try:
            resposta = cliente.messages.create(
                model=self.model_name,
                max_tokens=MAX_TOKENS_RESPOSTA,
                temperature=temperatura,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as erro:
            logger.error("Falha ao chamar a API do Claude: %r", erro, exc_info=True)
            raise IAIndisponivelError(
                f"O serviço de IA (Claude) não respondeu em {timeout_segundos}s ou recusou a requisição. "
                "Tente novamente em instantes."
            ) from erro
        return "".join(bloco.text for bloco in resposta.content if bloco.type == "text")


FORMATO_JSON_CURRICULO_ESTRUTURADO = """{
  "nome_completo": "<nome completo ou string vazia>",
  "titulo_profissional": "<cargo/título que resume o perfil, ou string vazia>",
  "contato": {"email": "", "telefone": "", "linkedin": "", "cidade": ""},
  "resumo_profissional": "<resumo/objetivo profissional, ou string vazia>",
  "experiencias": [
    {
      "cargo": "", "empresa": "", "periodo_inicio": "", "periodo_fim": "",
      "descricao_bullets": ["<cada responsabilidade/conquista descrita, uma por item>"]
    }
  ],
  "formacao": [{"curso": "", "instituicao": "", "periodo": ""}],
  "habilidades_tecnicas": ["<uma habilidade por item>"],
  "idiomas": [{"idioma": "", "nivel": ""}],
  "certificacoes": ["<uma certificação/curso por item>"],
  "secoes_adicionais": [
    {"titulo": "<título da seção como está no currículo, ex.: Projetos, Voluntariado, Publicações>", "itens": ["<um item por entrada>"]}
  ]
}"""


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
        """Análise currículo × vaga. A resposta traz também o currículo estruturado completo
        (`curriculo_estruturado`), para o fluxo "Transformar em Template ATS" não precisar de
        uma segunda requisição de extração — ver AnalisadorService."""
        prompt = self._montar_prompt_comparacao(texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.3, timeout_segundos=TIMEOUT_RESPOSTA_LONGA_SEGUNDOS)

    def extrair_dados_estruturados(self, texto_curriculo: str) -> str:
        prompt = self._montar_prompt_extracao(texto_curriculo)
        return self.cliente.gerar_resposta(prompt, temperatura=0.2, timeout_segundos=TIMEOUT_RESPOSTA_LONGA_SEGUNDOS)

    def responder_chat(
        self,
        historico: list[tuple[str, str]],
        pergunta: str,
        texto_curriculo: str | None = None,
        texto_vaga: str | None = None,
    ) -> str:
        prompt = self._montar_prompt_chat(historico, pergunta, texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.5)

    def gerar_perguntas_entrevista(self, texto_vaga: str) -> str:
        prompt = self._montar_prompt_perguntas_entrevista(texto_vaga)
        return self.cliente.gerar_resposta(prompt, temperatura=0.6)

    def avaliar_resposta_entrevista(self, texto_vaga: str, pergunta: str, tipo: str, resposta: str) -> str:
        prompt = self._montar_prompt_feedback_entrevista(texto_vaga, pergunta, tipo, resposta)
        return self.cliente.gerar_resposta(prompt, temperatura=0.3)

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
            "otimizado para ATS).\n"
            "4. Para CADA sugestão de reescrita, identifique com certeza em qual campo do currículo "
            "estruturado o trecho original está: 'resumo' (resumo profissional), 'formacao' (formação "
            "acadêmica), 'experiencia_profissional' (experiências de trabalho) ou 'habilidades' "
            "(habilidades técnicas/comportamentais). Use EXATAMENTE um desses 4 valores no campo "
            "\"campo\" — nunca deixe em branco e nunca invente um valor fora dessa lista.\n"
            "5. Primeiro preencha \"curriculo_estruturado\": estruture o currículo INTEIRO como foi enviado "
            "(sem aplicar nenhuma sugestão ainda), preservando TODO o conteúdo: todas as experiências com "
            "todas as suas responsabilidades em 'descricao_bullets' (uma por item), todas as formações, "
            "habilidades (uma por item), idiomas, certificações, e qualquer outra seção em "
            "'secoes_adicionais' com o título original. NUNCA resuma, corte ou invente. Campo sem "
            "informação: string vazia ou lista vazia.\n"
            "6. As sugestões serão aplicadas AUTOMATICAMENTE, por busca de texto, em cima desse "
            "\"curriculo_estruturado\" — não há revisão humana entre a sua resposta e a substituição. Por "
            "isso, cada \"trecho_original\" deve ser a cópia IDÊNTICA (mesmas palavras, pontuação, "
            "maiúsculas e acentos) de UM item que você mesmo escreveu em \"curriculo_estruturado\": um "
            "bullet inteiro de 'descricao_bullets', uma frase inteira de 'resumo_profissional', um item "
            "de 'habilidades_tecnicas' ou o 'curso' de uma formação. Nunca parafraseie, nunca junte dois "
            "itens num trecho só, nunca cite um pedaço de palavra. Se o trecho não bater exatamente, a "
            "sugestão é descartada.\n"
            "7. \"sugestao_otimizada\" substitui o trecho inteiro no mesmo lugar: deve ser um texto "
            "completo e autossuficiente, no mesmo formato do item (um bullet continua um bullet; se fizer "
            "sentido dividir em dois bullets, separe-os com quebra de linha \\n).\n"
            "8. Palavras-chave da vaga ausentes: quando o currículo JÁ SUSTENTA a competência (ex.: o "
            "candidato descreve uso de containers e a vaga pede Docker; descreve testes automatizados e "
            "a vaga pede TDD), crie uma sugestão de reescrita que incorpore o termo exato da vaga no "
            "trecho correspondente — essa é a forma de a palavra-chave entrar no currículo. Palavras-chave "
            "SEM nenhuma sustentação no currículo ficam apenas em 'ausentes' e NUNCA entram em uma "
            "reescrita.\n"
            "9. \"o_que_retirar\" só aceita ITENS INTEIROS a remover, copiados idênticos de "
            "\"curriculo_estruturado\" (uma formação irrelevante, uma habilidade genérica, um bullet "
            "redundante, uma certificação obsoleta). Se o problema é um termo vago ou clichê DENTRO de uma "
            "frase ('proativo', 'dinâmico', 'responsável por'), NÃO o coloque em 'o_que_retirar': crie uma "
            "sugestão de reescrita com a frase inteira como trecho original e a versão sem o termo.\n"
            "10. Cobertura: gere entre 4 e 10 sugestões de reescrita, priorizando o resumo profissional e "
            "os bullets de experiência mais fracos ou menos alinhados à vaga, uma sugestão por item. Se o "
            "currículo for curto e não houver 4 trechos a melhorar, gere menos — nunca invente problemas.\n"
            "11. \"o_que_reorganizar\" é orientação para o candidato ler (a ordem das seções no documento "
            "final é fixa, no padrão ATS); seja breve. Mantenha \"motivo\" em 1 frase curta.\n\n"
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
            '    "o_que_retirar": ["<item INTEIRO a remover, copiado idêntico de curriculo_estruturado>"]\n'
            "  },\n"
            '  "sugestoes_reescrita": [\n'
            "    {\n"
            '      "campo": "<resumo | formacao | experiencia_profissional | habilidades>",\n'
            '      "trecho_original": "<cópia idêntica de UM item de curriculo_estruturado (bullet, frase do resumo, habilidade ou curso)>",\n'
            '      "sugestao_otimizada": "<versão reescrita completa que substitui o item, com verbos de ação e termos da vaga que o currículo sustenta, SEM inventar fatos>",\n'
            '      "motivo": "<1 frase: por que melhora em ATS/recrutadores>"\n'
            "    }\n"
            "  ],\n"
            f'  "curriculo_estruturado": {FORMATO_JSON_CURRICULO_ESTRUTURADO}\n'
            "}\n\n"
            f"Descrição da vaga:\n{texto_vaga}\n\n"
            f"Currículo do candidato:\n{texto_curriculo}"
        )

    def _montar_prompt_extracao(self, texto_curriculo: str) -> str:
        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Estruture o currículo abaixo no JSON indicado, preservando TODO o conteúdo. O "
            "resultado será usado para remontar o MESMO currículo em um template ATS — nada pode "
            "ser perdido, resumido ou inventado.\n\n"
            "REGRAS ESTRITAS:\n"
            "1. NUNCA resuma, corte ou omita experiências, formações, habilidades, idiomas, "
            "certificações, projetos ou qualquer outro item do currículo. Liste TODOS, um por item.\n"
            "2. Em cada experiência, coloque TODAS as responsabilidades/conquistas descritas em "
            "'descricao_bullets', uma por item, mantendo o texto do candidato (pode corrigir "
            "pontuação, nunca o sentido).\n"
            "3. Toda seção do currículo que não se encaixe nos campos fixos (projetos, voluntariado, "
            "publicações, prêmios, cursos livres, objetivo, informações adicionais etc.) deve entrar "
            "em 'secoes_adicionais' com o MESMO título usado no currículo e todos os seus itens.\n"
            "4. NUNCA invente dados. Campo sem informação no currículo: string vazia \"\" ou lista "
            "vazia [].\n"
            "5. Mantenha o idioma original do currículo.\n"
            "6. Responda ESTRITAMENTE em JSON válido, sem nenhum texto fora do JSON e sem markdown, "
            "no formato exato:\n"
            f"{FORMATO_JSON_CURRICULO_ESTRUTURADO}\n\n"
            f"Currículo:\n{texto_curriculo}"
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

    def _montar_prompt_perguntas_entrevista(self, texto_vaga: str) -> str:
        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Monte um roteiro de simulação de entrevista de emprego para a vaga descrita abaixo, "
            "para o candidato treinar antes do processo seletivo real.\n\n"
            "DIRETRIZES:\n"
            "1. Gere exatamente 2 perguntas do tipo comportamental (sobre experiências passadas e soft "
            "skills, ex.: trabalho em equipe, conflitos, liderança), 2 do tipo técnica (sobre "
            "conhecimentos e ferramentas específicos exigidos pela vaga) e 2 do tipo situacional "
            "(cenários hipotéticos relacionados ao dia a dia da vaga).\n"
            "2. As perguntas devem ser específicas ao conteúdo da vaga, nunca genéricas.\n"
            "3. Responda ESTRITAMENTE em JSON válido, sem nenhum texto fora do JSON e sem blocos "
            "markdown, no formato exato:\n"
            "{\n"
            '  "perguntas": [\n'
            '    {"tipo": "comportamental", "texto": "<pergunta>"},\n'
            '    {"tipo": "tecnica", "texto": "<pergunta>"},\n'
            '    {"tipo": "situacional", "texto": "<pergunta>"}\n'
            "  ]\n"
            "}\n\n"
            f"Descrição da vaga:\n{texto_vaga}"
        )

    def _montar_prompt_feedback_entrevista(self, texto_vaga: str, pergunta: str, tipo: str, resposta: str) -> str:
        return (
            f"{PERSONA_ESPECIALISTA_RH}\n"
            "TAREFA: Avalie a resposta do candidato a uma pergunta de simulação de entrevista para a "
            "vaga descrita abaixo, dando feedback construtivo para ele treinar.\n\n"
            "DIRETRIZES:\n"
            "1. Avalie a resposta em 4 dimensões: clareza (a resposta é fácil de entender e bem "
            "estruturada?), objetividade (vai direto ao ponto, sem enrolação?), coerência (a resposta "
            "faz sentido com o que foi perguntado e é internamente consistente?) e alinhamento "
            "(quão aderente a resposta está aos requisitos e ao perfil da vaga?).\n"
            "2. Para cada dimensão, dê uma nota de 0 a 10 e um comentário curto (1 a 2 frases) e "
            "acionável.\n"
            "3. Dê também um feedback geral (2 a 3 frases) resumindo o principal ponto a melhorar.\n"
            "4. Responda ESTRITAMENTE em JSON válido, sem nenhum texto fora do JSON e sem blocos "
            "markdown, no formato exato:\n"
            "{\n"
            '  "clareza": {"nota": <0 a 10>, "comentario": "<comentário>"},\n'
            '  "objetividade": {"nota": <0 a 10>, "comentario": "<comentário>"},\n'
            '  "coerencia": {"nota": <0 a 10>, "comentario": "<comentário>"},\n'
            '  "alinhamento": {"nota": <0 a 10>, "comentario": "<comentário>"},\n'
            '  "feedback_geral": "<feedback geral>"\n'
            "}\n\n"
            f"Descrição da vaga:\n{texto_vaga}\n\n"
            f"Pergunta ({tipo}): {pergunta}\n\n"
            f"Resposta do candidato: {resposta}"
        )
