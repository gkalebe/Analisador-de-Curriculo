from app.core.service.reescrita_curriculo import aplicar_sugestoes_sem_ia


def _dados():
    return {
        "nome_completo": "Ana Silva",
        "resumo_profissional": "Profissional proativa que fez coisas em projetos de software e busca crescimento.",
        "experiencias": [
            {
                "cargo": "Desenvolvedora",
                "empresa": "Empresa X",
                "periodo_inicio": "2021",
                "periodo_fim": "atual",
                "descricao_bullets": ["Responsável por fazer deploy das aplicações", "Ajudava o time nas tarefas"],
            }
        ],
        "formacao": [
            {"curso": "Ensino Médio", "instituicao": "Escola Y", "periodo": "2015"},
            {"curso": "Engenharia de Software", "instituicao": "UnB", "periodo": "2016-2020"},
        ],
        "habilidades_tecnicas": ["Python", "Proativo", "SQL"],
        "idiomas": [{"idioma": "Inglês", "nivel": "C1"}],
        "certificacoes": ["Curso de Excel básico"],
        "secoes_adicionais": [{"titulo": "Projetos", "itens": ["Projeto A"]}],
    }


def test_reescrita_substitui_trecho_dentro_do_resumo_sem_alterar_o_resto():
    sugestoes = {
        "sugestoes_reescrita": [
            {"campo": "resumo", "trecho_original": "fez coisas em projetos de software", "versao_otimizada": "entregou 12 projetos de software"}
        ]
    }

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes, "bruto")

    assert dados["resumo_profissional"] == "Profissional proativa que entregou 12 projetos de software e busca crescimento."
    assert relatorio["reescritas"] == {"total": 1, "aplicadas": 1, "nao_aplicadas": []}
    assert relatorio["total_aplicadas"] == 1
    assert dados["texto_bruto"] == "bruto"


def test_reescrita_troca_bullet_inteiro_e_divide_versao_em_varias_linhas():
    sugestoes = {
        "sugestoes_reescrita": [
            {
                "campo": "experiencia_profissional",
                "trecho_original": "Responsável por fazer deploy das aplicações",
                "versao_otimizada": "Orquestrou implantações contínuas (CI/CD) de 5 aplicações\nReduziu o tempo de deploy em 40%",
            }
        ]
    }

    dados, _ = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert dados["experiencias"][0]["descricao_bullets"] == [
        "Orquestrou implantações contínuas (CI/CD) de 5 aplicações",
        "Reduziu o tempo de deploy em 40%",
        "Ajudava o time nas tarefas",
    ]


def test_reescrita_tolera_diferencas_de_caixa_espacos_e_pontuacao_e_campo_errado():
    sugestoes = {
        "sugestoes_reescrita": [
            {"campo": "habilidades", "trecho_original": "ajudava   o time nas Tarefas.", "versao_otimizada": "Apoiou 4 desenvolvedores em revisões de código"}
        ]
    }

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert "Apoiou 4 desenvolvedores em revisões de código" in dados["experiencias"][0]["descricao_bullets"]
    assert relatorio["reescritas"]["aplicadas"] == 1


def test_reescrita_substitui_lista_de_habilidades_inteira_quando_trecho_cita_o_bloco():
    sugestoes = {
        "sugestoes_reescrita": [
            {"campo": "habilidades", "trecho_original": "Python, Proativo, SQL", "versao_otimizada": "Python, SQL, PostgreSQL, Docker"}
        ]
    }

    dados, _ = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert dados["habilidades_tecnicas"] == ["Python", "SQL", "PostgreSQL", "Docker"]


def test_reescrita_sem_correspondencia_vai_para_nao_aplicadas_e_nao_altera_nada():
    sugestoes = {"sugestoes_reescrita": [{"campo": "resumo", "trecho_original": "texto inexistente", "versao_otimizada": "x"}]}

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert relatorio["reescritas"]["nao_aplicadas"] == ["texto inexistente"]
    assert relatorio["total_aplicadas"] == 0
    assert dados["resumo_profissional"] == _dados()["resumo_profissional"]


