import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import AnelProgresso, { classificarAderencia } from "../components/AnelProgresso.jsx";
import { listarAnalises } from "../api/analiseApi.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

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
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";
  const idAnalise = searchParams.get("id") || "";

  const [analise, setAnalise] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [copiado, setCopiado] = useState(false);

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
              <h4 className="font-brand font-bold text-black">
                Lacunas técnicas / Termos ausentes ({dadosAts.palavras_chave.faltantes?.length || 0})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {dadosAts.palavras_chave.faltantes?.map((palavra, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-100 text-rose-900 border border-rose-200"
                  >
                    {palavra}
                  </span>
                ))}
                {(!dadosAts.palavras_chave.faltantes || dadosAts.palavras_chave.faltantes.length === 0) && (
                  <span className="text-xs text-emerald-700">Todas as principais palavras-chave já estão presentes!</span>
                )}
              </div>
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

          <div className="flex gap-3">
            <span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-gray-400 shrink-0"></span>
            <div>
              <p className="font-semibold text-sm text-black">Sugestões de reescrita</p>
              <p className="text-sm text-gray-500">
                {dadosAts?.sugestoes_reescrita?.length > 0
                  ? `${dadosAts.sugestoes_reescrita.length} sugestão(ões) de reescrita disponível(is) — use "Copiar Reescritas" abaixo.`
                  : "Sem sugestões de reescrita, apenas detalhes pontuais."}
              </p>
            </div>
          </div>
        </div>

        {/* Ações finais */}
        <div className="flex flex-col sm:flex-row gap-3 pb-6">
          <Link
            to={`/templates?email=${encodeURIComponent(emailInicial)}`}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[#1e5e3f] px-5 py-3 font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors"
          >
            <i className="ti ti-download"></i>
            Exportar Currículo Otimizado
          </Link>
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
