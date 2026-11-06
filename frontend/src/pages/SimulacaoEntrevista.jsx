import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import AvisoErro, { formatarDataRenovacao, paraErroTela } from "../components/AvisoErro.jsx";
import {
  avaliarSimulacao,
  excluirSimulacao,
  iniciarSimulacao,
  listarSimulacoes,
  obterSimulacao,
  repetirSimulacao,
} from "../api/simuladorApi.js";
import { obterUsoPlano } from "../api/assinaturaApi.js";
import { listarVagas } from "../api/vagasApi.js";
import { lerSessao } from "../models/usuario.js";
import {
  TAMANHO_MAXIMO_RESPOSTA,
  TAMANHO_MINIMO_RESPOSTA,
  formatarDataHora,
  formatarNota,
  lerRascunho,
  limparRascunho,
  resumirSimulacao,
  respostaValida,
  salvarRascunho,
  temRascunho,
  todasRespondidas,
} from "../models/simulacao.js";

const ITENS_POR_PAGINA = 20;

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

const AVISO_RESPOSTAS_NAO_ENVIADAS =
  "Você tem respostas não enviadas. Elas ficam salvas como rascunho neste navegador, mas ainda não foram avaliadas. Deseja continuar?";

function tituloDaSimulacao(simulacao) {
  return simulacao.vaga_titulo || "Vaga sem título";
}

function BadgeStatus({ simulacao }) {
  if (simulacao.status === "avaliada") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-xs font-bold text-[#1e5e3f]">
        <i className="ti ti-circle-check"></i> Avaliada
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
      <i className="ti ti-pencil"></i> Pendente de respostas
    </span>
  );
}

function ItemHistorico({ simulacao, selecionada, onAbrir, onExcluir, excluindo }) {
  return (
    <li className="relative">
      <button
        type="button"
        onClick={() => onAbrir(simulacao.id_simulacao)}
        aria-current={selecionada ? "true" : undefined}
        className={`w-full rounded-lg border-[0.5px] p-3 pr-10 text-left hover:border-[#1e5e3f] ${
          selecionada ? "border-[#1e5e3f] bg-[#f0fdf4]" : "border-black bg-white"
        }`}
      >
        <p className="truncate font-medium text-gray-900">{tituloDaSimulacao(simulacao)}</p>
        <p className="mt-0.5 text-xs text-gray-500">{formatarDataHora(simulacao.data_criacao)}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <BadgeStatus simulacao={simulacao} />
          {simulacao.status === "avaliada" && simulacao.nota_final != null && (
            <span className="text-xs font-bold text-[#1e5e3f]">Nota {formatarNota(simulacao.nota_final)}/10</span>
          )}
          {simulacao.legada && <span className="text-xs text-gray-400">formato antigo</span>}
        </div>
      </button>
      <button
        type="button"
        onClick={() => onExcluir(simulacao)}
        disabled={excluindo}
        aria-label={`Excluir entrevista ${tituloDaSimulacao(simulacao)}`}
        title="Excluir entrevista"
        className="absolute right-2 top-2 rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
      >
        <i className="ti ti-trash"></i>
      </button>
    </li>
  );
}

