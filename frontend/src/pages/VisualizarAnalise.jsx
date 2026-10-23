import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import AnelProgresso, { classificarAderencia } from "../components/AnelProgresso.jsx";
import { listarAnalises } from "../api/analiseApi.js";
import {
  adicionarHabilidadeCurriculo,
  aplicarSugestaoIndividual,
  obterEdicaoCurriculo,
  removerHabilidadeCurriculo,
} from "../api/curriculoApi.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";
import { montarRotaGaleriaTemplates, prepararCurriculoParaTemplate } from "../models/templateAts.js";

function extrairDadosAts(observacoes) {
  if (!observacoes) return null;
  try {
    const parsed = JSON.parse(observacoes);
    if (typeof parsed === "object" && parsed !== null) {
      const palavrasChave = parsed.palavras_chave || {};
      const diagnostico = parsed.diagnostico_ats || {};
      const sugestoes = Array.isArray(parsed.sugestoes_reescrita) ? parsed.sugestoes_reescrita : [];

      return {
        explicacao_ats: parsed.resumo || parsed.explicacao_ats || parsed.observacoes,
        requisitos_avaliados: Array.isArray(parsed.requisitos_avaliados)
          ? parsed.requisitos_avaliados
          : [],
        palavras_chave: {
          encontradas: palavrasChave.encontradas || palavrasChave.correspondentes || [],
          faltantes: palavrasChave.faltantes || palavrasChave.ausentes || [],
        },
        diagnostico_ats: {
          pontos_fortes: diagnostico.pontos_fortes || [],
          a_reorganizar: diagnostico.a_reorganizar || diagnostico.o_que_reorganizar || [],
          a_remover: diagnostico.a_remover || diagnostico.o_que_retirar || [],
        },
        sugestoes_reescrita: sugestoes.map((s) => ({
          trecho_original: s.trecho_original || "",
          versao_otimizada: s.versao_otimizada || s.sugestao_otimizada || "",
          campo: s.campo || "",
          justificativa: s.justificativa || s.motivo || "",
        })),
      };
    }
  } catch {
    // Ignora erro de parse caso seja texto puro legado
  }
  return null;
}

