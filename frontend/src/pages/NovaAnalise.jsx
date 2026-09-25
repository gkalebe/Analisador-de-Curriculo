import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { criarAnalise } from "../api/analiseApi.js";
import { listarVagas } from "../api/vagasApi.js";
import { listarCurriculos } from "../api/curriculoApi.js";
import { formatarDataUpload, formatarTamanhoArquivo, validarArquivoCurriculo } from "../models/curriculo.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

export default function NovaAnalise() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [vagas, setVagas] = useState([]);
  const [idVagaSelecionada, setIdVagaSelecionada] = useState("");
  const [curriculos, setCurriculos] = useState([]);
  const [origemCurriculo, setOrigemCurriculo] = useState("salvo"); // "salvo" ou "novo"
  const [idCurriculoSelecionado, setIdCurriculoSelecionado] = useState("");
  const [arquivo, setArquivo] = useState(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [avisoIndisponivel, setAvisoIndisponivel] = useState("");
  const [resultado, setResultado] = useState(null);
  const [copiadoIdx, setCopiadoIdx] = useState(null);

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

  useEffect(() => {
    if (!emailInicial) return;
    listarVagas(emailInicial)
      .then((resposta) => setVagas(resposta.vagas || []))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        }
      });

    listarCurriculos(emailInicial)
      .then((resposta) => {
        const lista = resposta.curriculos || [];
        setCurriculos(lista);
        if (lista.length > 0) {
          setIdCurriculoSelecionado(lista[0].id_curriculo);
          setOrigemCurriculo("salvo");
        } else {
          setOrigemCurriculo("novo");
        }
      })
      .catch(() => { });
  }, [emailInicial]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo });
  }

  function selecionarArquivo(file) {
    setResultado(null);
    const mensagemErro = validarArquivoCurriculo(file);
    if (mensagemErro) {
      setErro(mensagemErro);
      setArquivo(null);
      return;
    }
    setErro("");
    setArquivo(file);
  }

  function aoSoltarArquivo(evento) {
    evento.preventDefault();
    setArrastando(false);
    const file = evento.dataTransfer.files?.[0];
    if (file) selecionarArquivo(file);
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    if (!idVagaSelecionada) {
      setErro("Selecione uma vaga antes de iniciar a análise.");
      return;
    }

    if (origemCurriculo === "salvo" && !idCurriculoSelecionado) {
      setErro("Selecione um currículo salvo ou envie um novo arquivo.");
      return;
    }

    if (origemCurriculo === "novo" && !arquivo) {
      setErro("Selecione um arquivo de currículo para envio.");
      return;
    }

    setErro("");
    setAvisoIndisponivel("");
    setResultado(null);
    setEnviando(true);

    try {
      const payload = {
        email: emailInicial,
        idVaga: idVagaSelecionada,
        idCurriculo: origemCurriculo === "salvo" ? idCurriculoSelecionado : undefined,
        file: origemCurriculo === "novo" ? arquivo : undefined,
      };
      const resposta = await criarAnalise(payload);
      setResultado(resposta);
      if (origemCurriculo === "novo") {
        setArquivo(null);
        listarCurriculos(emailInicial).then((res) => setCurriculos(res.curriculos || []));
      }
    } catch (e) {
      if (e instanceof ApiError && (e.status === 501 || e.status === 503)) {
        setAvisoIndisponivel(e.message);
      } else {
        setErro(e instanceof ApiError ? e.message : "Não foi possível concluir a análise. Tente novamente.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="analise" />

      <main className="flex-1 p-6 space-y-6 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Nova análise</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Escolha uma vaga cadastrada e selecione um currículo já salvo ou envie um novo para comparar os dois.
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

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}

        {avisoIndisponivel && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
            {avisoIndisponivel}
          </div>
        )}

        {resultado && (() => {
          const dadosAts = extrairDadosAts(resultado.observacoes);
          const pontuacao = resultado.pontuacao != null ? Math.round(resultado.pontuacao) : null;
          const corBadge = pontuacao >= 70 ? "bg-emerald-100 text-emerald-800 border-emerald-300" : pontuacao >= 50 ? "bg-amber-100 text-amber-800 border-amber-300" : "bg-rose-100 text-rose-800 border-rose-300";
          const corProgresso = pontuacao >= 70 ? "bg-emerald-600" : pontuacao >= 50 ? "bg-amber-500" : "bg-rose-500";
          const rotuloNivel = pontuacao >= 70 ? "Excelente Aderência" : pontuacao >= 50 ? "Aderência Moderada" : "Baixa Aderência";

          return (
            <div className="rounded-xl border-[0.5px] border-black bg-white shadow-sm overflow-hidden space-y-6 p-6 md:p-8">
              {/* Cabeçalho do Relatório */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-900">
                      <i className="ti ti-sparkles text-xs"></i> Inteligência Artificial Gemini
                    </span>
                    <span className="text-xs text-gray-400">Análise concluída</span>
                  </div>
                  <h2 className="font-brand text-2xl md:text-3xl font-bold text-black">
                    Diagnóstico de Aderência ATS
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setResultado(null)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <i className="ti ti-refresh text-sm"></i>
                    Nova análise
                  </button>
                  <Link
                    to={`/templates?email=${encodeURIComponent(emailInicial)}`}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#1e5e3f] px-3 py-2 text-xs font-semibold text-white hover:bg-[#174a32] transition-colors"
                  >
                    <i className="ti ti-template text-sm"></i>
                    Templates ATS
                  </Link>
                </div>
              </div>

              {/* Card de Pontuação ATS (RN-006 & RN-011) */}
              {pontuacao != null && (
                <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-[#f8faf9] to-[#ffffff] p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                        Índice de Compatibilidade com a Vaga
                      </span>
                      <div className="flex items-baseline gap-3 mt-1">
                        <span className="font-brand text-4xl md:text-5xl font-extrabold text-black">
                          {pontuacao}%
                        </span>
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${corBadge}`}>
                          {rotuloNivel}
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 max-w-md sm:text-right">
                      {dadosAts?.explicacao_ats ||
                        "A pontuação reflete o alinhamento de competências, clareza textual e aderência aos requisitos técnicos da vaga."}
                    </div>
                  </div>

                  {/* Barra de Progresso */}
                  <div className="w-full bg-gray-200 h-3 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-1000 ease-out ${corProgresso}`}
                      style={{ width: `${pontuacao}%` }}
                    ></div>
                  </div>

                  <div className="flex items-start gap-2 rounded-lg bg-gray-50 border border-gray-200 p-3 text-xs text-gray-600">
                    <i className="ti ti-info-circle text-gray-500 mt-0.5 flex-shrink-0 text-sm"></i>
                    <p>
                      <strong>Transparência ATS (RN-011):</strong> Este índice mensura a probabilidade de leitura fluida por filtros automáticos ATS e aderência de vocabulário técnico. Ele não garante contratação automática e deve ser usado como guia de evolução contínua.
                    </p>
                  </div>
                </div>
              )}

              {/* Seção de Palavras-Chave Identificadas */}
              {dadosAts?.palavras_chave && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <i className="ti ti-tag text-[22px] text-[#1e5e3f]"></i>
                    <h3 className="font-brand text-xl font-bold text-black">
                      Palavras-Chave & Vocabulário Técnico da Vaga
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Encontradas */}
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 space-y-3">
                      <div className="flex items-center gap-2 text-emerald-900 font-semibold text-sm">
                        <i className="ti ti-circle-check text-emerald-600 text-base"></i>
                        <span>Encontradas no seu currículo ({dadosAts.palavras_chave.encontradas?.length || 0})</span>
                      </div>
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

                    {/* Faltantes ou Recomendadas */}
                    <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-3">
                      <div className="flex items-center gap-2 text-amber-900 font-semibold text-sm">
                        <i className="ti ti-alert-triangle text-amber-600 text-base"></i>
                        <span>Ausentes na sua descrição ({dadosAts.palavras_chave.faltantes?.length || 0})</span>
                      </div>
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
                      <p className="text-[11px] text-amber-800 leading-tight">
                        * Inclua estes termos apenas se você tiver real vivência neles (veracidade absoluta).
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Diagnóstico Estrutural ATS */}
              {dadosAts?.diagnostico_ats && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <i className="ti ti-layout-grid text-[22px] text-[#1e5e3f]"></i>
                    <h3 className="font-brand text-xl font-bold text-black">
                      Diagnóstico Crítico da Estrutura
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Pontos Fortes */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2.5 shadow-sm">
                      <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm">
                        <i className="ti ti-circle-check text-lg"></i>
                        <span>Pontos Fortes (Manter)</span>
                      </div>
                      <ul className="space-y-2 text-xs text-gray-700">
                        {dadosAts.diagnostico_ats.pontos_fortes?.map((ponto, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-emerald-600 mt-0.5">•</span>
                            <span>{ponto}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* A Reorganizar */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2.5 shadow-sm">
                      <div className="flex items-center gap-2 text-blue-700 font-bold text-sm">
                        <i className="ti ti-arrows-sort text-lg"></i>
                        <span>Ordem & Prioridade</span>
                      </div>
                      <ul className="space-y-2 text-xs text-gray-700">
                        {dadosAts.diagnostico_ats.a_reorganizar?.map((ponto, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-blue-600 mt-0.5">•</span>
                            <span>{ponto}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* A Remover ou Enxugar */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2.5 shadow-sm">
                      <div className="flex items-center gap-2 text-rose-700 font-bold text-sm">
                        <i className="ti ti-scissors text-lg"></i>
                        <span>O Que Cortar / Simplificar</span>
                      </div>
                      <ul className="space-y-2 text-xs text-gray-700">
                        {dadosAts.diagnostico_ats.a_remover?.map((ponto, idx) => (
                          <li key={idx} className="flex items-start gap-2">
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
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <i className="ti ti-writing text-[22px] text-[#1e5e3f]"></i>
                      <h3 className="font-brand text-xl font-bold text-black">
                        Sugestões de Reescrita Lado a Lado
                      </h3>
                    </div>
                    <span className="text-xs text-gray-500 hidden sm:inline">
                      Sem inventar qualificações
                    </span>
                  </div>

                  <div className="space-y-4">
                    {dadosAts.sugestoes_reescrita.map((sugestao, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl border border-gray-200 bg-[#fafafa] p-4 md:p-5 space-y-3"
                      >
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Versão Original */}
                          <div className="rounded-lg border border-rose-200 bg-white p-3 space-y-1.5">
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-rose-600">
                              <i className="ti ti-file-text"></i> Original no seu currículo
                            </span>
                            <p className="text-xs text-gray-700 italic font-mono bg-rose-50/50 p-2.5 rounded border border-rose-100">
                              "{sugestao.trecho_original}"
                            </p>
                          </div>

                          {/* Versão Otimizada */}
                          <div className="rounded-lg border border-emerald-200 bg-white p-3 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-emerald-700">
                                <i className="ti ti-sparkles"></i> Sugestão Otimizada para ATS
                              </span>
                              <button
                                type="button"
                                onClick={() => copiarTexto(sugestao.versao_otimizada, idx)}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1e5e3f] hover:text-[#174a32] px-2 py-0.5 rounded border border-[#1e5e3f]/30 hover:bg-emerald-50 transition-colors"
                              >
                                {copiadoIdx === idx ? (
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
                            <p className="text-xs text-emerald-950 font-medium bg-emerald-50/60 p-2.5 rounded border border-emerald-100">
                              {sugestao.versao_otimizada}
                            </p>
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

              {/* Fallback caso não seja JSON estruturado */}
              {!dadosAts && resultado.observacoes && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
                  <p className="text-xs font-bold uppercase text-gray-500 tracking-wider">Parecer do Avaliador</p>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{resultado.observacoes}</p>
                </div>
              )}

              {/* Rodapé do Diagnóstico com Ações */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  Pronto para aplicar as melhorias? Transforme este diagnóstico num currículo em template ATS.
                </p>
                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={() => setResultado(null)}
                    className="flex-1 sm:flex-none text-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Testar outra vaga / currículo
                  </button>
                  <Link
                    to={`/analises/editar?email=${encodeURIComponent(emailInicial)}&curriculo=${resultado.id_curriculo}`}
                    className="flex-1 sm:flex-none text-center rounded-lg bg-[#1e5e3f] px-5 py-2 text-sm font-bold text-white hover:bg-[#174a32] shadow-sm transition-colors"
                  >
                    Transformar em Template ATS
                  </Link>
                </div>
              </div>
            </div>
          );
        })()}

        {emailInicial && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
            <div className="flex items-center gap-3">
              <i className="ti ti-briefcase text-[28px] text-[#1e5e3f]"></i>
              <h2 className="font-brand text-[28px] text-black">1. Escolha a vaga</h2>
            </div>

            {vagas.length === 0 && (
              <p className="text-sm text-gray-500">
                Você ainda não tem nenhuma vaga salva. Cadastre uma na aba "Cadastrar vaga" antes de rodar uma análise.
              </p>
            )}

            {vagas.length > 0 && (
              <ul className="space-y-2">
                {vagas.map((vaga) => (
                  <li key={vaga.id_vaga}>
                    <label
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border-[0.5px] p-4 hover:border-[#1e5e3f] transition-colors ${idVagaSelecionada === vaga.id_vaga ? "border-[#1e5e3f] bg-[#f0fdf4]" : "border-gray-200"
                        }`}
                    >
                      <input
                        type="radio"
                        name="vaga"
                        value={vaga.id_vaga}
                        checked={idVagaSelecionada === vaga.id_vaga}
                        onChange={(e) => setIdVagaSelecionada(e.target.value)}
                        className="mt-1 text-[#1e5e3f] focus:ring-[#1e5e3f]"
                      />
                      <div>
                        <p className="font-medium text-black">{vaga.titulo || "(Sem título)"}</p>
                        <p className="text-sm text-gray-500">{vaga.area || "Área não informada"}</p>
                      </div>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {emailInicial && (
          <form
            onSubmit={aoEnviar}
            className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <i className="ti ti-file-analytics text-[28px] text-[#1e5e3f]"></i>
                <h2 className="font-brand text-[28px] text-black">2. Escolha o currículo</h2>
              </div>

              {/* Seletor de Origem: Salvo vs Novo */}
              <div className="flex rounded-lg border border-gray-300 p-1 bg-gray-100 text-sm self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setOrigemCurriculo("salvo")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-all ${origemCurriculo === "salvo"
                      ? "bg-white text-black shadow-sm font-semibold"
                      : "text-gray-600 hover:text-black"
                    }`}
                >
                  <i className="ti ti-folder-check"></i>
                  Currículo Salvo ({curriculos.length})
                </button>
                <button
                  type="button"
                  onClick={() => setOrigemCurriculo("novo")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-all ${origemCurriculo === "novo"
                      ? "bg-white text-black shadow-sm font-semibold"
                      : "text-gray-600 hover:text-black"
                    }`}
                >
                  <i className="ti ti-upload"></i>
                  Enviar Novo
                </button>
              </div>
            </div>

            {/* Opção 1: Selecionar Currículo já Salvo */}
            {origemCurriculo === "salvo" && (
              <div className="space-y-3">
                {curriculos.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-gray-500 space-y-2">
                    <i className="ti ti-file-off text-[32px] text-gray-400"></i>
                    <p className="font-medium text-gray-700">Você ainda não tem nenhum currículo salvo.</p>
                    <p className="text-xs text-gray-400">
                      Clique em "Enviar Novo" acima para subir um currículo diretamente nesta análise.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-[#595859]">
                      Selecione um currículo da sua conta:
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {curriculos.map((curr) => {
                        const selecionado = idCurriculoSelecionado === curr.id_curriculo;
                        return (
                          <div
                            key={curr.id_curriculo}
                            onClick={() => setIdCurriculoSelecionado(curr.id_curriculo)}
                            className={`flex items-center justify-between p-3.5 rounded-lg border cursor-pointer transition-all ${selecionado
                                ? "border-[#1e5e3f] bg-[#f0fdf4] ring-1 ring-[#1e5e3f]"
                                : "border-gray-200 bg-white hover:border-gray-400"
                              }`}
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div
                                className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${selecionado ? "bg-[#1e5e3f] text-white" : "bg-gray-100 text-gray-600"
                                  }`}
                              >
                                <i className="ti ti-file-text text-[18px]"></i>
                              </div>
                              <div className="min-w-0">
                                <p className="font-medium text-sm text-black truncate">{curr.nome_arquivo}</p>
                                <p className="text-xs text-gray-400">
                                  Enviado em {formatarDataUpload(curr.data_upload)}
                                </p>
                              </div>
                            </div>
                            <input
                              type="radio"
                              name="curriculo_salvo"
                              checked={selecionado}
                              onChange={() => setIdCurriculoSelecionado(curr.id_curriculo)}
                              className="text-[#1e5e3f] focus:ring-[#1e5e3f] ml-2"
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Opção 2: Enviar Novo Arquivo */}
            {origemCurriculo === "novo" && (
              <label
                htmlFor="input-arquivo"
                onDragOver={(e) => {
                  e.preventDefault();
                  setArrastando(true);
                }}
                onDragLeave={() => setArrastando(false)}
                onDrop={aoSoltarArquivo}
                className={`flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer transition-colors ${arrastando ? "border-[#1e5e3f] bg-[#f0fdf4]" : "border-[#dfdfe0] hover:border-[#1e5e3f] hover:bg-[#f7f7f7]"
                  }`}
              >
                <input
                  type="file"
                  id="input-arquivo"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={(e) => selecionarArquivo(e.target.files?.[0])}
                />
                {!arquivo && (
                  <>
                    <i className="ti ti-cloud-upload text-[40px] text-[#1e5e3f]"></i>
                    <p className="font-brand text-lg font-semibold text-[#595859]">Clique para selecionar</p>
                    <p className="text-sm text-gray-400">ou arraste e solte seu arquivo aqui (PDF, DOCX até 5MB)</p>
                  </>
                )}
                {arquivo && (
                  <>
                    <i className="ti ti-circle-check text-[40px] text-[#1e5e3f]"></i>
                    <p className="font-brand text-lg font-semibold text-[#595859] break-all px-4">{arquivo.name}</p>
                    <p className="text-sm text-gray-400">{formatarTamanhoArquivo(arquivo.size)}</p>
                    <p className="text-sm text-[#1e5e3f] font-medium">Clique novamente para trocar</p>
                  </>
                )}
              </label>
            )}

            <button
              type="submit"
              disabled={
                !idVagaSelecionada ||
                (origemCurriculo === "salvo" && !idCurriculoSelecionado) ||
                (origemCurriculo === "novo" && !arquivo) ||
                enviando
              }
              className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-6 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60 transition-colors"
            >
              <i className="ti ti-send"></i> {enviando ? "Analisando..." : "Iniciar análise"}
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
