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
    <div className="min-h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900">
      <Sidebar email={emailInicial} ativo="analise" />

      <main className="flex-1 p-6 space-y-6">
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

        {resultado && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-4 text-green-800 space-y-2">
            <p className="font-brand text-lg font-semibold">Análise concluída</p>
            {resultado.pontuacao != null && <p className="font-medium">Pontuação: {resultado.pontuacao}%</p>}
            {resultado.observacoes && <p className="text-sm whitespace-pre-wrap">{resultado.observacoes}</p>}
            <Link
              className="inline-block font-semibold text-[#1e5e3f] underline"
              to={`/templates?email=${encodeURIComponent(emailInicial)}`}
            >
              Ver templates ATS para este currículo
            </Link>
          </div>
        )}

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
