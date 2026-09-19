import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import {
  aplicarSugestoesCurriculo,
  obterEdicaoCurriculo,
  salvarEdicaoEstruturada,
  salvarEdicaoTextoLivre,
} from "../api/curriculoApi.js";
import { listarAnalises } from "../api/analiseApi.js";
import { ApiError } from "../api/client.js";

const CAMPOS_ESTRUTURADOS = [
  { chave: "nome", rotulo: "Nome", tipo: "input" },
  { chave: "email", rotulo: "E-mail", tipo: "input" },
  { chave: "telefone", rotulo: "Telefone", tipo: "input" },
  { chave: "resumo", rotulo: "Resumo profissional", tipo: "textarea" },
  { chave: "formacao", rotulo: "Formação", tipo: "textarea" },
  { chave: "experiencia_profissional", rotulo: "Experiência profissional", tipo: "textarea" },
  { chave: "habilidades", rotulo: "Habilidades", tipo: "input" },
];

const DADOS_VAZIOS = {
  nome: "",
  email: "",
  telefone: "",
  resumo: "",
  formacao: "",
  experiencia_profissional: "",
  habilidades: "",
};

export default function EditarCurriculo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || "";
  const idCurriculoUrl = searchParams.get("curriculo") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [analises, setAnalises] = useState([]);
  const [idCurriculoSelecionado, setIdCurriculoSelecionado] = useState(idCurriculoUrl);

  const [modo, setModo] = useState("estruturado"); // "estruturado" | "texto-livre"
  const [dadosForm, setDadosForm] = useState(DADOS_VAZIOS);
  const [textoLivre, setTextoLivre] = useState("");
  const [sugestoes, setSugestoes] = useState(null);
  const [possuiEdicao, setPossuiEdicao] = useState(false);
  const [editadoEm, setEditadoEm] = useState(null);

  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [aplicandoSugestoes, setAplicandoSugestoes] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    if (!emailInicial) return;
    listarAnalises(emailInicial)
      .then((resposta) => setAnalises(resposta.analises || []))
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
    setSearchParams({ email: emailInicial, curriculo: idCurriculo });
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

  const temSugestoes =
    sugestoes &&
    ((sugestoes.palavras_chave_faltantes && sugestoes.palavras_chave_faltantes.length > 0) ||
      (sugestoes.sugestoes_reescrita && sugestoes.sugestoes_reescrita.length > 0) ||
      sugestoes.diagnostico_ats);

  async function aplicarSugestoes() {
    setAplicandoSugestoes(true);
    setErro("");
    setAviso("");
    try {
      const resposta = await aplicarSugestoesCurriculo(idCurriculoSelecionado, emailInicial);
      setDadosForm({ ...DADOS_VAZIOS, ...resposta.dados });
      setTextoLivre(resposta.dados?.texto_bruto || "");
      setPossuiEdicao(true);
      setEditadoEm(resposta.editado_em || null);
      setModo("estruturado");
      setAviso("Sugestões aplicadas automaticamente. Revise os campos abaixo antes de exportar.");
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível aplicar as sugestões agora. Tente novamente.");
    } finally {
      setAplicandoSugestoes(false);
    }
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="editar" />

      <main className="flex-1 p-6 space-y-4 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Editar currículo</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Aplique as sugestões da análise ao seu currículo — por campos ou colando o texto todo.
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
            <h2 className="font-brand text-[24px] text-black">Escolha o currículo para editar</h2>
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

        {emailInicial && idCurriculoSelecionado && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setModo("estruturado")}
                    className={`rounded-md px-4 py-2 text-sm font-bold transition-colors ${
                      modo === "estruturado" ? "bg-[#1e5e3f] text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    Campos estruturados
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
                {possuiEdicao && (
                  <span className="text-xs font-semibold text-[#1e5e3f]">
                    Editado {editadoEm ? `em ${new Date(editadoEm).toLocaleString("pt-BR")}` : ""}
                  </span>
                )}
              </div>

              {carregando && <p className="text-sm text-gray-500">Carregando...</p>}

              {!carregando && modo === "estruturado" && (
                <form onSubmit={salvarEstruturado} className="space-y-4">
                  {CAMPOS_ESTRUTURADOS.map((campo) => (
                    <div key={campo.chave}>
                      <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-gray-500">
                        {campo.rotulo}
                      </label>
                      {campo.tipo === "textarea" ? (
                        <textarea
                          value={dadosForm[campo.chave] || ""}
                          onChange={(e) => setDadosForm({ ...dadosForm, [campo.chave]: e.target.value })}
                          rows={4}
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
                  ))}
                  <button
                    type="submit"
                    disabled={salvando}
                    className="rounded-md bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                  >
                    {salvando ? "Salvando..." : "Salvar edição"}
                  </button>
                </form>
              )}

              {!carregando && modo === "texto-livre" && (
                <form onSubmit={salvarTextoLivre} className="space-y-4">
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

              {possuiEdicao && (
                <div className="rounded-lg border border-emerald-200 bg-[#f0fdf4] px-4 py-3 text-sm text-[#1e5e3f]">
                  Pronto! Ao exportar um template em "Templates ATS", escolha a versão <strong>Editada</strong> para
                  usar esses dados.{" "}
                  <Link
                    to={`/templates?email=${encodeURIComponent(emailInicial)}`}
                    className="font-semibold underline"
                  >
                    Ir para templates
                  </Link>
                </div>
              )}
            </div>

            <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4 h-fit">
              <h3 className="font-brand text-lg font-bold text-black">Sugestões da última análise</h3>
              {!temSugestoes && (
                <p className="text-sm text-gray-500">
                  Nenhuma sugestão disponível ainda. Rode uma análise deste currículo para receber recomendações.
                </p>
              )}

              {temSugestoes && (
                <button
                  type="button"
                  onClick={aplicarSugestoes}
                  disabled={aplicandoSugestoes}
                  className="w-full flex items-center justify-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                >
                  <i className="ti ti-sparkles"></i>{" "}
                  {aplicandoSugestoes ? "Aplicando..." : "Aplicar sugestões automaticamente"}
                </button>
              )}

              {sugestoes?.palavras_chave_faltantes?.length > 0 && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">
                    Palavras-chave faltantes
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {sugestoes.palavras_chave_faltantes.map((palavra, idx) => (
                      <span
                        key={idx}
                        className="rounded-full bg-amber-100 border border-amber-300 px-2.5 py-1 text-xs text-amber-800"
                      >
                        {palavra}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {sugestoes?.diagnostico_ats && (
                <div className="space-y-2">
                  {sugestoes.diagnostico_ats.pontos_fortes?.length > 0 && (
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Pontos fortes</p>
                      <ul className="list-disc pl-4 text-sm text-gray-700 space-y-0.5">
                        {sugestoes.diagnostico_ats.pontos_fortes.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {sugestoes.diagnostico_ats.a_reorganizar?.length > 0 && (
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">A reorganizar</p>
                      <ul className="list-disc pl-4 text-sm text-gray-700 space-y-0.5">
                        {sugestoes.diagnostico_ats.a_reorganizar.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {sugestoes.diagnostico_ats.a_remover?.length > 0 && (
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">A remover</p>
                      <ul className="list-disc pl-4 text-sm text-gray-700 space-y-0.5">
                        {sugestoes.diagnostico_ats.a_remover.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {sugestoes?.sugestoes_reescrita?.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Trechos para reescrever</p>
                  {sugestoes.sugestoes_reescrita.map((item, idx) => (
                    <div key={idx} className="rounded-lg border border-gray-200 p-3 text-xs space-y-1.5">
                      {item.trecho_original && (
                        <p className="text-gray-500">
                          <span className="font-bold">Original: </span>
                          {item.trecho_original}
                        </p>
                      )}
                      {item.versao_otimizada && (
                        <p className="text-[#1e5e3f]">
                          <span className="font-bold">Sugestão: </span>
                          {item.versao_otimizada}
                        </p>
                      )}
                      {item.justificativa && <p className="italic text-gray-400">{item.justificativa}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
