import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import ItemPlanoDesenvolvimento, { ListaCertificacoes } from "../components/ItemPlanoDesenvolvimento.jsx";
import { obterPlanoDesenvolvimento } from "../api/analiseApi.js";
import { ApiError } from "../api/client.js";
import { lerSessao } from "../models/usuario.js";

const FILTROS = [
  { chave: "todas", rotulo: "Todas" },
  { chave: "alta", rotulo: "Alta" },
  { chave: "media", rotulo: "Média" },
  { chave: "baixa", rotulo: "Baixa" },
];

function CartaoResumo({ rotulo, valor, icone, destaque = "text-[#1e5e3f]" }) {
  return (
    <div className="rounded-xl border-[0.5px] border-black bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-600">
        <i className={`ti ${icone} text-[18px] ${destaque}`}></i>
        {rotulo}
      </div>
      <p className="mt-1 font-brand text-[28px] font-bold text-black">{valor}</p>
    </div>
  );
}

/** US-015: dashboard do plano de desenvolvimento e trilha de certificações. */
export default function PlanoDesenvolvimento() {
  const [searchParams] = useSearchParams();
  const email = lerSessao()?.email || searchParams.get("email") || "";
  const [plano, setPlano] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [filtro, setFiltro] = useState("todas");

  useEffect(() => {
    obterPlanoDesenvolvimento()
      .then(setPlano)
      .catch((e) => setErro(e instanceof ApiError ? e.message : "Não foi possível carregar o plano."))
      .finally(() => setCarregando(false));
  }, []);

  const itensFiltrados = (plano?.itens || []).filter((item) => filtro === "todas" || item.prioridade === filtro);
  const comCertificacao = (plano?.itens || []).filter((item) => item.certificacoes.length > 0).length;

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={email} ativo="plano" />
      <main className="flex-1 p-6 space-y-6 md:h-screen md:overflow-y-auto">
        <header>
          <h1 className="font-brand text-[32px] font-bold text-black">Plano de desenvolvimento</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Trilhas e certificações para os requisitos que ainda faltam nas vagas que você analisou.
          </p>
        </header>

        {carregando && <p role="status" className="text-gray-600">Carregando plano...</p>}
        {erro && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {erro}
          </div>
        )}

        {plano?.sem_analises && (
          <section className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center space-y-3">
            <i className="ti ti-route text-[40px] text-gray-400"></i>
            <p className="font-brand text-lg font-semibold text-gray-800">Você ainda não tem análises.</p>
            <p className="text-sm text-gray-500">
              Compare seu currículo com uma vaga para gerarmos as trilhas de desenvolvimento.
            </p>
            <Link
              to={`/analises/nova?email=${encodeURIComponent(email)}`}
              className="inline-flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-2 font-semibold text-white hover:bg-[#174a32]"
            >
              <i className="ti ti-search"></i> Fazer uma análise
            </Link>
          </section>
        )}

        {plano && !plano.sem_analises && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <CartaoResumo rotulo="Lacunas abertas" valor={plano.resumo.total} icone="ti-target-arrow" />
              <CartaoResumo rotulo="Prioridade alta" valor={plano.resumo.alta} icone="ti-flame" destaque="text-rose-600" />
              <CartaoResumo rotulo="Com certificação" valor={comCertificacao} icone="ti-certificate" />
              <CartaoResumo rotulo="Vagas analisadas" valor={plano.total_analises} icone="ti-briefcase" />
            </div>

            {plano.sem_lacunas ? (
              <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 space-y-3">
                <p className="flex items-center gap-2 font-semibold text-emerald-900">
                  <i className="ti ti-circle-check text-[22px]"></i>
                  Nenhuma lacuna nas vagas analisadas.
                </p>
                <p className="text-sm text-emerald-900">{plano.mensagem}</p>
              </section>
            ) : (
              <section aria-labelledby="trilhas-titulo" className="space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 id="trilhas-titulo" className="font-brand text-xl font-bold text-black">
                      Trilhas por requisito
                    </h2>
                    <p className="text-sm text-gray-600">{plano.mensagem}</p>
                  </div>
                  <div role="group" aria-label="Filtrar por prioridade" className="flex rounded-lg border border-gray-300 bg-gray-100 p-1 text-sm">
                    {FILTROS.map((opcao) => (
                      <button
                        key={opcao.chave}
                        type="button"
                        aria-pressed={filtro === opcao.chave}
                        onClick={() => setFiltro(opcao.chave)}
                        className={`rounded-md px-3 py-1.5 font-medium ${
                          filtro === opcao.chave ? "bg-white text-black shadow-sm" : "text-gray-600 hover:text-black"
                        }`}
                      >
                        {opcao.rotulo}
                      </button>
                    ))}
                  </div>
                </div>

                {itensFiltrados.length === 0 ? (
                  <p className="text-sm text-gray-500">Nenhum requisito com essa prioridade.</p>
                ) : (
                  <ul className="grid gap-4 xl:grid-cols-2">
                    {itensFiltrados.map((item) => (
                      <ItemPlanoDesenvolvimento
                        key={item.competencia}
                        item={item}
                        rodape={
                          <p className="border-t border-gray-100 pt-2 text-xs text-gray-500">
                            Pedido em {item.frequencia} {item.frequencia === 1 ? "vaga" : "vagas"}:{" "}
                            {item.vagas.map((vaga, idx) => (
                              <span key={vaga.id_analise}>
                                {idx > 0 && ", "}
                                <Link
                                  className="font-semibold text-[#1e5e3f] hover:underline"
                                  to={`/analises/historico/visualizar?email=${encodeURIComponent(email)}&id=${vaga.id_analise}`}
                                >
                                  {vaga.vaga_titulo}
                                </Link>
                              </span>
                            ))}
                          </p>
                        }
                      />
                    ))}
                  </ul>
                )}
              </section>
            )}

            {plano.certificacoes_opcionais.length > 0 && (
              <section className="rounded-xl border-[0.5px] border-black bg-white p-5">
                <ListaCertificacoes
                  certificacoes={plano.certificacoes_opcionais}
                  titulo="Certificações opcionais para se diferenciar"
                />
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