function FeedbackPergunta({ pergunta }) {
  const feedback = pergunta.feedback;
  if (!feedback) return null;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {DIMENSOES.map((dimensao) => {
          const dados = feedback[dimensao.chave] || {};
          const nota = dados.nota;
          return (
            <div key={dimensao.chave} className="rounded-lg border border-gray-200 px-3 py-2.5">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-gray-600">{dimensao.rotulo}</span>
                {nota != null && <span className="text-xs font-bold text-[#1e5e3f]">{nota}/10</span>}
              </div>
              {nota != null && (
                <div className="mb-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
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

      {feedback.feedback_geral && (
        <div className="rounded-lg border border-emerald-200 bg-[#f0fdf4] px-4 py-3">
          <p className="mb-1 text-xs font-bold uppercase text-[#1e5e3f]">Feedback desta resposta</p>
          <p className="text-sm text-gray-700">{feedback.feedback_geral}</p>
        </div>
      )}
    </div>
  );
}

function CartaoPergunta({ indice, pergunta, somenteLeitura, texto, onChange, enviando, mostrarErros }) {
  const estilo = ESTILOS_TIPO[pergunta.tipo] || ESTILOS_TIPO.tecnica;
  const tamanho = (texto || "").trim().length;
  const invalida = mostrarErros && !respostaValida(texto);

  return (
    <div className="space-y-3 rounded-lg border-[0.5px] border-black bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-gray-400">Pergunta {indice + 1}</span>
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-bold ${estilo.badge}`}
        >
          <i className={`ti ${estilo.icone}`}></i> {estilo.rotulo}
        </span>
      </div>

      <p className="font-medium text-gray-900">{pergunta.texto}</p>

      {!somenteLeitura && (
        <div className="space-y-1">
          <textarea
            rows={4}
            aria-label={`Resposta da pergunta ${indice + 1}`}
            placeholder="Digite sua resposta como se estivesse na entrevista..."
            value={texto || ""}
            maxLength={TAMANHO_MAXIMO_RESPOSTA}
            onChange={(e) => onChange(pergunta.id_pergunta, e.target.value)}
            disabled={enviando}
            className={`w-full rounded border px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f] disabled:opacity-60 ${
              invalida ? "border-red-400" : "border-[#dfdfe0]"
            }`}
          />
          <div className="flex items-center justify-between text-xs">
            <span className={invalida ? "text-red-700" : "text-gray-500"}>
              {tamanho < TAMANHO_MINIMO_RESPOSTA
                ? `Escreva pelo menos ${TAMANHO_MINIMO_RESPOSTA} caracteres.`
                : "Resposta pronta."}
            </span>
            <span className="text-gray-400">
              {(texto || "").length}/{TAMANHO_MAXIMO_RESPOSTA}
            </span>
          </div>
        </div>
      )}

      {somenteLeitura && (
        <div className="space-y-3 border-t border-gray-100 pt-3">
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
            <p className="mb-1 text-xs font-bold uppercase text-gray-400">Sua resposta</p>
            {pergunta.resposta ? (
              <p className="whitespace-pre-wrap text-sm text-gray-700">{pergunta.resposta}</p>
            ) : (
              <p className="text-sm italic text-gray-500">Não respondida (entrevista no formato antigo).</p>
            )}
          </div>
          <FeedbackPergunta pergunta={pergunta} />
        </div>
      )}
    </div>
  );
}

export default function SimulacaoEntrevista() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = lerSessao()?.email || searchParams.get("email") || "";
  const idVagaParam = searchParams.get("vaga") || "";
  const idSimulacaoParam = searchParams.get("simulacao") || "";

  const [vagas, setVagas] = useState([]);
  const [carregandoVagas, setCarregandoVagas] = useState(false);
  const [idVagaSelecionada, setIdVagaSelecionada] = useState(idVagaParam);

  const [historico, setHistorico] = useState({ itens: [], total: 0 });
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [erroHistorico, setErroHistorico] = useState(null);

  const [uso, setUso] = useState(null);

  const [simulacao, setSimulacao] = useState(null);
  const [carregandoSimulacao, setCarregandoSimulacao] = useState(false);
  const [iniciando, setIniciando] = useState(false);
  const [avaliando, setAvaliando] = useState(false);
  const [excluindoId, setExcluindoId] = useState(null);
  const [erro, setErro] = useState(null);

  const [rascunho, setRascunho] = useState({});
  const [mostrarErros, setMostrarErros] = useState(false);

  // Evita recarregar do servidor a simulação que acabamos de receber (iniciar/repetir/avaliar).
  const simulacaoAtualRef = useRef(null);
  simulacaoAtualRef.current = simulacao;

  const pendente = simulacao?.status === "pendente";
  const rascunhoSujo = Boolean(pendente && temRascunho(rascunho));

  const limiteEntrevistas = uso?.plano?.limite_entrevistas;
  const entrevistasUsadas = uso?.usos?.entrevista_inicio || 0;
  const planoSemEntrevistas = limiteEntrevistas === 0;
  const cotaEsgotada = typeof limiteEntrevistas === "number" && limiteEntrevistas > 0 && entrevistasUsadas >= limiteEntrevistas;
  const iniciosBloqueados = planoSemEntrevistas || cotaEsgotada;

  const atualizarUso = useCallback(() => {
    obterUsoPlano()
      .then((resposta) => setUso(resposta?.uso || null))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!emailInicial) return;
    setCarregandoVagas(true);
    listarVagas(emailInicial)
      .then((resposta) => setVagas(resposta.vagas || []))
      .catch(() => {})
      .finally(() => setCarregandoVagas(false));
    atualizarUso();
  }, [emailInicial, atualizarUso]);

  const carregarHistorico = useCallback((offset = 0) => {
    setCarregandoHistorico(true);
    setErroHistorico(null);
    return listarSimulacoes({ limit: ITENS_POR_PAGINA, offset })
      .then((resposta) =>
        setHistorico((atual) => ({
          itens: offset === 0 ? resposta.simulacoes || [] : [...atual.itens, ...(resposta.simulacoes || [])],
          total: resposta.paginacao?.total ?? 0,
        })),
      )
      .catch((e) => setErroHistorico(paraErroTela(e, "Não foi possível carregar o histórico de entrevistas.")))
      .finally(() => setCarregandoHistorico(false));
  }, []);

  useEffect(() => {
    if (!emailInicial) return;
    carregarHistorico(0);
  }, [emailInicial, carregarHistorico]);

  // Abre a simulação indicada na URL (?simulacao=...) e restaura o rascunho das pendentes.
  useEffect(() => {
    if (!emailInicial) return;
    if (!idSimulacaoParam) {
      setSimulacao(null);
      return;
    }
    if (simulacaoAtualRef.current?.id_simulacao === idSimulacaoParam) return;

    let cancelado = false;
    setCarregandoSimulacao(true);
    setErro(null);
    obterSimulacao(idSimulacaoParam)
      .then((resposta) => {
        if (cancelado) return;
        setSimulacao(resposta);
        setRascunho(resposta.status === "pendente" ? lerRascunho(resposta.id_simulacao) : {});
        setMostrarErros(false);
      })
      .catch((e) => {
        if (cancelado) return;
        setErro(paraErroTela(e, "Não foi possível carregar a simulação."));
        setSimulacao(null);
      })
      .finally(() => {
        if (!cancelado) setCarregandoSimulacao(false);
      });
    return () => {
      cancelado = true;
    };
  }, [emailInicial, idSimulacaoParam]);

  // Avisa antes de fechar/recarregar a aba com respostas ainda não enviadas.
  useEffect(() => {
    if (!rascunhoSujo) return undefined;
    function avisarAntesDeSair(evento) {
      evento.preventDefault();
      evento.returnValue = "";
    }
    window.addEventListener("beforeunload", avisarAntesDeSair);
    return () => window.removeEventListener("beforeunload", avisarAntesDeSair);
  }, [rascunhoSujo]);

  function confirmarSaida() {
    return !rascunhoSujo || window.confirm(AVISO_RESPOSTAS_NAO_ENVIADAS);
  }

  function abrirSimulacao(idSimulacao) {
    if (idSimulacao === simulacao?.id_simulacao) return;
    if (!confirmarSaida()) return;
    setErro(null);
    setSearchParams({ simulacao: idSimulacao });
  }

  function novaEntrevista() {
    if (!confirmarSaida()) return;
    setErro(null);
    setSimulacao(null);
    setRascunho({});
    setSearchParams(idVagaSelecionada ? { vaga: idVagaSelecionada } : {});
  }

  async function excluir(alvo) {
    if (excluindoId) return;
    const eAtual = alvo.id_simulacao === simulacao?.id_simulacao;
    const confirmado = window.confirm(
      `Excluir a entrevista "${tituloDaSimulacao(alvo)}"? Ela some do seu histórico para sempre, com perguntas, respostas e feedback. A entrevista já consumida continua contando na cota do ciclo.`,
    );
    if (!confirmado) return;
    setExcluindoId(alvo.id_simulacao);
    setErro(null);
    try {
      await excluirSimulacao(alvo.id_simulacao);
      limparRascunho(alvo.id_simulacao);
      setHistorico((atual) => ({
        itens: atual.itens.filter((item) => item.id_simulacao !== alvo.id_simulacao),
        total: Math.max(0, atual.total - 1),
      }));
      if (eAtual) {
        simulacaoAtualRef.current = null;
        setSimulacao(null);
        setRascunho({});
        setSearchParams({});
      }
    } catch (e) {
      setErro(paraErroTela(e, "Não foi possível excluir a entrevista."));
    } finally {
      setExcluindoId(null);
    }
  }

  function escolherVaga(idVaga) {
    setIdVagaSelecionada(idVaga);
  }

  // Mostra a simulação recém-criada/avaliada e a reflete no histórico sem recarregar a lista.
  function aplicarSimulacao(resposta, { nova }) {
    const resumo = resumirSimulacao(resposta);
    setSimulacao(resposta);
    simulacaoAtualRef.current = resposta;
    setHistorico((atual) => {
      const existe = atual.itens.some((item) => item.id_simulacao === resumo.id_simulacao);
      return {
        itens: existe
          ? atual.itens.map((item) => (item.id_simulacao === resumo.id_simulacao ? resumo : item))
          : [resumo, ...atual.itens],
        total: existe ? atual.total : atual.total + (nova ? 1 : 0),
      };
    });
  }

  async function criarSimulacao(chamada, mensagemPadrao) {
    if (!confirmarSaida()) return;
    setErro(null);
    setIniciando(true);
    try {
      const resposta = await chamada();
      aplicarSimulacao(resposta, { nova: true });
      setRascunho({});
      setMostrarErros(false);
      setSearchParams({ simulacao: resposta.id_simulacao });
      atualizarUso();
    } catch (e) {
      setErro(paraErroTela(e, mensagemPadrao));
    } finally {
      setIniciando(false);
    }
  }

  function iniciar() {
    // RN-004: bloqueia início da simulação sem vaga definida.
    if (!idVagaSelecionada) {
      setErro({ mensagem: "Selecione uma vaga para iniciar a simulação de entrevista." });
      return;
    }
    return criarSimulacao(
      () => iniciarSimulacao(idVagaSelecionada),
      "Não foi possível iniciar a simulação. Tente novamente.",
    );
  }

  function repetir() {
    return criarSimulacao(
      () => repetirSimulacao(simulacao.id_simulacao),
      "Não foi possível repetir a entrevista. Tente novamente.",
    );
  }

  function alterarResposta(idPergunta, texto) {
    const proximo = { ...rascunho, [idPergunta]: texto };
    setRascunho(proximo);
    salvarRascunho(simulacao.id_simulacao, proximo);
  }

  function limparRespostas() {
    if (!window.confirm("Apagar todas as respostas digitadas? Essa ação não pode ser desfeita.")) return;
    setRascunho({});
    setMostrarErros(false);
    limparRascunho(simulacao.id_simulacao);
  }

  async function enviarParaAvaliacao() {
    if (!todasRespondidas(simulacao.perguntas, rascunho)) {
      setMostrarErros(true);
      setErro({
        mensagem: `Responda todas as perguntas (mínimo de ${TAMANHO_MINIMO_RESPOSTA} caracteres cada) antes de enviar para avaliação.`,
      });
      return;
    }
    const confirmado = window.confirm(
      "Enviar as respostas para avaliação? Isso consome 1 avaliação da sua cota e as respostas não poderão mais ser alteradas. Para treinar de novo, use \"Repetir entrevista\".",
    );
    if (!confirmado) return;

    const respostas = Object.fromEntries(
      simulacao.perguntas.map((p) => [p.id_pergunta, rascunho[p.id_pergunta].trim()]),
    );
    setErro(null);
    setAvaliando(true);
    try {
      const resposta = await avaliarSimulacao(simulacao.id_simulacao, respostas);
      limparRascunho(simulacao.id_simulacao);
      setRascunho({});
      aplicarSimulacao(resposta, { nova: false });
      atualizarUso();
    } catch (e) {
      setErro(paraErroTela(e, "Não foi possível avaliar suas respostas. Tente novamente."));
      if (e?.status === 409) {
        // Já avaliada (outra aba/requisição): recarrega o estado real em vez de manter o formulário.
        obterSimulacao(simulacao.id_simulacao).then((atual) => aplicarSimulacao(atual, { nova: false })).catch(() => {});
      }
    } finally {
      setAvaliando(false);
    }
  }

  const totalPerguntas = simulacao?.perguntas?.length || 0;
  const respostasProntas = simulacao ? simulacao.perguntas.filter((p) => respostaValida(rascunho[p.id_pergunta])).length : 0;
  const renovacaoCota = formatarDataRenovacao(uso?.fim_janela);

  return (
    <div className="flex min-h-screen flex-col bg-[#f3f3f3] text-gray-900 md:h-screen md:flex-row md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="simulacao" />

      <main className="flex-1 space-y-4 p-6 md:h-screen md:overflow-y-auto">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-brand text-[32px] font-bold text-black">Simulação de Entrevista</h1>
            <p className="mt-1 text-lg font-semibold text-[#727272]">
              Responda às perguntas geradas para a vaga, envie tudo de uma vez e receba a avaliação da IA com nota e
              feedback por resposta. Todas as suas entrevistas ficam salvas no histórico.
            </p>
          </div>
          {emailInicial && (
            <button
              type="button"
              onClick={novaEntrevista}
              className="flex items-center gap-2 rounded-md border border-[#1e5e3f] px-4 py-2.5 font-bold text-[#1e5e3f] hover:bg-[#f0fdf4]"
            >
              <i className="ti ti-plus"></i> Nova entrevista
            </button>
          )}
        </div>

        {!emailInicial && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            Entre com seu e-mail cadastrado para simular uma entrevista.
          </div>
        )}

        {emailInicial && typeof limiteEntrevistas === "number" && limiteEntrevistas > 0 && (
          <p className="text-sm text-gray-600">
            Entrevistas deste ciclo: <strong>{entrevistasUsadas}</strong> de <strong>{limiteEntrevistas}</strong>
            {renovacaoCota ? ` (renova em ${renovacaoCota})` : ""}.
          </p>
        )}

        <AvisoErro erro={erro} />

        {emailInicial && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
            <aside aria-label="Histórico de entrevistas" className="space-y-3">
              <h2 className="font-brand text-[20px] text-black">Minhas entrevistas</h2>

              {erroHistorico && <AvisoErro erro={erroHistorico} />}

              {!carregandoHistorico && !erroHistorico && historico.itens.length === 0 && (
                <p className="rounded-lg border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-500">
                  Você ainda não fez nenhuma entrevista simulada.
                </p>
              )}

              <ul className="space-y-2">
                {historico.itens.map((item) => (
                  <ItemHistorico
                    key={item.id_simulacao}
                    simulacao={item}
                    selecionada={item.id_simulacao === simulacao?.id_simulacao}
                    onAbrir={abrirSimulacao}
                    onExcluir={excluir}
                    excluindo={excluindoId === item.id_simulacao}
                  />
                ))}
              </ul>

              {carregandoHistorico && <p className="text-sm text-gray-500">Carregando histórico...</p>}

              {!carregandoHistorico && historico.itens.length < historico.total && (
                <button
                  type="button"
                  onClick={() => carregarHistorico(historico.itens.length)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:border-[#1e5e3f]"
                >
                  Carregar mais
                </button>
              )}
            </aside>

            <section aria-label="Entrevista" className="min-w-0 space-y-4">
              {carregandoSimulacao && (
                <div className="flex flex-col items-center gap-2 py-12 text-center text-gray-500">
                  <i className="ti ti-loader animate-spin text-[28px] text-[#1e5e3f]"></i>
                  <p className="text-sm">Carregando simulação...</p>
                </div>
              )}

              {!simulacao && !carregandoSimulacao && planoSemEntrevistas && (
                <div className="space-y-3 rounded-lg border-[0.5px] border-black bg-white p-6">
                  <div className="flex items-center gap-3">
                    <i className="ti ti-lock text-[28px]"></i>
                    <h2 className="font-brand text-[24px] text-black">Entrevistas simuladas nos planos pagos</h2>
                  </div>
                  <p className="text-sm text-gray-700">
                    O plano gratuito não inclui a simulação de entrevistas. Veja os planos para treinar com perguntas
                    geradas para a sua vaga e receber nota e feedback da IA.
                  </p>
                  <Link
                    to="/planos"
                    className="inline-flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32]"
                  >
                    <i className="ti ti-sparkles"></i> Ver planos
                  </Link>
                </div>
              )}

              {!simulacao && !carregandoSimulacao && !planoSemEntrevistas && (
                <div className="space-y-4 rounded-lg border-[0.5px] border-black bg-white p-6">
                  <div className="flex items-center gap-3">
                    <i className="ti ti-briefcase text-[28px]"></i>
                    <h2 className="font-brand text-[24px] text-black">Para qual vaga você quer treinar?</h2>
                  </div>

                  {carregandoVagas && <p className="text-sm text-gray-500">Carregando vagas...</p>}

                  {!carregandoVagas && vagas.length === 0 && (
                    <div className="space-y-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-gray-500">
                      <i className="ti ti-briefcase-off text-[32px] text-gray-400"></i>
                      <p className="text-sm">
                        Você ainda não tem nenhuma vaga cadastrada. Cadastre uma vaga primeiro para poder simular a
                        entrevista.
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
                      disabled={iniciando || !idVagaSelecionada || iniciosBloqueados}
                      className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                    >
                      <i className={`ti ${iniciando ? "ti-loader animate-spin" : "ti-player-play"}`}></i>
                      {iniciando ? "Gerando perguntas..." : "Iniciar simulação"}
                    </button>
                  )}

                  {cotaEsgotada && (
                    <p className="text-sm text-amber-800">
                      Você usou todas as entrevistas do seu plano neste ciclo
                      {renovacaoCota ? ` (renova em ${renovacaoCota})` : ""}.{" "}
                      <Link to="/planos" className="font-bold underline">
                        Ver planos
                      </Link>
                    </p>
                  )}
                </div>
              )}

              {simulacao && !carregandoSimulacao && (
                <div className="space-y-4">
                  <div className="space-y-3 rounded-lg border-[0.5px] border-black bg-white px-5 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h2 className="font-brand text-[22px] text-black">{tituloDaSimulacao(simulacao)}</h2>
                        <p className="text-xs text-gray-500">
                          Iniciada em {formatarDataHora(simulacao.data_criacao)}
                          {simulacao.avaliada_em ? ` · avaliada em ${formatarDataHora(simulacao.avaliada_em)}` : ""}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <BadgeStatus simulacao={simulacao} />
                        <button
                          type="button"
                          onClick={() => excluir(simulacao)}
                          disabled={Boolean(excluindoId)}
                          className="flex items-center gap-2 rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
                        >
                          <i className={`ti ${excluindoId === simulacao.id_simulacao ? "ti-loader animate-spin" : "ti-trash"}`}></i>
                          Excluir
                        </button>
                        {!planoSemEntrevistas && simulacao.status === "avaliada" && (
                          <button
                            type="button"
                            onClick={repetir}
                            disabled={iniciando || cotaEsgotada}
                            title={cotaEsgotada ? "Você usou todas as entrevistas do seu plano neste ciclo." : undefined}
                            className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-3 py-2 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                          >
                            <i className={`ti ${iniciando ? "ti-loader animate-spin" : "ti-refresh"}`}></i>
                            {iniciando ? "Gerando perguntas..." : "Repetir entrevista"}
                          </button>
                        )}
                      </div>
                    </div>

                    {simulacao.legada && (
                      <p className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-600">
                        Esta entrevista foi feita no formato antigo (avaliação pergunta a pergunta) e está disponível
                        somente para consulta.
                      </p>
                    )}

                    {simulacao.status === "avaliada" && (
                      <div className="flex flex-wrap items-start gap-4 border-t border-gray-100 pt-3">
                        <div className="rounded-lg border border-emerald-200 bg-[#f0fdf4] px-4 py-3 text-center">
                          <p className="text-xs font-bold uppercase text-[#1e5e3f]">Nota final</p>
                          <p className="text-3xl font-bold text-[#1e5e3f]">{formatarNota(simulacao.nota_final)}</p>
                          <p className="text-xs text-gray-500">de 10</p>
                        </div>
                        {simulacao.feedback_geral && (
                          <div className="min-w-[220px] flex-1">
                            <p className="mb-1 text-xs font-bold uppercase text-gray-500">Feedback geral</p>
                            <p className="whitespace-pre-wrap text-sm text-gray-700">{simulacao.feedback_geral}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {pendente && (
                      <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-3">
                        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                          <i className="ti ti-list-check text-[#1e5e3f]"></i>
                          {respostasProntas} de {totalPerguntas} respostas prontas
                        </div>
                        <div className="h-2 w-40 overflow-hidden rounded-full bg-gray-200">
                          <div
                            className="h-full bg-[#1e5e3f] transition-all"
                            style={{ width: totalPerguntas ? `${(respostasProntas / totalPerguntas) * 100}%` : "0%" }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>

                  {simulacao.perguntas.map((pergunta, indice) => (
                    <CartaoPergunta
                      key={pergunta.id_pergunta}
                      indice={indice}
                      pergunta={pergunta}
                      somenteLeitura={!pendente}
                      texto={rascunho[pergunta.id_pergunta]}
                      onChange={alterarResposta}
                      enviando={avaliando}
                      mostrarErros={mostrarErros}
                    />
                  ))}

                  {pendente && (
                    <div className="flex flex-wrap items-center gap-3 rounded-lg border-[0.5px] border-black bg-white px-5 py-4">
                      <button
                        type="button"
                        onClick={enviarParaAvaliacao}
                        disabled={avaliando || respostasProntas < totalPerguntas}
                        className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                      >
                        <i className={`ti ${avaliando ? "ti-loader animate-spin" : "ti-send"}`}></i>
                        {avaliando ? "Avaliando suas respostas..." : "Enviar para avaliação"}
                      </button>
                      <button
                        type="button"
                        onClick={limparRespostas}
                        disabled={avaliando || !temRascunho(rascunho)}
                        className="rounded-md border border-gray-300 px-4 py-3 font-semibold text-gray-700 hover:border-red-400 hover:text-red-700 disabled:opacity-50"
                      >
                        Limpar respostas
                      </button>
                      <p className="text-xs text-gray-500">
                        {avaliando
                          ? "A IA está avaliando todas as respostas de uma vez; pode levar até 1 minuto."
                          : "Suas respostas ficam salvas como rascunho neste navegador até o envio."}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