def test_remocao_tira_item_inteiro_de_formacao_habilidade_e_certificacao():
    sugestoes = {"diagnostico_ats": {"a_remover": ["Formação: Ensino Médio", "Proativo", "Excel básico"]}}

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert [f["curso"] for f in dados["formacao"]] == ["Engenharia de Software"]
    assert dados["habilidades_tecnicas"] == ["Python", "SQL"]
    assert dados["certificacoes"] == []
    assert relatorio["remocoes"]["aplicadas"] == ["Formação: Ensino Médio", "Proativo", "Excel básico"]
    assert relatorio["remocoes"]["ja_ausentes"] == []
    assert relatorio["total_aplicadas"] == 3


def test_remocao_de_termo_vago_dentro_de_frase_nao_e_aplicada_e_e_reportada():
    sugestoes = {"diagnostico_ats": {"a_remover": ["busca crescimento"]}}

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert dados["resumo_profissional"] == _dados()["resumo_profissional"]
    assert relatorio["remocoes"]["nao_aplicadas"] == ["busca crescimento"]
    assert relatorio["total_aplicadas"] == 0


def test_remocao_de_item_que_nunca_existiu_nao_conta_como_aplicada():
    sugestoes = {"diagnostico_ats": {"a_remover": ["Curso de Cobol"]}}

    _, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert relatorio["remocoes"]["ja_ausentes"] == ["Curso de Cobol"]
    assert relatorio["remocoes"]["total"] == 0
    assert relatorio["total_aplicadas"] == 0


def test_remocao_conta_como_aplicada_se_a_reescrita_ja_tirou_o_trecho():
    sugestoes = {
        "diagnostico_ats": {"a_remover": ["fez coisas"]},
        "sugestoes_reescrita": [{"campo": "resumo", "trecho_original": "fez coisas", "versao_otimizada": "entregou projetos"}],
    }

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert "fez coisas" not in dados["resumo_profissional"]
    assert relatorio["remocoes"]["aplicadas"] == ["fez coisas"]


def test_remocao_nao_apaga_item_so_por_compartilhar_uma_palavra():
    sugestoes = {"diagnostico_ats": {"a_remover": ["Software"]}}

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert [f["curso"] for f in dados["formacao"]] == ["Ensino Médio", "Engenharia de Software"]
    assert relatorio["remocoes"]["nao_aplicadas"] == ["Software"]


def test_palavras_chave_e_reorganizacao_nunca_sao_aplicadas_so_reportadas():
    sugestoes = {
        "palavras_chave_faltantes": ["Docker", "Kubernetes"],
        "diagnostico_ats": {"a_reorganizar": ["Mover formação para depois da experiência"]},
    }

    dados, relatorio = aplicar_sugestoes_sem_ia(_dados(), sugestoes)

    assert "Docker" not in dados["habilidades_tecnicas"]
    assert relatorio["palavras_chave_faltantes"] == ["Docker", "Kubernetes"]
    assert relatorio["a_reorganizar"] == ["Mover formação para depois da experiência"]
    assert relatorio["total_aplicadas"] == 0


def test_aplica_em_dados_no_formato_plano_antigo():
    legado = {"nome": "Ana", "resumo": "fez coisas", "formacao": "Ensino Médio\nEngenharia", "habilidades": "Python"}
    sugestoes = {
        "diagnostico_ats": {"a_remover": ["Ensino Médio"]},
        "sugestoes_reescrita": [{"campo": "resumo", "trecho_original": "fez coisas", "versao_otimizada": "liderou automações"}],
    }

    dados, relatorio = aplicar_sugestoes_sem_ia(legado, sugestoes)

    assert dados["resumo_profissional"] == "liderou automações"
    assert [f["curso"] for f in dados["formacao"]] == ["Engenharia"]
    assert relatorio["total_aplicadas"] == 2
