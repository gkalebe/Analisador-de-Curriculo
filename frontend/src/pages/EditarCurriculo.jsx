import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import {
  obterEdicaoCurriculo,
  salvarEdicaoEstruturada,
  salvarEdicaoTextoLivre,
} from "../api/curriculoApi.js";
import { listarAnalises } from "../api/analiseApi.js";
import { listarTemplates } from "../api/templateApi.js";
import { ApiError } from "../api/client.js";

const ESTILOS_CARTAO = {
  moderno: { borda: "border-[#1e5e3f]", nome: "text-[#1e5e3f]" },
  classico: { borda: "border-black", nome: "text-black" },
  minimalista: { borda: "border-gray-300", nome: "text-gray-900" },
  executivo: { borda: "border-[#1e3a5f]", nome: "text-[#1e3a5f]" },
  criativo: { borda: "border-[#c45a3c]", nome: "text-gray-900" },
};

const DADOS_VAZIOS = {
  nome: "",
  email: "",
  telefone: "",
  resumo: "",
  formacao: "",
  experiencia_profissional: "",
  habilidades: "",
};

const BLOCOS_CAMPO = [
  { chave: "resumo", rotulo: "Resumo profissional", tipo: "textarea", linhas: 4 },
  { chave: "formacao", rotulo: "Formação", tipo: "textarea", linhas: 3 },
  { chave: "experiencia_profissional", rotulo: "Experiência profissional", tipo: "textarea", linhas: 6 },
  { chave: "habilidades", rotulo: "Habilidades", tipo: "input" },
];

