import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import ModalConfirmarExclusao from "../components/ModalConfirmarExclusao.jsx";
import {
  baixarArquivoCurriculo,
  excluirCurriculo,
  listarBibliotecaCurriculos,
  obterUrlDownloadCurriculo,
} from "../api/curriculoApi.js";
import { formatarDataUpload } from "../models/curriculo.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

const CATEGORIAS = [
  {
    chave: "enviados_por_mim",
    titulo: "Enviados por mim",
    icone: "ti-upload",
    vazio: "Você ainda não enviou nenhum currículo.",
  },
  {
    chave: "gerados_por_ia",
    titulo: "Gerados pela IA",
    icone: "ti-sparkles",
    vazio: "Nenhum currículo otimizado pela IA ainda.",
  },
];

export default function BibliotecaCurriculos() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [biblioteca, setBiblioteca] = useState({ enviados_por_mim: [], gerados_por_ia: [] });
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [baixando, setBaixando] = useState("");
  const [curriculoParaExcluir, setCurriculoParaExcluir] = useState(null);
  const [excluindo, setExcluindo] = useState(false);

  const carregar = useCallback(() => {
    if (!emailInicial) return;
    setCarregando(true);
    setErro("");
    listarBibliotecaCurriculos(emailInicial)
      .then((resposta) =>
        setBiblioteca({
          enviados_por_mim: resposta.enviados_por_mim || [],
          gerados_por_ia: resposta.gerados_por_ia || [],
        })
      )
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        } else {
          setErro("Não foi possível carregar sua biblioteca de currículos.");
        }
      })
      .finally(() => setCarregando(false));
  }, [emailInicial]);

  useEffect(carregar, [carregar]);

  function entrarComEmail(evento) {
    evento.preventDefault();
    setSearchParams({ email: emailCampo });
  }

  async function baixar(item) {
    setErro("");
    setBaixando(item.id_curriculo);
    try {
      const { blob, nomeArquivo } = await baixarArquivoCurriculo(item.id_curriculo, emailInicial);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = nomeArquivo || item.nome_arquivo;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível baixar este currículo.");
    } finally {
      setBaixando("");
    }
  }

  async function confirmarExclusao() {
    if (!curriculoParaExcluir) return;
    setExcluindo(true);
    setErro("");
    try {
      await excluirCurriculo(curriculoParaExcluir.id_curriculo, emailInicial);
      setAviso(`"${curriculoParaExcluir.nome_arquivo}" foi excluído permanentemente da sua biblioteca.`);
      setCurriculoParaExcluir(null);
      carregar();
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível excluir este currículo.");
    } finally {
      setExcluindo(false);
    }
  }

  const total = biblioteca.enviados_por_mim.length + biblioteca.gerados_por_ia.length;

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="biblioteca" />

      <main className="flex-1 p-6 space-y-6 max-w-4xl md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Biblioteca</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Seus currículos enviados e as versões otimizadas pela IA
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

        {aviso && (
          <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-800">
            <i className="ti ti-circle-check mt-0.5 shrink-0"></i>
            <p className="flex-1 text-sm">{aviso}</p>
            <button type="button" onClick={() => setAviso("")} className="shrink-0 text-emerald-700 hover:text-emerald-900">
              <i className="ti ti-x"></i>
            </button>
          </div>
        )}

        {carregando && (
          <div className="rounded-xl border-[0.5px] border-black bg-white p-12 text-center text-gray-500 space-y-3">
            <i className="ti ti-loader animate-spin text-[32px] text-[#1e5e3f]"></i>
            <p className="font-brand font-semibold">Carregando biblioteca...</p>
          </div>
        )}

        {emailInicial && !carregando && total === 0 && (
          <div className="rounded-xl border-[0.5px] border-black bg-white p-12 text-center text-gray-500 space-y-4">
            <i className="ti ti-folder-off text-[42px] text-gray-400"></i>
            <div className="space-y-1">
              <p className="font-brand text-lg font-bold text-gray-800">Sua biblioteca está vazia</p>
              <p className="text-sm text-gray-500">
                Você ainda não enviou nem gerou nenhum currículo. Faça sua primeira análise para começar.
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

        {emailInicial &&
          !carregando &&
          total > 0 &&
          CATEGORIAS.map((categoria) => {
            const itens = biblioteca[categoria.chave];

            return (
              <div
                key={categoria.chave}
                className="rounded-xl border-[0.5px] border-black bg-white shadow-sm overflow-hidden"
              >
                <div className="flex items-center gap-2 border-b border-gray-200 px-6 py-4">
                  <i className={`ti ${categoria.icone} text-lg text-black`}></i>
                  <h2 className="font-brand text-lg font-bold text-black">{categoria.titulo}</h2>
                  <span className="ml-auto rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-600">
                    {itens.length}
                  </span>
                </div>

                {itens.length === 0 ? (
                  <p className="px-6 py-8 text-center text-sm text-gray-500">{categoria.vazio}</p>
                ) : (
                  <ul className="divide-y divide-gray-100">
                    {itens.map((item) => (
                      <li
                        key={item.id_curriculo}
                        className="flex flex-col gap-3 px-6 py-4 hover:bg-gray-50/70 transition-colors sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex min-w-0 items-start gap-3">
                          <i className="ti ti-file-text mt-0.5 text-xl text-gray-700 shrink-0"></i>
                          <div className="min-w-0">
                            <h3 className="font-brand text-base font-semibold text-black truncate">
                              {item.nome_arquivo}
                            </h3>
                            <p className="text-xs text-gray-500">
                              {formatarDataUpload(item.data_upload)}
                              {item.vaga_titulo && ` · ${item.vaga_titulo}`}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {item.possui_arquivo ? (
                            <>
                              <a
                                href={obterUrlDownloadCurriculo(item.id_curriculo, emailInicial)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e5e3f] px-3.5 py-2 text-sm font-bold text-[#1e5e3f] hover:bg-[#1e5e3f]/5 transition-colors"
                              >
                                <i className="ti ti-eye"></i> Visualizar
                              </a>
                              <button
                                type="button"
                                onClick={() => baixar(item)}
                                disabled={baixando === item.id_curriculo}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-[#1e5e3f] px-3.5 py-2 text-sm font-bold text-white hover:bg-[#174a32] transition-colors disabled:opacity-50"
                              >
                                {baixando === item.id_curriculo ? (
                                  <i className="ti ti-loader animate-spin"></i>
                                ) : (
                                  <>
                                    <i className="ti ti-download"></i> Baixar
                                  </>
                                )}
                              </button>
                            </>
                          ) : (
                            <span className="text-xs text-gray-400">Arquivo original indisponível</span>
                          )}

                          <button
                            type="button"
                            onClick={() => setCurriculoParaExcluir(item)}
                            className="p-2 rounded text-gray-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                            title="Excluir currículo"
                          >
                            <i className="ti ti-trash text-lg"></i>
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
      </main>

      <ModalConfirmarExclusao
        aberto={!!curriculoParaExcluir}
        excluindo={excluindo}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setCurriculoParaExcluir(null)}
      />
    </div>
  );
}