export default function VisualizarAnalise() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const emailInicial = lerSessao()?.email || searchParams.get("email") || "";
  const idAnalise = searchParams.get("id") || "";

  const [analise, setAnalise] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [copiado, setCopiado] = useState(false);
  const [copiadoIdx, setCopiadoIdx] = useState(null);
  const [transformando, setTransformando] = useState(false);

  // Estados interativos
  const [sugestoesState, setSugestoesState] = useState([]);
  const [habilidadesNoCurriculo, setHabilidadesNoCurriculo] = useState(new Set());
  const [carregandoHabilidade, setCarregandoHabilidade] = useState(null);
  const [aplicandoTodas, setAplicandoTodas] = useState(false);
  const [alteracoesFeitas, setAlteracoesFeitas] = useState(false);
  const [feedbackMensagem, setFeedbackMensagem] = useState("");

  async function exportarCurriculoOtimizado() {
    if (!analise?.id_curriculo || transformando) return;
    setTransformando(true);
    try {
      const { versao, aviso } = await prepararCurriculoParaTemplate(
        analise.id_curriculo,
        emailInicial,
        alteracoesFeitas
      );
      navigate(montarRotaGaleriaTemplates(emailInicial, analise.id_curriculo, versao, aviso));
    } finally {
      setTransformando(false);
    }
  }

  async function alternarHabilidade(palavra) {
    if (!analise?.id_curriculo || carregandoHabilidade) return;
    const palavraLimpa = palavra.trim();
    const jaAdicionada = habilidadesNoCurriculo.has(palavraLimpa.toLowerCase());
    setCarregandoHabilidade(palavra);
    try {
      if (jaAdicionada) {
        await removerHabilidadeCurriculo(analise.id_curriculo, emailInicial, palavraLimpa);
        setHabilidadesNoCurriculo((prev) => {
          const next = new Set(prev);
          next.delete(palavraLimpa.toLowerCase());
          return next;
        });
        setFeedbackMensagem(`"${palavraLimpa}" removida das habilidades do currículo.`);
      } else {
        await adicionarHabilidadeCurriculo(analise.id_curriculo, emailInicial, palavraLimpa);
        setHabilidadesNoCurriculo((prev) => {
          const next = new Set(prev);
          next.add(palavraLimpa.toLowerCase());
          return next;
        });
        setAlteracoesFeitas(true);
        setFeedbackMensagem(`"${palavraLimpa}" adicionada às habilidades do currículo!`);
      }
    } catch {
      setFeedbackMensagem(`Não foi possível atualizar "${palavraLimpa}". Tente novamente.`);
    } finally {
      setCarregandoHabilidade(null);
    }
  }

  function toggleEdicaoSugestao(idx, editando) {
    setSugestoesState((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, editando, textoTemp: s.versaoOtimizada } : s))
    );
  }

  function atualizarTextoTempSugestao(idx, texto) {
    setSugestoesState((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, textoTemp: texto } : s))
    );
  }

  function salvarTextoEditadoSugestao(idx) {
    setSugestoesState((prev) =>
      prev.map((s, i) =>
        i === idx ? { ...s, versaoOtimizada: s.textoTemp, editando: false } : s
      )
    );
    setFeedbackMensagem("Texto atualizado. Clique em 'Aplicar' para gravar no currículo.");
  }

  async function aplicarSugestao(idx, textoSobrescrito) {
    const s = sugestoesState[idx];
    if (!s || !analise?.id_curriculo || s.salvando) return;
    const textoParaAplicar = textoSobrescrito || s.versaoOtimizada;
    setSugestoesState((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, salvando: true } : item))
    );
    try {
      const resp = await aplicarSugestaoIndividual(analise.id_curriculo, emailInicial, {
        trecho_original: s.trecho_original,
        versao_otimizada: textoParaAplicar,
        campo: s.campo,
      });
      setSugestoesState((prev) =>
        prev.map((item, i) =>
          i === idx
            ? { ...item, aplicada: true, versaoOtimizada: textoParaAplicar, editando: false, salvando: false }
            : item
        )
      );
      setAlteracoesFeitas(true);
      if (resp?.aplicou === false) {
        setFeedbackMensagem("Sugestão salva, mas o trecho original não foi localizado com exatidão no documento.");
      } else {
        setFeedbackMensagem("Sugestão aplicada com sucesso ao currículo!");
      }
    } catch {
      setSugestoesState((prev) =>
        prev.map((item, i) => (i === idx ? { ...item, salvando: false } : item))
      );
      setFeedbackMensagem("Erro ao aplicar sugestão ao currículo. Tente novamente.");
    }
  }

  async function salvarEAplicarSugestao(idx) {
    const s = sugestoesState[idx];
    if (!s) return;
    await aplicarSugestao(idx, s.textoTemp);
  }

  async function reverterSugestao(idx) {
    const s = sugestoesState[idx];
    if (!s || !analise?.id_curriculo || s.salvando) return;
    setSugestoesState((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, salvando: true } : item))
    );
    try {
      await aplicarSugestaoIndividual(analise.id_curriculo, emailInicial, {
        trecho_original: s.versaoOtimizada,
        versao_otimizada: s.trecho_original,
        campo: s.campo,
      });
      setSugestoesState((prev) =>
        prev.map((item, i) => (i === idx ? { ...item, aplicada: false, salvando: false } : item))
      );
      setFeedbackMensagem("Sugestão desfeita no currículo.");
    } catch {
      setSugestoesState((prev) =>
        prev.map((item, i) => (i === idx ? { ...item, salvando: false } : item))
      );
      setFeedbackMensagem("Erro ao desfazer sugestão. Tente novamente.");
    }
  }

  async function aplicarTodasSugestoes() {
    if (!analise?.id_curriculo || aplicandoTodas) return;
    setAplicandoTodas(true);
    try {
      for (let i = 0; i < sugestoesState.length; i++) {
        const s = sugestoesState[i];
        if (!s.aplicada) {
          await aplicarSugestaoIndividual(analise.id_curriculo, emailInicial, {
            trecho_original: s.trecho_original,
            versao_otimizada: s.versaoOtimizada,
            campo: s.campo,
          });
        }
      }
      setSugestoesState((prev) =>
        prev.map((item) => ({ ...item, aplicada: true, editando: false }))
      );
      setAlteracoesFeitas(true);
      setFeedbackMensagem("Todas as sugestões foram aplicadas ao currículo!");
    } catch {
      setFeedbackMensagem("Ocorreu um erro ao aplicar todas as sugestões.");
    } finally {
      setAplicandoTodas(false);
    }
  }

  function copiarTextoIndividual(texto, idx) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(texto);
    setCopiadoIdx(idx);
    setTimeout(() => setCopiadoIdx(null), 2500);
  }

  useEffect(() => {
    if (!emailInicial || !idAnalise) return;
    setCarregando(true);
    setErro("");
    listarAnalises(emailInicial)
      .then((resposta) => {
        const encontrada = (resposta.analises || []).find((a) => a.id_analise === idAnalise);
        if (!encontrada) {
          setErro("Análise não encontrada.");
        } else {
          setAnalise(encontrada);
        }
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        } else {
          setErro("Não foi possível carregar esta análise.");
        }
      })
      .finally(() => setCarregando(false));
  }, [emailInicial, idAnalise]);

  useEffect(() => {
    if (!analise) {
      setSugestoesState([]);
      setHabilidadesNoCurriculo(new Set());
      setAlteracoesFeitas(false);
      setFeedbackMensagem("");
      return;
    }
    const dados = extrairDadosAts(analise.observacoes);
    const lista = (dados?.sugestoes_reescrita || []).map((s) => ({
      trecho_original: s.trecho_original,
      versaoOtimizada: s.versao_otimizada,
      textoTemp: s.versao_otimizada,
      campo: s.campo,
      justificativa: s.justificativa,
      editando: false,
      aplicada: false,
      salvando: false,
    }));
    setSugestoesState(lista);
    setAlteracoesFeitas(false);
    setFeedbackMensagem("");

    if (analise.id_curriculo) {
      obterEdicaoCurriculo(analise.id_curriculo, emailInicial)
        .then((res) => {
          const habs = res.dados?.habilidades_tecnicas || [];
          setHabilidadesNoCurriculo(new Set(habs.map((h) => h.toLowerCase().trim())));
        })
        .catch(() => {});
    }
  }, [analise, emailInicial]);

  function copiarReescritas() {
    const dadosAts = extrairDadosAts(analise?.observacoes);
    if (!dadosAts?.sugestoes_reescrita?.length || !navigator.clipboard) return;
    const texto = dadosAts.sugestoes_reescrita
      .map((s) => `Original: ${s.trecho_original}\nSugestão: ${s.versao_otimizada}`)
      .join("\n\n");
    navigator.clipboard.writeText(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2500);
  }

  if (carregando) {
    return (
      <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
        <Sidebar email={emailInicial} ativo="historico" />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500 space-y-3">
            <i className="ti ti-loader animate-spin text-[36px] text-[#1e5e3f]"></i>
            <p className="font-brand text-lg font-semibold">Carregando análise...</p>
          </div>
        </main>
      </div>
    );
  }

  if (erro || !analise) {
    return (
      <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
        <Sidebar email={emailInicial} ativo="historico" />
        <main className="flex-1 p-6">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {erro || "Análise não encontrada."}
          </div>
          <Link
            to={`/analises/historico?email=${encodeURIComponent(emailInicial)}`}
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-[#1e5e3f] hover:underline"
          >
            <i className="ti ti-arrow-left"></i> Voltar
          </Link>
        </main>
      </div>
    );
  }

  const pontuacao = analise.pontuacao != null ? Math.round(analise.pontuacao) : 0;
  const { rotulo } = classificarAderencia(pontuacao);
  const dadosAts = extrairDadosAts(analise.observacoes);
  const pontosAtencao = [...(dadosAts?.diagnostico_ats.a_reorganizar || []), ...(dadosAts?.diagnostico_ats.a_remover || [])];

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="historico" />

      <main className="flex-1 p-6 space-y-6 max-w-5xl md:h-screen md:overflow-y-auto">
        <div>
          <Link
            to={`/analises/historico?email=${encodeURIComponent(emailInicial)}`}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-600 hover:text-black"
          >
            <i className="ti ti-arrow-left"></i> Voltar
          </Link>
          <h1 className="mt-2 font-brand text-[28px] font-bold text-black">
            {analise.titulo_vaga || "Vaga sem título"}
          </h1>
          <p className="text-[#727272] font-semibold">Resultado da Análise</p>
        </div>

        {/* Banner de próximo passo */}
        <div className="rounded-xl border border-[#1e5e3f]/20 bg-emerald-50/60 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#1e5e3f]">
              Próximo passo recomendado
            </span>
            <h3 className="font-brand text-lg font-bold text-black mt-1">Treine a entrevista com a IA</h3>
            <p className="text-sm text-gray-600 mt-1 max-w-lg">
              A simulação usa as palavras-chave e lacunas detectadas para gerar perguntas no contexto desta vaga.
            </p>
          </div>
          <Link
            to={`/analises/simulacao?email=${encodeURIComponent(emailInicial)}&vaga=${analise.id_vaga}`}
            className="inline-flex items-center gap-2 rounded-lg bg-[#1e5e3f] px-4 py-2.5 font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors shrink-0"
          >
            <i className="ti ti-microphone"></i>
            Treinar Entrevista
          </Link>
        </div>

        {/* Termos e Lacunas */}
        {dadosAts?.palavras_chave && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border-[0.5px] border-black bg-white p-5 space-y-3">
              <h4 className="font-brand font-bold text-black">
                Termos encontrados ({dadosAts.palavras_chave.encontradas?.length || 0})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {dadosAts.palavras_chave.encontradas?.map((palavra, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-900 border border-emerald-200"
                  >
                    {palavra}
                  </span>
                ))}
                {(!dadosAts.palavras_chave.encontradas || dadosAts.palavras_chave.encontradas.length === 0) && (
                  <span className="text-xs text-gray-500">Nenhum termo técnico coincidente encontrado.</span>
                )}
              </div>
            </div>

            <div className="rounded-xl border-[0.5px] border-black bg-white p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-brand font-bold text-black">
                  Lacunas técnicas / Termos ausentes ({dadosAts.palavras_chave.faltantes?.length || 0})
                </h4>
                <span className="text-[11px] text-gray-500 font-medium hidden sm:inline">
                  Clique no <strong>+</strong> para adicionar ao currículo
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {dadosAts.palavras_chave.faltantes?.map((palavra, idx) => {
                  const normalizada = palavra.trim().toLowerCase();
                  const jaAdicionada = habilidadesNoCurriculo.has(normalizada);
                  const estaCarregando = carregandoHabilidade === palavra;

                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => alternarHabilidade(palavra)}
                      disabled={estaCarregando}
                      title={jaAdicionada ? "Já adicionada ao seu currículo. Clique para remover." : "Clique no + para adicionar esta tecnologia ao seu currículo"}
                      className={`group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer shadow-sm ${
                        jaAdicionada
                          ? "bg-emerald-100 text-emerald-950 border border-emerald-400 hover:bg-rose-50 hover:border-rose-400 hover:text-rose-900"
                          : "bg-white text-rose-900 border border-rose-300 hover:bg-emerald-50 hover:border-emerald-400 hover:text-emerald-900"
                      }`}
                    >
                      {estaCarregando ? (
                        <i className="ti ti-loader animate-spin text-[11px]"></i>
                      ) : jaAdicionada ? (
                        <>
                          <i className="ti ti-check text-[11px] text-emerald-700 group-hover:hidden"></i>
                          <i className="ti ti-x text-[11px] text-rose-700 hidden group-hover:inline"></i>
                        </>
                      ) : (
                        <i className="ti ti-plus text-[11px] text-rose-700 group-hover:text-emerald-700 group-hover:scale-125 transition-transform"></i>
                      )}
                      <span>{palavra}</span>
                      {jaAdicionada && (
                        <span className="text-[10px] bg-emerald-200/70 group-hover:bg-rose-200/70 px-1 rounded font-normal">
                          No currículo
                        </span>
                      )}
                    </button>
                  );
                })}
                {(!dadosAts.palavras_chave.faltantes || dadosAts.palavras_chave.faltantes.length === 0) && (
                  <span className="text-xs text-emerald-700">Todas as principais palavras-chave já estão presentes!</span>
                )}
              </div>
              <p className="text-[11px] text-gray-500 leading-tight">
                * Inclua apenas termos em que você tenha real domínio técnico para garantir transparência nas entrevistas.
              </p>
            </div>
          </div>
        )}

        {/* Score de Aderência */}
        <div className="rounded-xl border-[0.5px] border-black bg-white p-6 flex flex-col sm:flex-row items-center gap-6">
          <AnelProgresso pontuacao={pontuacao} tamanho={96} espessura={8} />
          <div className="text-center sm:text-left">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">Score de Aderência</span>
            <h3 className="font-brand text-xl font-bold text-black">{rotulo}</h3>
            <p className="text-sm text-gray-600 mt-1 max-w-lg">
              {dadosAts?.explicacao_ats ||
                "Calculado pela sobreposição entre requisitos da vaga e evidências encontradas no seu currículo. Para ATS, valores acima de 75% são recomendados."}
            </p>
          </div>
        </div>

        {/* Requisitos e evidências */}
        {dadosAts?.requisitos_avaliados?.length > 0 && (
          <div className="rounded-xl border-[0.5px] border-black bg-white p-6 space-y-4">
            <div className="flex items-center gap-2">
              <i className="ti ti-list-check text-[22px] text-[#1e5e3f]"></i>
              <h3 className="font-brand text-lg font-bold text-black">Requisitos e evidências</h3>
            </div>
            <ul className="space-y-2">
              {dadosAts.requisitos_avaliados.map((item, idx) => {
                const estiloStatus =
                  {
                    evidenciado: "border-emerald-200 bg-emerald-50 text-emerald-900",
                    parcial: "border-amber-200 bg-amber-50 text-amber-900",
                    nao_evidenciado: "border-rose-200 bg-rose-50 text-rose-900",
                  }[item.status] || "border-gray-200 bg-gray-50 text-gray-800";
                const rotuloStatus =
                  {
                    evidenciado: "Evidenciado",
                    parcial: "Parcial",
                    nao_evidenciado: "Não evidenciado",
                  }[item.status] || "Não identificado";
                return (
                  <li key={`${item.requisito}-${idx}`} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-black">{item.requisito}</span>
                      <span className="rounded-full bg-white border border-gray-200 px-2 py-0.5 text-xs text-gray-700">
                        {item.tipo === "obrigatorio" ? "Obrigatório" : "Desejável"}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${estiloStatus}`}>
                        {rotuloStatus}
                      </span>
                    </div>
                    {item.evidencia && <p className="mt-2 text-sm text-gray-600">{item.evidencia}</p>}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Diagnóstico Crítico */}
        <div className="rounded-xl border-[0.5px] border-black bg-white p-6 space-y-5">
          <h3 className="font-brand text-lg font-bold text-black">Diagnóstico crítico</h3>

          <div className="flex gap-3">
            <span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-emerald-600 shrink-0"></span>
            <div>
              <p className="font-semibold text-sm text-black">Pontos Fortes</p>
              {dadosAts?.diagnostico_ats.pontos_fortes?.length > 0 ? (
                <ul className="mt-1 space-y-1 text-sm text-gray-600">
                  {dadosAts.diagnostico_ats.pontos_fortes.map((ponto, idx) => (
                    <li key={idx}>{ponto}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">Nenhum ponto forte destacado nesta análise.</p>
              )}
            </div>
          </div>

          <div className="flex gap-3">
            <span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-amber-500 shrink-0"></span>
            <div>
              <p className="font-semibold text-sm text-black">Descrições genéricas</p>
              {pontosAtencao.length > 0 ? (
                <ul className="mt-1 space-y-1 text-sm text-gray-600">
                  {pontosAtencao.map((ponto, idx) => (
                    <li key={idx}>{ponto}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">Nenhuma descrição genérica detectada.</p>
              )}
            </div>
          </div>
        </div>

        {/* Feedback de alterações interativas */}
        {feedbackMensagem && (
          <div className="flex items-center justify-between gap-3 rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 shadow-sm animate-fade-in">
            <div className="flex items-center gap-2">
              <i className="ti ti-circle-check text-base text-emerald-700"></i>
              <span>{feedbackMensagem}</span>
            </div>
            <button
              type="button"
              onClick={() => setFeedbackMensagem("")}
              className="text-emerald-700 hover:text-emerald-950 text-xs font-semibold"
            >
              <i className="ti ti-x text-sm"></i>
            </button>
          </div>
        )}

        {/* Sugestões de Reescrita Lado a Lado */}
        {sugestoesState.length > 0 && (
          <div className="rounded-xl border-[0.5px] border-black bg-white p-6 space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <i className="ti ti-writing text-[22px] text-[#1e5e3f]"></i>
                  <h3 className="font-brand text-lg font-bold text-black">
                    Sugestões de Reescrita Lado a Lado
                  </h3>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  Revise, edite e escolha quais sugestões aplicar diretamente ao currículo.
                </p>
              </div>

              <button
                type="button"
                onClick={aplicarTodasSugestoes}
                disabled={aplicandoTodas || sugestoesState.every((s) => s.aplicada)}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1e5e3f] px-4 py-2 text-xs font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {aplicandoTodas ? (
                  <>
                    <i className="ti ti-loader animate-spin text-sm"></i>
                    <span>Aplicando todas...</span>
                  </>
                ) : sugestoesState.every((s) => s.aplicada) ? (
                  <>
                    <i className="ti ti-checks text-sm text-emerald-300"></i>
                    <span>Todas as sugestões aplicadas</span>
                  </>
                ) : (
                  <>
                    <i className="ti ti-checks text-sm"></i>
                    <span>Aplicar todas as sugestões</span>
                  </>
                )}
              </button>
            </div>

            <div className="space-y-4">
              {sugestoesState.map((sugestao, idx) => (
                <div
                  key={idx}
                  className={`rounded-xl border transition-all p-4 md:p-5 space-y-3 ${
                    sugestao.aplicada
                      ? "border-emerald-300 bg-emerald-50/20 shadow-sm ring-1 ring-emerald-200"
                      : "border-gray-200 bg-[#fafafa]"
                  }`}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Versão Original */}
                    <div className="rounded-lg border border-rose-200 bg-white p-3.5 space-y-2 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-rose-600">
                            <i className="ti ti-file-text"></i> Original no seu currículo
                          </span>
                          {sugestao.campo && (
                            <span className="text-[10px] text-gray-400 font-mono">
                              {sugestao.campo}
                            </span>
                          )}
                        </div>
                        <p className="mt-1.5 text-xs text-gray-700 italic font-mono bg-rose-50/50 p-2.5 rounded border border-rose-100">
                          "{sugestao.trecho_original}"
                        </p>
                      </div>
                    </div>

                    {/* Versão Otimizada */}
                    <div
                      className={`rounded-lg border p-3.5 space-y-2.5 transition-all ${
                        sugestao.aplicada
                          ? "border-emerald-300 bg-emerald-50/40"
                          : "border-emerald-200 bg-white"
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                            <i className="ti ti-sparkles"></i> Sugestão Otimizada para ATS
                          </span>
                          {sugestao.aplicada && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                              <i className="ti ti-check"></i> No currículo
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-1.5">
                          {!sugestao.editando && (
                            <>
                              <button
                                type="button"
                                onClick={() => copiarTextoIndividual(sugestao.versaoOtimizada, idx)}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-gray-600 hover:text-gray-900 px-2 py-1 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
                                title="Copiar texto"
                              >
                                <i className={`ti ${copiadoIdx === idx ? "ti-check text-emerald-600" : "ti-copy"} text-xs`}></i>
                                <span>{copiadoIdx === idx ? "Copiado!" : "Copiar"}</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => toggleEdicaoSugestao(idx, true)}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1e5e3f] hover:text-[#174a32] px-2 py-1 rounded border border-[#1e5e3f]/30 hover:bg-emerald-50 transition-colors"
                                title="Editar texto sugerido"
                              >
                                <i className="ti ti-pencil text-xs"></i>
                                <span>Editar</span>
                              </button>
                            </>
                          )}

                          {sugestao.aplicada ? (
                            <button
                              type="button"
                              onClick={() => reverterSugestao(idx)}
                              disabled={sugestao.salvando}
                              className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-700 hover:text-rose-900 px-2.5 py-1 rounded border border-rose-300 bg-rose-50 hover:bg-rose-100 transition-colors disabled:opacity-50"
                              title="Desfazer e restaurar texto original no currículo"
                            >
                              {sugestao.salvando ? (
                                <i className="ti ti-loader animate-spin"></i>
                              ) : (
                                <i className="ti ti-arrow-back-up"></i>
                              )}
                              <span>Desfazer</span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => aplicarSugestao(idx)}
                              disabled={sugestao.salvando}
                              className="inline-flex items-center gap-1 text-[11px] font-bold text-white bg-[#1e5e3f] hover:bg-[#174a32] px-3 py-1 rounded shadow-sm transition-colors disabled:opacity-50"
                              title="Aplicar esta sugestão ao seu currículo"
                            >
                              {sugestao.salvando ? (
                                <i className="ti ti-loader animate-spin"></i>
                              ) : (
                                <i className="ti ti-check"></i>
                              )}
                              <span>Aplicar</span>
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Área de texto em modo edição ou exibição */}
                      {sugestao.editando ? (
                        <div className="space-y-2 pt-1">
                          <textarea
                            value={sugestao.textoTemp}
                            onChange={(e) => atualizarTextoTempSugestao(idx, e.target.value)}
                            rows={3}
                            className="w-full text-xs text-gray-900 bg-white p-2.5 rounded border border-emerald-400 focus:outline-none focus:ring-2 focus:ring-[#1e5e3f] font-sans resize-y leading-relaxed"
                            placeholder="Personalize o texto como preferir antes de aplicar..."
                          />
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                            <span className="text-[11px] text-gray-500">
                              Você pode ajustar palavras antes de salvar.
                            </span>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => toggleEdicaoSugestao(idx, false)}
                                className="px-2.5 py-1 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 text-[11px] font-semibold"
                              >
                                Cancelar
                              </button>
                              <button
                                type="button"
                                onClick={() => salvarTextoEditadoSugestao(idx)}
                                className="px-2.5 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-800 text-[11px] font-semibold"
                              >
                                Salvar texto
                              </button>
                              <button
                                type="button"
                                onClick={() => salvarEAplicarSugestao(idx)}
                                disabled={sugestao.salvando}
                                className="px-3 py-1 rounded bg-[#1e5e3f] hover:bg-[#174a32] text-white text-[11px] font-bold shadow-sm inline-flex items-center gap-1"
                              >
                                {sugestao.salvando && <i className="ti ti-loader animate-spin"></i>}
                                <span>Salvar e aplicar</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-emerald-950 font-medium bg-emerald-50/60 p-2.5 rounded border border-emerald-100 leading-relaxed">
                          {sugestao.versaoOtimizada}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Justificativa */}
                  {sugestao.justificativa && (
                    <div className="flex items-start gap-2 pt-1 text-xs text-gray-500">
                      <i className="ti ti-bulb text-amber-500 mt-0.5 text-sm flex-shrink-0"></i>
                      <p>
                        <strong className="text-gray-700">Por que funciona melhor no ATS:</strong> {sugestao.justificativa}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ações finais */}
        <div className="flex flex-col sm:flex-row gap-3 pb-6">
          <button
            type="button"
            onClick={exportarCurriculoOtimizado}
            disabled={transformando}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[#1e5e3f] px-5 py-3 font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors disabled:opacity-60 disabled:cursor-wait"
          >
            <i className={`ti ${transformando ? "ti-loader animate-spin" : "ti-download"}`}></i>
            {transformando ? "Aplicando sugestões..." : "Exportar Currículo Otimizado"}
          </button>
          <button
            type="button"
            onClick={copiarReescritas}
            disabled={!dadosAts?.sugestoes_reescrita?.length}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[#06331d] px-5 py-3 font-bold text-white hover:bg-[#0a2b1a] shadow-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <i className={`ti ${copiado ? "ti-check" : "ti-copy"}`}></i>
            {copiado ? "Copiado!" : "Copiar Reescritas"}
          </button>
        </div>
      </main>
    </div>
  );
}
