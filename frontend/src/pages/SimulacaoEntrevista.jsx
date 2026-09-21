import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { iniciarSimulacao, obterSimulacao, responderPerguntaSimulacao } from "../api/simuladorApi.js";
import { listarVagas } from "../api/vagasApi.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

const ESTILOS_TIPO = {
  comportamental: { rotulo: "Comportamental", badge: "bg-purple-100 text-purple-800 border-purple-300", icone: "ti-users" },
  tecnica: { rotulo: "Técnica", badge: "bg-blue-100 text-blue-800 border-blue-300", icone: "ti-code" },
  situacional: { rotulo: "Situacional", badge: "bg-amber-100 text-amber-800 border-amber-300", icone: "ti-compass" },
};

const DIMENSOES = [
  { chave: "clareza", rotulo: "Clareza" },
  { chave: "objetividade", rotulo: "Objetividade" },
  { chave: "coerencia", rotulo: "Coerência" },
  { chave: "alinhamento", rotulo: "Alinhamento com a vaga" },
];

export default function SimulacaoEntrevista() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";
  const idVagaParam = searchParams.get("vaga") || "";
  const idSimulacaoParam = searchParams.get("simulacao") || "";

  const [vagas, setVagas] = useState([]);
  const [carregandoVagas, setCarregandoVagas] = useState(false);
  const [idVagaSelecionada, setIdVagaSelecionada] = useState(idVagaParam);

  const [simulacao, setSimulacao] = useState(null);
  const [carregandoSimulacao, setCarregandoSimulacao] = useState(false);
  const [iniciando, setIniciando] = useState(false);
  const [erro, setErro] = useState("");

  const [respostasRascunho, setRespostasRascunho] = useState({});
  const [erroPorPergunta, setErroPorPergunta] = useState({});
  const [enviandoPergunta, setEnviandoPergunta] = useState("");

  useEffect(() => {
    if (!emailInicial) return;
    setCarregandoVagas(true);
    listarVagas(emailInicial)
      .then((resposta) => setVagas(resposta.vagas || []))
      .catch(() => {})
      .finally(() => setCarregandoVagas(false));
  }, [emailInicial]);

  useEffect(() => {
    if (!emailInicial || !idSimulacaoParam) return;
    setCarregandoSimulacao(true);
    setErro("");
    obterSimulacao(emailInicial, idSimulacaoParam)
      .then((resposta) => setSimulacao(resposta))
      .catch((e) => {
        setErro(e instanceof ApiError ? e.message : "Não foi possível carregar a simulação.");
        setSimulacao(null);
      })
      .finally(() => setCarregandoSimulacao(false));
  }, [emailInicial, idSimulacaoParam]);

  function escolherVaga(idVaga) {
    setIdVagaSelecionada(idVaga);
    setSearchParams({ email: emailInicial, vaga: idVaga });
  }

  async function iniciar() {
    // RN-004: bloqueia início da simulação sem vaga definida.
    if (!idVagaSelecionada) {
      setErro("Selecione uma vaga para iniciar a simulação de entrevista.");
      return;
    }
    setErro("");
    setIniciando(true);
    try {
      const resposta = await iniciarSimulacao(emailInicial, idVagaSelecionada);
      setSimulacao(resposta);
      setSearchParams({ email: emailInicial, vaga: idVagaSelecionada, simulacao: resposta.id_simulacao });
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível iniciar a simulação. Tente novamente.");
    } finally {
      setIniciando(false);
    }
  }

  function novaSimulacao() {
    setSimulacao(null);
    setRespostasRascunho({});
    setErroPorPergunta({});
    setSearchParams({ email: emailInicial });
  }

  async function enviarResposta(idPergunta) {
    const texto = (respostasRascunho[idPergunta] || "").trim();
    if (!texto) {
      // Critério de aceite: resposta em branco é bloqueada com mensagem.
      setErroPorPergunta((atual) => ({ ...atual, [idPergunta]: "Digite uma resposta antes de enviar." }));
      return;
    }

    setErroPorPergunta((atual) => ({ ...atual, [idPergunta]: "" }));
    setEnviandoPergunta(idPergunta);
    try {
      const resposta = await responderPerguntaSimulacao(emailInicial, simulacao.id_simulacao, idPergunta, texto);
      setSimulacao(resposta);
    } catch (e) {
      setErroPorPergunta((atual) => ({
        ...atual,
        [idPergunta]: e instanceof ApiError ? e.message : "Não foi possível enviar sua resposta. Tente novamente.",
      }));
    } finally {
      setEnviandoPergunta("");
    }
  }

  const totalPerguntas = simulacao?.perguntas?.length || 0;
  const totalRespondidas = simulacao?.perguntas?.filter((p) => p.resposta).length || 0;

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="simulacao" />

      <main className="flex-1 p-6 space-y-4 md:h-screen md:overflow-y-auto">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-brand text-[32px] font-bold text-black">Simulação de Entrevista</h1>
            <p className="mt-1 text-lg font-semibold text-[#727272]">
              Pratique perguntas de entrevista geradas para a vaga escolhida e receba feedback da IA a cada resposta.
            </p>
          </div>
          {simulacao && (
            <button
              type="button"
              onClick={novaSimulacao}
              className="flex items-center gap-2 rounded-md border border-[#1e5e3f] px-4 py-2.5 font-bold text-[#1e5e3f] hover:bg-[#f0fdf4]"
            >
              <i className="ti ti-refresh"></i> Nova simulação
            </button>
          )}
        </div>

        {!emailInicial && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            Entre com seu e-mail cadastrado para simular uma entrevista.
          </div>
        )}

        {erro && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">{erro}</div>}

        {emailInicial && !simulacao && !carregandoSimulacao && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
            <div className="flex items-center gap-3">
              <i className="ti ti-briefcase text-[28px]"></i>
              <h2 className="font-brand text-[24px] text-black">1. Para qual vaga você quer treinar?</h2>
            </div>

            {carregandoVagas && <p className="text-sm text-gray-500">Carregando vagas...</p>}

            {!carregandoVagas && vagas.length === 0 && (
              <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-gray-500 space-y-2">
                <i className="ti ti-briefcase-off text-[32px] text-gray-400"></i>
                <p className="text-sm">
                  Você ainda não tem nenhuma vaga cadastrada. Cadastre uma vaga primeiro para poder simular a entrevista.
                </p>
              </div>
            )}

            {vagas.length > 0 && (
              <ul className="space-y-2">
                {vagas.map((vaga) => (
                  <li key={vaga.id_vaga}>
                    <label
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border-[0.5px] p-4 hover:border-[#1e5e3f] ${
                        idVagaSelecionada === vaga.id_vaga ? "border-[#1e5e3f] bg-[#f0fdf4]" : "border-black"
                      }`}
                    >
                      <input
                        type="radio"
                        name="vaga"
                        value={vaga.id_vaga}
                        checked={idVagaSelecionada === vaga.id_vaga}
                        onChange={() => escolherVaga(vaga.id_vaga)}
                        className="mt-1"
                      />
                      <div>
                        <p className="font-medium">{vaga.titulo || "(Sem título)"}</p>
                        <p className="text-sm text-gray-500">{vaga.area || "Área não informada"}</p>
                      </div>
                    </label>
                  </li>
                ))}
              </ul>
            )}

            {vagas.length > 0 && (
              <button
                type="button"
                onClick={iniciar}
                disabled={iniciando || !idVagaSelecionada}
                className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
              >
                <i className={`ti ${iniciando ? "ti-loader animate-spin" : "ti-player-play"}`}></i>
                {iniciando ? "Gerando perguntas..." : "Iniciar simulação"}
              </button>
            )}
          </div>
        )}

        {carregandoSimulacao && (
          <div className="py-12 text-center text-gray-500 flex flex-col items-center gap-2">
            <i className="ti ti-loader text-[28px] animate-spin text-[#1e5e3f]"></i>
            <p className="text-sm">Carregando simulação...</p>
          </div>
        )}

        {simulacao && !carregandoSimulacao && (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border-[0.5px] border-black bg-white px-5 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <i className="ti ti-list-check text-[#1e5e3f]"></i>
                {totalRespondidas} de {totalPerguntas} perguntas respondidas
              </div>
              <div className="h-2 w-40 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className="h-full bg-[#1e5e3f] transition-all"
                  style={{ width: totalPerguntas ? `${(totalRespondidas / totalPerguntas) * 100}%` : "0%" }}
                ></div>
              </div>
            </div>

            {simulacao.perguntas.map((pergunta, idx) => {
              const estilo = ESTILOS_TIPO[pergunta.tipo] || ESTILOS_TIPO.tecnica;
              const respondida = Boolean(pergunta.resposta);
              const enviando = enviandoPergunta === pergunta.id_pergunta;

              return (
                <div key={pergunta.id_pergunta} className="rounded-lg border-[0.5px] border-black bg-white p-5 space-y-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold text-gray-400">Pergunta {idx + 1}</span>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${estilo.badge}`}>
                      <i className={`ti ${estilo.icone}`}></i> {estilo.rotulo}
                    </span>
                    {respondida && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-[#1e5e3f] border border-emerald-300">
                        <i className="ti ti-check"></i> Respondida
                      </span>
                    )}
                  </div>

                  <p className="font-medium text-gray-900">{pergunta.texto}</p>

                  {!respondida && (
                    <div className="space-y-2">
                      <textarea
                        rows={3}
                        placeholder="Digite sua resposta como se estivesse na entrevista..."
                        value={respostasRascunho[pergunta.id_pergunta] || ""}
                        onChange={(e) =>
                          setRespostasRascunho((atual) => ({ ...atual, [pergunta.id_pergunta]: e.target.value }))
                        }
                        disabled={enviando}
                        className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f] disabled:opacity-60"
                      />
                      {erroPorPergunta[pergunta.id_pergunta] && (
                        <p className="text-sm text-red-700">{erroPorPergunta[pergunta.id_pergunta]}</p>
                      )}
                      <button
                        type="button"
                        onClick={() => enviarResposta(pergunta.id_pergunta)}
                        disabled={enviando}
                        className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-2 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                      >
                        <i className={`ti ${enviando ? "ti-loader animate-spin" : "ti-send"}`}></i>
                        {enviando ? "Avaliando resposta..." : "Enviar resposta"}
                      </button>
                    </div>
                  )}

                  {respondida && (
                    <div className="space-y-3 border-t border-gray-100 pt-3">
                      <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Sua resposta</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{pergunta.resposta}</p>
                      </div>

                      {pergunta.feedback && (
                        <div className="space-y-3">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {DIMENSOES.map((dimensao) => {
                              const dados = pergunta.feedback[dimensao.chave] || {};
                              const nota = dados.nota;
                              return (
                                <div key={dimensao.chave} className="rounded-lg border border-gray-200 px-3 py-2.5">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs font-bold text-gray-600 uppercase">{dimensao.rotulo}</span>
                                    {nota != null && (
                                      <span className="text-xs font-bold text-[#1e5e3f]">{nota}/10</span>
                                    )}
                                  </div>
                                  {nota != null && (
                                    <div className="h-1.5 w-full rounded-full bg-gray-200 overflow-hidden mb-1.5">
                                      <div
                                        className="h-full bg-[#1e5e3f]"
                                        style={{ width: `${Math.min(Math.max(nota, 0), 10) * 10}%` }}
                                      ></div>
                                    </div>
                                  )}
                                  <p className="text-xs text-gray-600">{dados.comentario}</p>
                                </div>
                              );
                            })}
                          </div>

                          {pergunta.feedback.feedback_geral && (
                            <div className="rounded-lg bg-[#f0fdf4] border border-emerald-200 px-4 py-3">
                              <p className="text-xs font-bold text-[#1e5e3f] uppercase mb-1">Feedback geral</p>
                              <p className="text-sm text-gray-700">{pergunta.feedback.feedback_geral}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
