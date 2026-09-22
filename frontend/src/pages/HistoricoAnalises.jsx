import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import AnelProgresso, { classificarAderencia } from "../components/AnelProgresso.jsx";
import { listarAnalises } from "../api/analiseApi.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

export default function HistoricoAnalises() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [analises, setAnalises] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!emailInicial) return;
    setCarregando(true);
    setErro("");
    listarAnalises(emailInicial)
      .then((resposta) => setAnalises(resposta.analises || []))
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

  function irParaVisualizar(idAnalise) {
    navigate(`/analises/historico/visualizar?email=${encodeURIComponent(emailInicial)}&id=${idAnalise}`);
  }

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="historico" />

      <main className="flex-1 p-6 space-y-6 max-w-4xl md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Histórico</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Revise e compare seus relatórios anteriores
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

        {emailInicial && (
          <div className="rounded-xl border-[0.5px] border-black bg-white shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 border-b border-gray-200 px-6 py-4">
              <i className="ti ti-briefcase text-lg text-black"></i>
              <h2 className="font-brand text-lg font-bold text-black">Vagas anteriores</h2>
            </div>

            {carregando && (
              <div className="p-12 text-center text-gray-500 space-y-3">
                <i className="ti ti-loader animate-spin text-[32px] text-[#1e5e3f]"></i>
                <p className="font-brand font-semibold">Carregando histórico...</p>
              </div>
            )}

            {!carregando && analises.length === 0 && (
              <div className="p-12 text-center text-gray-500 space-y-4">
                <i className="ti ti-history-off text-[42px] text-gray-400"></i>
                <div className="space-y-1">
                  <p className="font-brand text-lg font-bold text-gray-800">Nenhuma análise salva no histórico</p>
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

            {!carregando && analises.length > 0 && (
              <ul className="divide-y divide-gray-100">
                {analises.map((item) => {
                  const pontuacao = item.pontuacao != null ? Math.round(item.pontuacao) : 0;
                  const { rotulo } = classificarAderencia(pontuacao);

                  return (
                    <li
                      key={item.id_analise}
                      className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-gray-50/70 transition-colors"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <i className="ti ti-file-text text-xl text-gray-700 shrink-0"></i>
                        <h3 className="font-brand text-base font-semibold text-black truncate">
                          {item.titulo_vaga || "Vaga sem título"}
                        </h3>
                      </div>

                      <div className="flex items-center gap-4 shrink-0">
                        <div className="flex items-center gap-2">
                          <AnelProgresso pontuacao={pontuacao} tamanho={36} espessura={3.5} mostrarTexto={false} />
                          <div className="text-sm leading-tight">
                            <p className="font-brand font-bold text-black">{pontuacao}%</p>
                            <p className="text-xs text-gray-500 whitespace-nowrap">{rotulo}</p>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => irParaVisualizar(item.id_analise)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-[#1e5e3f] px-3.5 py-2 text-sm font-bold text-white hover:bg-[#174a32] transition-colors"
                        >
                          Visualizar
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
