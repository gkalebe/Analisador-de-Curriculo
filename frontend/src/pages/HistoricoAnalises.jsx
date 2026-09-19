import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { listarAnalises } from "../api/analiseApi.js";
import { formatarDataUpload } from "../models/curriculo.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

export default function HistoricoAnalises() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [analises, setAnalises] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [analiseExpandidaId, setAnaliseExpandidaId] = useState(null);
  const [copiadoIdx, setCopiadoIdx] = useState(null);

  useEffect(() => {
    if (!emailInicial) return;
    setCarregando(true);
    setErro("");
    listarAnalises(emailInicial)
      .then((resposta) => {
        setAnalises(resposta.analises || []);
        // Se houver análises, já deixa a mais recente expandida
        if (resposta.analises && resposta.analises.length > 0) {
          setAnaliseExpandidaId(resposta.analises[0].id_analise);
        }
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        } else {
          setErro("Não foi possível carregar o histórico de análises.");
        }
      })
      .finally(() => setCarregando(false));
  }, [emailInicial]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo });
  }

  function copiarTexto(texto, idx) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(texto);
    setCopiadoIdx(idx);
    setTimeout(() => setCopiadoIdx(null), 2500);
  }

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

  // Estatísticas calculadas
  const totalAnalises = analises.length;
  const mediaPontuacao = totalAnalises > 0
    ? Math.round(analises.reduce((acc, a) => acc + (a.pontuacao || 0), 0) / totalAnalises)
    : 0;
  const melhorPontuacao = totalAnalises > 0
    ? Math.round(Math.max(...analises.map((a) => a.pontuacao || 0)))
    : 0;

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="historico" />

      <main className="flex-1 p-6 space-y-6 max-w-7xl md:h-screen md:overflow-y-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-brand text-[32px] font-bold text-black">Histórico de análises</h1>
            <p className="mt-1 text-lg font-semibold text-[#727272]">
              Consulte todas as análises de aderência ATS realizadas e salvas no banco de dados.
            </p>
          </div>
          {emailInicial && (
            <Link
              to={`/analises/nova?email=${encodeURIComponent(emailInicial)}`}
              className="inline-flex items-center gap-2 rounded-lg bg-[#1e5e3f] px-4 py-2.5 font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors self-start sm:self-auto"
            >
              <i className="ti ti-plus"></i>
              Nova análise
            </Link>
          )}
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

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}

        {emailInicial && carregando && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-12 text-center text-gray-500 space-y-3">
            <i className="ti ti-loader animate-spin text-[36px] text-[#1e5e3f]"></i>
            <p className="font-brand text-lg font-semibold">Carregando histórico do banco de dados...</p>
          </div>
        )}

        {emailInicial && !carregando && totalAnalises > 0 && (
          <>
            {/* Cards de Métricas Gerais */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-xl border-[0.5px] border-black bg-white p-5 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Total de Análises
                </span>
                <div className="flex items-center gap-3 mt-2">
                  <div className="w-10 h-10 rounded-lg bg-emerald-50 text-[#1e5e3f] flex items-center justify-center">
                    <i className="ti ti-file-analytics text-xl"></i>
                  </div>
                  <span className="font-brand text-3xl font-extrabold text-black">{totalAnalises}</span>
                </div>
              </div>

              <div className="rounded-xl border-[0.5px] border-black bg-white p-5 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Média de Aderência ATS
                </span>
                <div className="flex items-center gap-3 mt-2">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
                    <i className="ti ti-chart-line text-xl"></i>
                  </div>
                  <span className="font-brand text-3xl font-extrabold text-black">{mediaPontuacao}%</span>
                </div>
              </div>

              <div className="rounded-xl border-[0.5px] border-black bg-white p-5 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Melhor Pontuação
                </span>
                <div className="flex items-center gap-3 mt-2">
                  <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                    <i className="ti ti-trophy text-xl"></i>
                  </div>
                  <span className="font-brand text-3xl font-extrabold text-black">{melhorPontuacao}%</span>
                </div>
              </div>
            </div>

            {/* Lista de Análises Realizadas */}
            <div className="space-y-4">
              {analises.map((item) => {
                const expandida = analiseExpandidaId === item.id_analise;
                const dadosAts = extrairDadosAts(item.observacoes);
                const pontuacao = item.pontuacao != null ? Math.round(item.pontuacao) : null;
                const corBadge = pontuacao >= 70 ? "bg-emerald-100 text-emerald-800 border-emerald-300" : pontuacao >= 50 ? "bg-amber-100 text-amber-800 border-amber-300" : "bg-rose-100 text-rose-800 border-rose-300";
                const corProgresso = pontuacao >= 70 ? "bg-emerald-600" : pontuacao >= 50 ? "bg-amber-500" : "bg-rose-500";
                const rotuloNivel = pontuacao >= 70 ? "Excelente Aderência" : pontuacao >= 50 ? "Aderência Moderada" : "Baixa Aderência";

                return (
                  <div
                    key={item.id_analise}
                    className="rounded-xl border-[0.5px] border-black bg-white shadow-sm overflow-hidden transition-all"
                  >
                    {/* Linha Resumo da Análise */}
                    <div
                      onClick={() => setAnaliseExpandidaId(expandida ? null : item.id_analise)}
                      className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-gray-50/70 transition-colors"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">
                            {formatarDataUpload(item.data_analise)}
                          </span>
                          <span className="text-gray-300">•</span>
                          <span className="text-xs font-mono text-gray-400">
                            ID: {item.id_analise.slice(0, 8)}
                          </span>
                        </div>
                        <h3 className="font-brand text-lg md:text-xl font-bold text-black flex items-center gap-2 truncate">
                          <i className="ti ti-briefcase text-[#1e5e3f]"></i>
                          {item.titulo_vaga || "Vaga sem título"}
                        </h3>
                        {item.nome_curriculo && (
                          <p className="text-xs text-gray-600 flex items-center gap-1.5">
                            <i className="ti ti-file-text text-gray-400"></i>
                            {item.nome_curriculo}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-4 self-start md:self-center">
                        {pontuacao != null && (
                          <div className="flex items-center gap-2">
                            <span className="font-brand text-2xl font-extrabold text-black">
                              {pontuacao}%
                            </span>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${corBadge}`}>
                              {rotuloNivel}
                            </span>
                          </div>
                        )}
                        <button
                          type="button"
                          className="w-8 h-8 rounded-full border border-gray-200 flex items-center justify-center text-gray-500 hover:text-black hover:bg-gray-100 transition-colors"
                        >
                          <i className={`ti ${expandida ? "ti-chevron-up" : "ti-chevron-down"}`}></i>
                        </button>
                      </div>
                    </div>

                    {/* Detalhe Expandido: Relatório ATS Completo */}
                    {expandida && (
                      <div className="border-t border-gray-200 p-6 md:p-8 bg-[#fafafa] space-y-6 animate-fadeIn">
                        {/* Card de Pontuação ATS com barra */}
                        {pontuacao != null && (
                          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                              <div>
                                <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                                  Compatibilidade da Análise
                                </span>
                                <div className="flex items-baseline gap-3 mt-1">
                                  <span className="font-brand text-3xl font-extrabold text-black">
                                    {pontuacao}%
                                  </span>
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${corBadge}`}>
                                    {rotuloNivel}
                                  </span>
                                </div>
                              </div>
                              <div className="text-xs text-gray-600 max-w-lg sm:text-right">
                                {dadosAts?.explicacao_ats ||
                                  "A pontuação reflete o alinhamento de competências, clareza textual e aderência aos requisitos técnicos da vaga."}
                              </div>
                            </div>

                            <div className="w-full bg-gray-200 h-2.5 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${corProgresso}`}
                                style={{ width: `${pontuacao}%` }}
                              ></div>
                            </div>

                            <div className="flex items-start gap-2 rounded-lg bg-gray-50 border border-gray-200 p-3 text-xs text-gray-600">
                              <i className="ti ti-info-circle text-gray-500 mt-0.5 flex-shrink-0 text-sm"></i>
                              <p>
                                <strong>Transparência ATS (RN-011):</strong> Este índice mensura a probabilidade de leitura fluida por filtros automáticos ATS e aderência de vocabulário técnico, sem garantir contratação automática.
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Palavras-Chave */}
                        {dadosAts?.palavras_chave && (
                          <div className="space-y-3">
                            <h4 className="font-brand text-lg font-bold text-black flex items-center gap-2">
                              <i className="ti ti-tag text-[#1e5e3f]"></i>
                              Palavras-Chave & Vocabulário Técnico
                            </h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="rounded-lg border border-emerald-200 bg-white p-4 space-y-2.5">
                                <span className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                                  <i className="ti ti-circle-check text-emerald-600"></i>
                                  Encontradas no currículo ({dadosAts.palavras_chave.encontradas?.length || 0})
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {dadosAts.palavras_chave.encontradas?.map((palavra, idx) => (
                                    <span
                                      key={idx}
                                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-900 border border-emerald-200"
                                    >
                                      <i className="ti ti-check text-[10px]"></i>
                                      {palavra}
                                    </span>
                                  ))}
                                  {(!dadosAts.palavras_chave.encontradas || dadosAts.palavras_chave.encontradas.length === 0) && (
                                    <span className="text-xs text-gray-500">Nenhum termo técnico coincidente encontrado diretamente.</span>
                                  )}
                                </div>
                              </div>

                              <div className="rounded-lg border border-amber-200 bg-white p-4 space-y-2.5">
                                <span className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                                  <i className="ti ti-alert-triangle text-amber-600"></i>
                                  Ausentes na descrição ({dadosAts.palavras_chave.faltantes?.length || 0})
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {dadosAts.palavras_chave.faltantes?.map((palavra, idx) => (
                                    <span
                                      key={idx}
                                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-200"
                                    >
                                      <i className="ti ti-plus text-[10px]"></i>
                                      {palavra}
                                    </span>
                                  ))}
                                  {(!dadosAts.palavras_chave.faltantes || dadosAts.palavras_chave.faltantes.length === 0) && (
                                    <span className="text-xs text-emerald-700">Todas as principais palavras-chave da vaga já estão presentes!</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Diagnóstico Estrutural */}
                        {dadosAts?.diagnostico_ats && (
                          <div className="space-y-3">
                            <h4 className="font-brand text-lg font-bold text-black flex items-center gap-2">
                              <i className="ti ti-layout-grid text-[#1e5e3f]"></i>
                              Diagnóstico Crítico da Estrutura
                            </h4>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
                                <span className="text-xs font-bold text-emerald-700 flex items-center gap-1.5">
                                  <i className="ti ti-circle-check"></i> Pontos Fortes (Manter)
                                </span>
                                <ul className="space-y-1.5 text-xs text-gray-700">
                                  {dadosAts.diagnostico_ats.pontos_fortes?.map((ponto, idx) => (
                                    <li key={idx} className="flex items-start gap-1.5">
                                      <span className="text-emerald-600 mt-0.5">•</span>
                                      <span>{ponto}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
                                <span className="text-xs font-bold text-blue-700 flex items-center gap-1.5">
                                  <i className="ti ti-arrows-sort"></i> Ordem & Prioridade
                                </span>
                                <ul className="space-y-1.5 text-xs text-gray-700">
                                  {dadosAts.diagnostico_ats.a_reorganizar?.map((ponto, idx) => (
                                    <li key={idx} className="flex items-start gap-1.5">
                                      <span className="text-blue-600 mt-0.5">•</span>
                                      <span>{ponto}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
                                <span className="text-xs font-bold text-rose-700 flex items-center gap-1.5">
                                  <i className="ti ti-scissors"></i> O Que Cortar / Simplificar
                                </span>
                                <ul className="space-y-1.5 text-xs text-gray-700">
                                  {dadosAts.diagnostico_ats.a_remover?.map((ponto, idx) => (
                                    <li key={idx} className="flex items-start gap-1.5">
                                      <span className="text-rose-600 mt-0.5">•</span>
                                      <span>{ponto}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Sugestões de Reescrita Lado a Lado */}
                        {dadosAts?.sugestoes_reescrita && dadosAts.sugestoes_reescrita.length > 0 && (
                          <div className="space-y-3">
                            <h4 className="font-brand text-lg font-bold text-black flex items-center gap-2">
                              <i className="ti ti-writing text-[#1e5e3f]"></i>
                              Sugestões de Reescrita Lado a Lado
                            </h4>
                            <div className="space-y-3">
                              {dadosAts.sugestoes_reescrita.map((sugestao, idx) => (
                                <div
                                  key={idx}
                                  className="rounded-xl border border-gray-200 bg-white p-4 space-y-3"
                                >
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="rounded-lg border border-rose-200 bg-rose-50/30 p-3 space-y-1">
                                      <span className="text-[11px] font-bold uppercase tracking-wider text-rose-600">
                                        Original no currículo
                                      </span>
                                      <p className="text-xs text-gray-700 italic font-mono">
                                        "{sugestao.trecho_original}"
                                      </p>
                                    </div>
                                    <div className="rounded-lg border border-emerald-200 bg-emerald-50/40 p-3 space-y-1">
                                      <div className="flex items-center justify-between">
                                        <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">
                                          Sugestão Otimizada ATS
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => copiarTexto(sugestao.versao_otimizada, `${item.id_analise}-${idx}`)}
                                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1e5e3f] hover:text-[#174a32] px-2 py-0.5 rounded border border-[#1e5e3f]/30 hover:bg-emerald-50 transition-colors"
                                        >
                                          {copiadoIdx === `${item.id_analise}-${idx}` ? (
                                            <>
                                              <i className="ti ti-check text-xs"></i> Copiado!
                                            </>
                                          ) : (
                                            <>
                                              <i className="ti ti-copy text-xs"></i> Copiar
                                            </>
                                          )}
                                        </button>
                                      </div>
                                      <p className="text-xs text-emerald-950 font-medium">
                                        {sugestao.versao_otimizada}
                                      </p>
                                    </div>
                                  </div>
                                  {sugestao.justificativa && (
                                    <p className="text-xs text-gray-500 pt-1">
                                      <strong>Justificativa ATS:</strong> {sugestao.justificativa}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Fallback texto puro */}
                        {!dadosAts && item.observacoes && (
                          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-1">
                            <p className="text-xs font-bold uppercase text-gray-500">Parecer</p>
                            <p className="text-sm text-gray-800 whitespace-pre-wrap">{item.observacoes}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}

        {emailInicial && !carregando && totalAnalises === 0 && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-12 text-center text-gray-500 space-y-4">
            <i className="ti ti-history-off text-[48px] text-gray-400"></i>
            <div className="space-y-1">
              <p className="font-brand text-xl font-bold text-gray-800">Nenhuma análise salva no histórico</p>
              <p className="text-sm text-gray-500">
                Você ainda não realizou nenhuma comparação entre vaga e currículo.
              </p>
            </div>
            <Link
              to={`/analises/nova?email=${encodeURIComponent(emailInicial)}`}
              className="inline-flex items-center gap-2 rounded-lg bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors"
            >
              <i className="ti ti-search"></i>
              Realizar primeira análise
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
