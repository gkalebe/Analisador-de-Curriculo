import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import {
  alterarPlano,
  abrirPortalAssinatura,
  cancelarRenovacao,
  criarCheckout,
  obterPlanos,
  obterUsoPlano,
} from "../api/assinaturaApi.js";
import { ApiError } from "../api/client.js";
import { lerSessao } from "../models/usuario.js";

const ROTULOS_USO = {
  analise_vaga: "Análises de currículo",
  estruturacao_curriculo: "Estruturações de currículo com IA",
  mensagem_chat: "Mensagens do chatbot",
  entrevista_inicio: "Entrevistas iniciadas",
  entrevista_avaliacao: "Entrevistas avaliadas",
};

const METRICAS_PLANO = [
  { chave: "limite_analises", rotulo: "Análises de currículo" },
  { chave: "limite_estruturacoes", rotulo: "Estruturações de currículo com IA" },
  { chave: "limite_mensagens_chat", rotulo: "Mensagens do chatbot" },
  { chave: "limite_entrevistas", rotulo: "Entrevistas simuladas (iniciar e avaliar)" },
  { chave: "limite_curriculos", rotulo: "Currículos guardados" },
];
const ORDEM_PLANOS = { free: 0, pro: 1, max: 2, ultimate: 3 };
const PERFIL_PLANO = {
  free: "Para conhecer a ferramenta",
  pro: "Para quem está buscando emprego ativamente",
  max: "Para transição de carreira e muitas candidaturas",
  ultimate: "Para mentores, consultores e recrutadores",
};
const PLANO_DESTAQUE = "pro";

function formatarCustoPorAnalise(plano) {
  if (!plano.preco_centavos) return "Grátis";
  if (!plano.limite_analises) return "—";
  return `${formatarPreco(plano.preco_centavos / plano.limite_analises)}`;
}

function formatarPreco(centavos) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(centavos / 100);
}

function formatarData(data) {
  if (!data) return "Ainda não iniciada";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "long",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(data));
}