function normalizarTexto(texto) {
  return (texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

function pontuarSobreposicao(trecho, textoCampo) {
  if (!trecho || !textoCampo) return 0;
  const palavras = normalizarTexto(trecho)
    .split(/\W+/)
    .filter((p) => p.length > 3);
  if (palavras.length === 0) return 0;
  const textoNormalizado = normalizarTexto(textoCampo);
  const encontradas = palavras.filter((p) => textoNormalizado.includes(p));
  return encontradas.length / palavras.length;
}

function associarSugestoesPorBloco(sugestoes, dados) {
  const campos = ["resumo", "formacao", "experiencia_profissional", "habilidades"];
  const porCampo = { resumo: [], formacao: [], experiencia_profissional: [], habilidades: [] };
  const semCampo = [];

  (sugestoes?.sugestoes_reescrita || []).forEach((s) => {
    let melhorCampo = null;
    let melhorPontuacao = 0;
    campos.forEach((campo) => {
      const pontuacao = pontuarSobreposicao(s.trecho_original, dados[campo]);
      if (pontuacao > melhorPontuacao) {
        melhorPontuacao = pontuacao;
        melhorCampo = campo;
      }
    });
    if (melhorCampo && melhorPontuacao >= 0.4) {
      porCampo[melhorCampo].push(s);
    } else {
      semCampo.push(s);
    }
  });

  return { porCampo, semCampo };
}

export default function EditarCurriculo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || "";
  const idCurriculoUrl = searchParams.get("curriculo") || "";
  const idTemplateUrl = searchParams.get("template") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [analises, setAnalises] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [idCurriculoSelecionado, setIdCurriculoSelecionado] = useState(idCurriculoUrl);
  const [idTemplateSelecionado, setIdTemplateSelecionado] = useState(idTemplateUrl);

  const [modo, setModo] = useState("estruturado"); // "estruturado" | "texto-livre"
  const [dadosForm, setDadosForm] = useState(DADOS_VAZIOS);
  const [textoLivre, setTextoLivre] = useState("");
  const [sugestoes, setSugestoes] = useState(null);
  const [possuiEdicao, setPossuiEdicao] = useState(false);
  const [editadoEm, setEditadoEm] = useState(null);

  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    if (!emailInicial) return;
    listarAnalises(emailInicial)
      .then((resposta) => setAnalises(resposta.analises || []))
      .catch(() => {});
    listarTemplates(emailInicial)
      .then((resposta) => setTemplates(resposta.templates || []))
      .catch(() => {});
  }, [emailInicial]);

  useEffect(() => {
    if (!emailInicial || !idCurriculoSelecionado) return;
    setCarregando(true);
    setErro("");
    setAviso("");
    obterEdicaoCurriculo(idCurriculoSelecionado, emailInicial)
      .then((resposta) => {
        setDadosForm({ ...DADOS_VAZIOS, ...resposta.dados });
        setTextoLivre(resposta.dados?.texto_bruto || "");
        setSugestoes(resposta.sugestoes || null);
        setPossuiEdicao(Boolean(resposta.possui_edicao));
        setEditadoEm(resposta.editado_em || null);
      })
      .catch((e) => setErro(e instanceof ApiError ? e.message : "Não foi possível carregar os dados do currículo."))
      .finally(() => setCarregando(false));
  }, [emailInicial, idCurriculoSelecionado]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo });
  }

  function escolherCurriculo(idCurriculo) {
    setIdCurriculoSelecionado(idCurriculo);
    setSearchParams({ email: emailInicial, curriculo: idCurriculo, ...(idTemplateSelecionado ? { template: idTemplateSelecionado } : {}) });
  }

  function escolherTemplate(idTemplate) {
    setIdTemplateSelecionado(idTemplate);
    setSearchParams({ email: emailInicial, curriculo: idCurriculoSelecionado, template: idTemplate });
  }

  function trocarTemplate() {
    setIdTemplateSelecionado("");
    setSearchParams({ email: emailInicial, curriculo: idCurriculoSelecionado });
  }

  async function salvarEstruturado(evento) {
    evento.preventDefault();
    setSalvando(true);
    setErro("");
    setAviso("");
    try {
      const resposta = await salvarEdicaoEstruturada(idCurriculoSelecionado, emailInicial, dadosForm);
      setDadosForm({ ...DADOS_VAZIOS, ...resposta.dados });
      setPossuiEdicao(true);
      setEditadoEm(resposta.editado_em || null);
      setAviso("Edição salva. Agora você pode exportar a versão editada em qualquer template ATS.");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível salvar a edição.");
    } finally {
      setSalvando(false);
    }
  }

  async function salvarTextoLivre(evento) {
    evento.preventDefault();
    if (!textoLivre.trim()) return;
    setSalvando(true);
    setErro("");
    setAviso("");
    try {
      const resposta = await salvarEdicaoTextoLivre(idCurriculoSelecionado, emailInicial, textoLivre);
      setDadosForm({ ...DADOS_VAZIOS, ...resposta.dados });
      setPossuiEdicao(true);
      setEditadoEm(resposta.editado_em || null);
      setAviso("Texto salvo e reorganizado nos campos do currículo. Confira a aba \"Campos estruturados\".");
      setModo("estruturado");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível salvar o texto.");
    } finally {
      setSalvando(false);
    }
  }

  function usarSugestaoNoCampo(campo, sugestao) {
    setDadosForm((atual) => {
      const atualCampo = atual[campo] || "";
      let novoValor;
      if (sugestao.trecho_original && atualCampo.includes(sugestao.trecho_original)) {
        novoValor = atualCampo.replace(sugestao.trecho_original, sugestao.versao_otimizada);
      } else if (atualCampo.trim()) {
        novoValor = `${atualCampo}\n${sugestao.versao_otimizada}`;
      } else {
        novoValor = sugestao.versao_otimizada;
      }
      return { ...atual, [campo]: novoValor };
    });
  }

  function adicionarPalavraChave(palavra) {
    setDadosForm((atual) => {
      const atuais = (atual.habilidades || "")
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);
      if (atuais.some((p) => normalizarTexto(p) === normalizarTexto(palavra))) return atual;
      const novoValor = atuais.length > 0 ? `${atual.habilidades}, ${palavra}` : palavra;
      return { ...atual, habilidades: novoValor };
    });
  }

  const { porCampo: sugestoesPorCampo, semCampo: sugestoesSemCampo } = associarSugestoesPorBloco(sugestoes, dadosForm);
  const temDiagnostico =
    sugestoes?.diagnostico_ats &&
    ((sugestoes.diagnostico_ats.pontos_fortes && sugestoes.diagnostico_ats.pontos_fortes.length > 0) ||
      (sugestoes.diagnostico_ats.a_reorganizar && sugestoes.diagnostico_ats.a_reorganizar.length > 0) ||
      (sugestoes.diagnostico_ats.a_remover && sugestoes.diagnostico_ats.a_remover.length > 0));
  const temQualquerSugestao =
    sugestoes &&
    (temDiagnostico ||
      (sugestoes.palavras_chave_faltantes && sugestoes.palavras_chave_faltantes.length > 0) ||
      (sugestoes.sugestoes_reescrita && sugestoes.sugestoes_reescrita.length > 0));

  const templateEscolhido = templates.find((t) => t.id_template === idTemplateSelecionado);

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="editar" />

      <main className="flex-1 p-6 space-y-4 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Editar currículo</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Aplique as sugestões da análise direto em cada bloco do seu currículo.
          </p>
        </div>

        {!emailInicial && (
          <form onSubmit={entrarComEmail} className="flex gap-2 rounded-lg border-[0.5px] border-black bg-white p-4">
            <input
              type="email"
              value={emailCampo}
              onChange={(e) => setEmailCampo(e.target.value)}
              placeholder="Seu e-mail cadastrado"
              required
              className="flex-1 rounded border border-[#dfdfe0] px-3 py-2 text-sm text-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
            />
            <button type="submit" className="rounded bg-[#1e5e3f] px-4 py-2 font-bold text-white hover:bg-[#174a32]">
              Entrar
            </button>
          </form>
        )}

        {emailInicial && !idCurriculoSelecionado && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
            <h2 className="font-brand text-[24px] text-black">1. Escolha o currículo para editar</h2>
            {analises.length === 0 && (
              <p className="text-sm text-gray-500">
                Você ainda não concluiu nenhuma análise. Rode uma em "Nova análise" antes de editar seu currículo.
              </p>
            )}
            {analises.length > 0 && (
              <ul className="space-y-2">
                {analises.map((analise) => (
                  <li key={analise.id_analise}>
                    <button
                      type="button"
                      onClick={() => escolherCurriculo(analise.id_curriculo)}
                      className="flex w-full items-center justify-between gap-3 rounded-lg border-[0.5px] border-black p-4 text-left hover:border-[#1e5e3f] hover:bg-[#f0fdf4]"
                    >
                      <div>
                        <p className="font-medium">
                          {analise.nome_curriculo || "Currículo"} — Análise de{" "}
                          {new Date(analise.data_analise).toLocaleDateString("pt-BR")}
                        </p>
                        {analise.curriculo_possui_edicao && (
                          <p className="text-xs font-semibold text-[#1e5e3f]">Já possui uma edição salva</p>
                        )}
                      </div>
                      <i className="ti ti-chevron-right text-[20px] text-gray-400"></i>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}
        {aviso && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-[#1e5e3f]">{aviso}</div>
        )}

        {emailInicial && idCurriculoSelecionado && !idTemplateSelecionado && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-brand text-[24px] text-black">2. Para qual template você está otimizando?</h2>
              <button
                type="button"
                onClick={() => {
                  setIdCurriculoSelecionado("");
                  setSearchParams({ email: emailInicial });
                }}
                className="text-xs font-semibold text-gray-500 underline hover:text-black"
              >
                Trocar currículo
              </button>
            </div>
            <p className="text-sm text-gray-500">
              Os blocos de edição vão aparecer na mesma ordem usada pelo template escolhido, para facilitar encaixar
              as sugestões. Você pode trocar de template a qualquer momento.
            </p>
            {templates.length === 0 && <p className="text-sm text-gray-500">Carregando templates...</p>}
            {templates.length > 0 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {templates.map((template) => {
                  const estilo = ESTILOS_CARTAO[template.id_template] || ESTILOS_CARTAO.moderno;
                  return (
                    <button
                      key={template.id_template}
                      type="button"
                      onClick={() => escolherTemplate(template.id_template)}
                      className={`flex flex-col rounded-lg border-2 ${estilo.borda} bg-white p-4 text-left hover:bg-[#f9fafb]`}
                    >
                      <p className={`font-brand text-lg font-bold ${estilo.nome}`}>{template.nome}</p>
                      <p className="mt-1 text-xs text-gray-500">{template.descricao}</p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {emailInicial && idCurriculoSelecionado && idTemplateSelecionado && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border-[0.5px] border-black bg-white px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Template:</span>
                <span className="font-bold text-[#1e5e3f]">{templateEscolhido?.nome || idTemplateSelecionado}</span>
                <button type="button" onClick={trocarTemplate} className="text-xs font-semibold underline text-gray-500 hover:text-black">
                  Trocar template
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setModo("estruturado")}
                  className={`rounded-md px-4 py-2 text-sm font-bold transition-colors ${
                    modo === "estruturado" ? "bg-[#1e5e3f] text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Blocos
                </button>
                <button
                  type="button"
                  onClick={() => setModo("texto-livre")}
                  className={`rounded-md px-4 py-2 text-sm font-bold transition-colors ${
                    modo === "texto-livre" ? "bg-[#1e5e3f] text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Texto livre
                </button>
              </div>
            </div>

            {carregando && <p className="text-sm text-gray-500">Carregando...</p>}

            {possuiEdicao && !carregando && (
              <div className="rounded-lg border border-emerald-200 bg-[#f0fdf4] px-4 py-3 text-sm text-[#1e5e3f] flex flex-wrap items-center justify-between gap-2">
                <span>
                  Editado {editadoEm ? `em ${new Date(editadoEm).toLocaleString("pt-BR")}` : ""}. Ao exportar,
                  escolha a versão <strong>Editada</strong>.
                </span>
                <Link
                  to={`/templates/exportar?email=${encodeURIComponent(emailInicial)}&template=${idTemplateSelecionado}`}
                  className="font-semibold underline whitespace-nowrap"
                >
                  Ir para exportação
                </Link>
              </div>
            )}

            {!carregando && modo === "texto-livre" && (
              <form onSubmit={salvarTextoLivre} className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
                <p className="text-sm text-gray-500">
                  Cole aqui o texto completo do seu currículo já revisado. A IA reorganiza automaticamente nos
                  campos estruturados.
                </p>
                <textarea
                  value={textoLivre}
                  onChange={(e) => setTextoLivre(e.target.value)}
                  rows={16}
                  placeholder="Cole aqui o texto completo do currículo..."
                  className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                />
                <button
                  type="submit"
                  disabled={salvando || !textoLivre.trim()}
                  className="rounded-md bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                >
                  {salvando ? "Salvando..." : "Salvar e reorganizar"}
                </button>
              </form>
            )}

            {!carregando && modo === "estruturado" && (
              <form onSubmit={salvarEstruturado} className="space-y-4">
                {!temQualquerSugestao && (
                  <p className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-500">
                    Nenhuma sugestão disponível ainda para este currículo. Rode uma análise dele para receber
                    recomendações em cada bloco.
                  </p>
                )}

                {temDiagnostico && (
                  <div className="rounded-lg border-[0.5px] border-black bg-white p-4 space-y-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Diagnóstico geral da análise</p>
                    {sugestoes.diagnostico_ats.pontos_fortes?.length > 0 && (
                      <p className="text-sm text-gray-700">
                        <span className="font-bold text-[#1e5e3f]">Pontos fortes: </span>
                        {sugestoes.diagnostico_ats.pontos_fortes.join(" · ")}
                      </p>
                    )}
                    {sugestoes.diagnostico_ats.a_reorganizar?.length > 0 && (
                      <p className="text-sm text-gray-700">
                        <span className="font-bold text-amber-700">A reorganizar: </span>
                        {sugestoes.diagnostico_ats.a_reorganizar.join(" · ")}
                      </p>
                    )}
                    {sugestoes.diagnostico_ats.a_remover?.length > 0 && (
                      <p className="text-sm text-gray-700">
                        <span className="font-bold text-red-700">A remover: </span>
                        {sugestoes.diagnostico_ats.a_remover.join(" · ")}
                      </p>
                    )}
                  </div>
                )}

                <div className="rounded-lg border-[0.5px] border-black bg-white p-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-gray-500">Nome</label>
                    <input
                      type="text"
                      value={dadosForm.nome || ""}
                      onChange={(e) => setDadosForm({ ...dadosForm, nome: e.target.value })}
                      className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-gray-500">E-mail</label>
                    <input
                      type="text"
                      value={dadosForm.email || ""}
                      onChange={(e) => setDadosForm({ ...dadosForm, email: e.target.value })}
                      className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-gray-500">Telefone</label>
                    <input
                      type="text"
                      value={dadosForm.telefone || ""}
                      onChange={(e) => setDadosForm({ ...dadosForm, telefone: e.target.value })}
                      className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                    />
                  </div>
                </div>

                {BLOCOS_CAMPO.map((campo) => {
                  const sugestoesDoBloco = sugestoesPorCampo[campo.chave] || [];
                  const chaves = campo.chave === "habilidades" ? sugestoes?.palavras_chave_faltantes || [] : [];
                  const temAlgumaSugestao = sugestoesDoBloco.length > 0 || chaves.length > 0;
                  return (
                    <div
                      key={campo.chave}
                      className="rounded-lg border-[0.5px] border-black bg-white p-5 grid grid-cols-1 gap-4 lg:grid-cols-5"
                    >
                      <div className="lg:col-span-3">
                        <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-gray-500">
                          {campo.rotulo}
                        </label>
                        {campo.tipo === "textarea" ? (
                          <textarea
                            value={dadosForm[campo.chave] || ""}
                            onChange={(e) => setDadosForm({ ...dadosForm, [campo.chave]: e.target.value })}
                            rows={campo.linhas}
                            className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                          />
                        ) : (
                          <input
                            type="text"
                            value={dadosForm[campo.chave] || ""}
                            onChange={(e) => setDadosForm({ ...dadosForm, [campo.chave]: e.target.value })}
                            className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                          />
                        )}
                      </div>

                      <div className="lg:col-span-2 lg:border-l lg:border-gray-100 lg:pl-4 space-y-2">
                        <p className="text-xs font-bold uppercase tracking-wide text-gray-400">Sugestões para este bloco</p>
                        {!temAlgumaSugestao && (
                          <p className="text-xs text-gray-400">Nenhuma sugestão específica para este bloco.</p>
                        )}

                        {chaves.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {chaves.map((palavra, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => adicionarPalavraChave(palavra)}
                                title="Adicionar às habilidades"
                                className="rounded-full bg-amber-100 border border-amber-300 px-2.5 py-1 text-xs text-amber-800 hover:bg-amber-200"
                              >
                                + {palavra}
                              </button>
                            ))}
                          </div>
                        )}

                        {sugestoesDoBloco.map((s, idx) => (
                          <div key={idx} className="rounded-lg border border-gray-200 p-2.5 text-xs space-y-1">
                            {s.versao_otimizada && <p className="text-[#1e5e3f]">{s.versao_otimizada}</p>}
                            {s.justificativa && <p className="italic text-gray-400">{s.justificativa}</p>}
                            <button
                              type="button"
                              onClick={() => usarSugestaoNoCampo(campo.chave, s)}
                              className="rounded bg-[#1e5e3f] px-2.5 py-1 font-bold text-white hover:bg-[#174a32]"
                            >
                              Usar esta versão
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}

                {sugestoesSemCampo.length > 0 && (
                  <div className="rounded-lg border-[0.5px] border-black bg-white p-5 space-y-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                      Outras sugestões de reescrita (não identificamos o bloco exato)
                    </p>
                    {sugestoesSemCampo.map((s, idx) => (
                      <div key={idx} className="rounded-lg border border-gray-200 p-3 text-xs space-y-1.5">
                        {s.trecho_original && (
                          <p className="text-gray-500">
                            <span className="font-bold">Original: </span>
                            {s.trecho_original}
                          </p>
                        )}
                        {s.versao_otimizada && (
                          <p className="text-[#1e5e3f]">
                            <span className="font-bold">Sugestão: </span>
                            {s.versao_otimizada}
                          </p>
                        )}
                        {s.justificativa && <p className="italic text-gray-400">{s.justificativa}</p>}
                      </div>
                    ))}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={salvando}
                  className="rounded-md bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                >
                  {salvando ? "Salvando..." : "Salvar edição"}
                </button>
              </form>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
