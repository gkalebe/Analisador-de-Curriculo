import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { criarAnalise } from "../api/analiseApi.js";
import { listarVagas } from "../api/vagasApi.js";
import { formatarTamanhoArquivo, validarArquivoCurriculo } from "../models/curriculo.js";
import { ApiError } from "../api/client.js";

export default function NovaAnalise() {
  const [searchParams, setSearchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [vagas, setVagas] = useState([]);
  const [idVagaSelecionada, setIdVagaSelecionada] = useState("");
  const [arquivo, setArquivo] = useState(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [avisoIndisponivel, setAvisoIndisponivel] = useState("");
  const [resultado, setResultado] = useState(null);

  useEffect(() => {
    if (!emailInicial) return;
    listarVagas(emailInicial)
      .then((resposta) => setVagas(resposta.vagas))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setErro("Não encontramos um usuário cadastrado com esse e-mail.");
        }
      });
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
    if (!arquivo || !idVagaSelecionada) return;
    setErro("");
    setAvisoIndisponivel("");
    setResultado(null);
    setEnviando(true);
    try {
      const resposta = await criarAnalise(emailInicial, idVagaSelecionada, arquivo);
      setResultado(resposta);
      setArquivo(null);
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

      <main className="flex-1 p-6 space-y-4">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Nova análise</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Escolha uma vaga já cadastrada e envie o currículo para comparar os dois.
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
            {resultado.pontuacao != null && <p>Pontuação: {resultado.pontuacao}</p>}
            {resultado.observacoes && <p>{resultado.observacoes}</p>}
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
              <i className="ti ti-briefcase text-[28px]"></i>
              <h2 className="font-brand text-[28px] text-black">Vaga</h2>
            </div>

            {vagas.length === 0 && (
              <p className="text-sm text-gray-500">
                Você ainda não tem nenhuma vaga salva. Cadastre uma na aba "Cadastrar vaga" antes de rodar uma
                análise.
              </p>
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
                        onChange={(e) => setIdVagaSelecionada(e.target.value)}
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
          </div>
        )}

        {emailInicial && (
          <form
            onSubmit={aoEnviar}
            className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6"
          >
            <div className="flex items-center gap-3">
              <i className="ti ti-file-upload text-[28px]"></i>
              <h2 className="font-brand text-[28px] text-black">Currículo</h2>
            </div>

            <label
              htmlFor="input-arquivo"
              onDragOver={(e) => {
                e.preventDefault();
                setArrastando(true);
              }}
              onDragLeave={() => setArrastando(false)}
              onDrop={aoSoltarArquivo}
              className={`flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-12 text-center cursor-pointer transition-colors ${
                arrastando ? "border-[#1e5e3f] bg-[#f0fdf4]" : "border-[#dfdfe0] hover:border-[#1e5e3f] hover:bg-[#f7f7f7]"
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
                  <p className="text-sm text-gray-400">ou arraste e solte seu arquivo aqui (PDF, DOCX)</p>
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

            <button
              type="submit"
              disabled={!arquivo || !idVagaSelecionada || enviando}
              className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
            >
              <i className="ti ti-send"></i> {enviando ? "Analisando..." : "Analisar"}
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