export default function Planos() {
  const [planos, setPlanos] = useState([]);
  const [uso, setUso] = useState(null);
  const [erro, setErro] = useState("");
  const [erroUso, setErroUso] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [acao, setAcao] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [planoParaConfirmar, setPlanoParaConfirmar] = useState(null);
  const [searchParams] = useSearchParams();
  const sessao = lerSessao();

  useEffect(() => {
    Promise.allSettled([
      obterPlanos(),
      sessao?.accessToken ? obterUsoPlano() : Promise.resolve(null),
    ])
      .then(([resultadoCatalogo, resultadoUso]) => {
        if (resultadoCatalogo.status === "rejected") {
          throw resultadoCatalogo.reason;
        }
        setPlanos(resultadoCatalogo.value.planos);
        if (resultadoUso.status === "fulfilled") {
          setUso(resultadoUso.value?.uso ?? null);
        } else {
          setErroUso(
            resultadoUso.reason instanceof ApiError
              ? resultadoUso.reason.message
              : "Não foi possível carregar seu consumo agora.",
          );
        }
      })
      .catch((falha) => setErro(
        falha instanceof ApiError
          ? falha.message
          : "Não foi possível carregar os planos. Tente novamente.",
      ))
      .finally(() => setCarregando(false));
  }, [sessao?.accessToken]);

  useEffect(() => {
    if (searchParams.get("checkout") === "success") {
      setMensagem(
        "Pagamento recebido. Estamos confirmando sua assinatura; o plano será atualizado após a confirmação segura do Stripe.",
      );
    } else if (searchParams.get("checkout") === "cancelled") {
      setMensagem("Checkout cancelado. Nenhuma cobrança foi concluída.");
    }
  }, [searchParams]);

  const planoAtual = uso?.plano.codigo || "free";
  const assinaturaAtiva = ["active", "trialing"].includes(uso?.assinatura_status);
  const assinaturaExistente = ["active", "trialing", "past_due", "unpaid", "incomplete"].includes(uso?.assinatura_status);

  async function executarAcaoPlano(plano, upgradeConfirmado = false) {
    if (
      assinaturaAtiva
      && ORDEM_PLANOS[plano.codigo] > ORDEM_PLANOS[planoAtual]
      && !upgradeConfirmado
    ) {
      setPlanoParaConfirmar(plano);
      return;
    }

    setErro("");
    setMensagem("");
    setAcao(plano.codigo);
    try {
      if (assinaturaAtiva) {
        const resultado = await alterarPlano(plano.codigo);
        setMensagem(resultado.mensagem);
        setUso((await obterUsoPlano()).uso);
      } else if (assinaturaExistente) {
        const portal = await abrirPortalAssinatura();
        window.location.assign(portal.url);
      } else {
        const checkout = await criarCheckout(plano.codigo);
        window.location.assign(checkout.url);
      }
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : "Não foi possível iniciar esta ação.");
    } finally {
      setAcao("");
    }
  }

  async function confirmarUpgrade() {
    const plano = planoParaConfirmar;
    setPlanoParaConfirmar(null);
    if (plano) await executarAcaoPlano(plano, true);
  }

  async function abrirPortal() {
    setErro("");
    setAcao("portal");
    try {
      const portal = await abrirPortalAssinatura();
      window.location.assign(portal.url);
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : "Não foi possível abrir o portal de assinatura.");
      setAcao("");
    }
  }

  async function cancelarPlano() {
    setErro("");
    setMensagem("");
    setAcao("cancelar");
    try {
      const resultado = await cancelarRenovacao();
      setMensagem(resultado.mensagem);
      setUso((await obterUsoPlano()).uso);
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : "Não foi possível cancelar a renovação.");
    } finally {
      setAcao("");
    }
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={sessao?.email} ativo="planos" />
      <main className="flex-1 p-6 space-y-6 md:h-screen md:overflow-y-auto">
        <header>
          <h1 className="font-brand text-[32px] font-bold text-black">Planos e uso</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Compare os limites mensais de análise, currículo, chatbot e entrevista.
          </p>
        </header>

        {erro && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {erro}
          </div>
        )}
        {mensagem && (
          <div role="status" className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-blue-800">
            {mensagem}
          </div>
        )}
        {planoParaConfirmar && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <section
              role="dialog"
              aria-modal="true"
              aria-labelledby="confirmar-upgrade-titulo"
              className="w-full max-w-lg space-y-4 rounded-lg bg-white p-6 shadow-xl"
            >
              <h2 id="confirmar-upgrade-titulo" className="font-brand text-xl font-bold">
                Confirmar upgrade para {planoParaConfirmar.nome}
              </h2>
              <p className="text-sm leading-6 text-gray-700">
                Ao confirmar, o Stripe cobrará agora no cartão cadastrado o valor proporcional do upgrade
                pelo restante deste ciclo. O valor exato será calculado pelo Stripe.
              </p>
              <p className="text-sm text-gray-700">
                Nos próximos ciclos, o plano será renovado por{" "}
                <strong>{formatarPreco(planoParaConfirmar.preco_centavos)} por mês</strong>.
              </p>
              <div className="flex flex-wrap justify-end gap-3">
                <button
                  type="button"
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                  onClick={() => setPlanoParaConfirmar(null)}
                >
                  Voltar
                </button>
                <button
                  type="button"
                  className="rounded-md bg-[#1e5e3f] px-4 py-2 text-sm font-semibold text-white hover:bg-[#174a31] disabled:opacity-50"
                  disabled={Boolean(acao)}
                  onClick={confirmarUpgrade}
                >
                  Confirmar upgrade e pagar
                </button>
              </div>
            </section>
          </div>
        )}
        {carregando ? (
          <p role="status" className="text-gray-600">Carregando planos...</p>
        ) : (
          <>
            <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
              <section
                aria-labelledby="comparacao-planos-titulo"
                className="min-w-0 overflow-hidden rounded-lg border border-[#dfdfe0] bg-white"
              >
                <div className="border-b border-[#dfdfe0] p-5">
                  <h2 id="comparacao-planos-titulo" className="font-brand text-xl font-bold">
                    Compare os planos
                  </h2>
                  <p className="mt-1 text-sm text-gray-600">
                    Limites mensais de cada plano. As cotas renovam a cada ciclo de cobrança e não acumulam.
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table aria-label="Tabela de comparação de planos" className="w-full min-w-[760px] border-collapse text-left text-sm">
                    <thead className="bg-[#f8faf9]">
                      <tr>
                        <th scope="col" className="sticky left-0 z-10 min-w-48 bg-[#f8faf9] px-4 py-3 font-semibold text-gray-700">
                          Recurso
                        </th>
                        {planos.map((plano) => (
                          <th
                            key={plano.codigo}
                            scope="col"
                            className={`min-w-36 px-4 py-3 align-top ${plano.codigo === PLANO_DESTAQUE ? "bg-[#eaf5ef]" : ""}`}
                          >
                            <span className="flex flex-wrap items-center gap-2 font-brand text-base font-bold text-gray-900">
                              {plano.nome}
                              {plano.codigo === PLANO_DESTAQUE && (
                                <span className="rounded-full bg-[#1e5e3f] px-2 py-0.5 font-sans text-[10px] font-semibold uppercase tracking-wide text-white">
                                  Mais escolhido
                                </span>
                              )}
                            </span>
                            <span className="mt-1 block whitespace-nowrap font-bold text-[#1e5e3f]">
                              {formatarPreco(plano.preco_centavos)}
                              <span className="font-normal text-gray-500"> / mês</span>
                            </span>
                            {PERFIL_PLANO[plano.codigo] && (
                              <span className="mt-1 block text-xs font-normal leading-4 text-gray-500">
                                {PERFIL_PLANO[plano.codigo]}
                              </span>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {METRICAS_PLANO.map((metrica) => (
                        <tr key={metrica.chave} className="border-t border-gray-100 even:bg-[#fcfcfc]">
                          <th scope="row" className="sticky left-0 z-10 bg-inherit px-4 py-3 font-medium text-gray-700">
                            {metrica.rotulo}
                          </th>
                          {planos.map((plano) => (
                            <td
                              key={plano.codigo}
                              className={`px-4 py-3 text-gray-700 ${plano.codigo === PLANO_DESTAQUE ? "bg-[#f3faf6]" : ""}`}
                            >
                              {!plano[metrica.chave] ? (
                                <span className="text-gray-400">—</span>
                              ) : metrica.chave === "limite_curriculos" ? (
                                `Até ${plano[metrica.chave]}`
                              ) : (
                                plano[metrica.chave]
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                      <tr className="border-t border-gray-100">
                        <th scope="row" className="sticky left-0 z-10 bg-white px-4 py-3 font-medium text-gray-700">
                          Custo por análise
                        </th>
                        {planos.map((plano) => (
                          <td
                            key={plano.codigo}
                            className={`px-4 py-3 text-gray-500 ${plano.codigo === PLANO_DESTAQUE ? "bg-[#f3faf6]" : ""}`}
                          >
                            {formatarCustoPorAnalise(plano)}
                          </td>
                        ))}
                      </tr>
                      <tr className="border-t border-gray-200">
                        <th scope="row" className="sticky left-0 z-10 bg-white px-4 py-4 font-semibold text-gray-700">
                          Assinatura
                        </th>
                        {planos.map((plano) => {
                          const atual = plano.codigo === planoAtual;
                          const isFree = plano.codigo === "free";
                          const acaoLabel = atual
                            ? "Plano atual"
                            : !sessao?.accessToken
                              ? "Entrar para assinar"
                              : isFree
                                ? assinaturaAtiva && !uso?.cancelamento_agendado
                                  ? "Cancelar renovação"
                                  : "Gratuito"
                                : assinaturaExistente && !assinaturaAtiva
                                  ? "Regularizar pagamento"
                                  : assinaturaAtiva
                                    ? ORDEM_PLANOS[plano.codigo] > ORDEM_PLANOS[planoAtual]
                                      ? "Fazer upgrade"
                                      : "Agendar redução"
                                    : uso?.assinatura_status === "checkout_started"
                                      ? "Retomar pagamento"
                                      : "Assinar";
                          return (
                            <td key={plano.codigo} className="px-4 py-4 align-top">
                              {!sessao?.accessToken && !isFree ? (
                                <Link
                                  className="inline-block rounded-md bg-[#1e5e3f] px-3 py-2 text-center text-sm font-semibold text-white hover:bg-[#174a31]"
                                  to="/login"
                                >
                                  {acaoLabel}
                                </Link>
                              ) : isFree && assinaturaAtiva && !uso?.cancelamento_agendado ? (
                                <button
                                  className="rounded-md border border-[#1e5e3f] px-3 py-2 text-sm font-semibold text-[#1e5e3f] disabled:opacity-50"
                                  disabled={Boolean(acao)}
                                  onClick={cancelarPlano}
                                >
                                  {acao === "cancelar" ? "Cancelando..." : acaoLabel}
                                </button>
                              ) : !isFree && !atual && sessao?.accessToken ? (
                                <button
                                  className="rounded-md bg-[#1e5e3f] px-3 py-2 text-sm font-semibold text-white hover:bg-[#174a31] disabled:cursor-wait disabled:opacity-50"
                                  disabled={Boolean(acao)}
                                  onClick={() => executarAcaoPlano(plano)}
                                >
                                  {acao === plano.codigo ? "Aguarde..." : acaoLabel}
                                </button>
                              ) : (
                                <span className="text-sm text-gray-500">{acaoLabel}</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="border-t border-[#dfdfe0] px-5 py-3 text-xs leading-5 text-gray-500">
                  Upgrades são aplicados após a confirmação do pagamento; reduções entram em vigor no próximo ciclo.
                </p>
              </section>

              <aside
                aria-labelledby="uso-atual-titulo"
                className="rounded-lg border border-[#dfdfe0] bg-white p-5 xl:sticky xl:top-0"
              >
                <h2 id="uso-atual-titulo" className="font-brand text-xl font-bold">
                  Meu uso
                </h2>
                {uso ? (
                  <>
                    <p className="mt-1 text-sm text-gray-600">
                      Plano atual: <strong className="text-gray-900">{uso.plano.nome}</strong>
                    </p>
                    <p className="mt-1 text-xs leading-5 text-gray-500">
                      {uso.fim_janela
                        ? `Renova em ${formatarData(uso.fim_janela)}`
                        : "O período começa após a primeira operação de IA concluída."}
                    </p>
                    {uso.plano_pendente_codigo && (
                      <p className="mt-2 text-sm text-amber-700">
                        Próximo plano agendado:{" "}
                        <strong>
                          {planos.find((plano) => plano.codigo === uso.plano_pendente_codigo)?.nome
                            || uso.plano_pendente_codigo}
                        </strong>
                      </p>
                    )}
                    {uso.cancelamento_agendado && (
                      <p className="mt-2 text-sm text-amber-700">
                        Renovação cancelada. Seu acesso permanece até {formatarData(uso.acesso_ate)}.
                      </p>
                    )}
                    {assinaturaExistente && (
                      <button
                        className="mt-4 rounded-md border border-[#1e5e3f] px-3 py-2 text-sm font-semibold text-[#1e5e3f] disabled:opacity-50"
                        disabled={Boolean(acao)}
                        onClick={abrirPortal}
                      >
                        {acao === "portal" ? "Abrindo..." : "Gerenciar pagamento"}
                      </button>
                    )}
                    <dl className="mt-5 space-y-4">
                      {Object.entries(ROTULOS_USO).map(([tipo, rotulo]) => {
                        const limite = {
                          analise_vaga: uso.plano.limite_analises,
                          estruturacao_curriculo: uso.plano.limite_estruturacoes,
                          mensagem_chat: uso.plano.limite_mensagens_chat,
                          entrevista_inicio: uso.plano.limite_entrevistas,
                          entrevista_avaliacao: uso.plano.limite_entrevistas,
                        }[tipo];
                        const consumido = uso.usos[tipo] || 0;
                        const progresso = limite ? Math.min((consumido / limite) * 100, 100) : 0;

                        return (
                          <div key={tipo}>
                            <div className="flex items-start justify-between gap-3 text-sm">
                              <dt className="text-gray-700">{rotulo}</dt>
                              <dd className="shrink-0 font-semibold text-gray-900">
                                {consumido} / {limite}
                              </dd>
                            </div>
                            {limite > 0 && (
                              <div
                                aria-hidden="true"
                                className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-100"
                              >
                                <div
                                  className="h-full rounded-full bg-[#1e5e3f]"
                                  style={{ width: `${progresso}%` }}
                                />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </dl>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-gray-600">
                    {erroUso || "Entre na sua conta para consultar o consumo do plano."}
                  </p>
                )}
              </aside>
            </div>
            <p className="text-sm leading-6 text-gray-600">
              Salvar, consultar ou editar manualmente um currículo não consome cota de IA. Os créditos de operação
              destinam cerca de 70% do orçamento ponderado de IA para análises; os pesos serão calibrados com custos
              reais dos provedores antes de habilitar a cobrança em produção.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
