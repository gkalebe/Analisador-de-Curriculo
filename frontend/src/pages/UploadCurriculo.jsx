import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { enviarCurriculo } from "../api/curriculoApi.js";
import { formatarTamanhoArquivo, validarArquivoCurriculo } from "../models/curriculo.js";
import { ApiError } from "../api/client.js";

export default function UploadCurriculo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const emailInicial = searchParams.get("email") || "";

  const [emailCampo, setEmailCampo] = useState(emailInicial);
  const [arquivo, setArquivo] = useState(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);

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
    if (!arquivo) return;
    setErro("");
    setEnviando(true);
    try {
      const resposta = await enviarCurriculo(emailInicial, arquivo);
      setResultado(resposta);
      setArquivo(null);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar o currículo. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900">
      <aside className="bg-[#06331d] text-white w-full md:w-64 shrink-0 flex flex-col gap-8 p-6">
        <Link to="/" className="border-b border-[#8e8e8e] pb-6 font-brand text-[28px] text-white no-underline">
          currículo<span className="font-normal">IA</span>
        </Link>

        <nav className="flex flex-col gap-3">
          <a
            href={`/analises/vagas/nova?email=${encodeURIComponent(emailInicial)}`}
            onClick={(e) => {
              e.preventDefault();
              navigate(`/analises/vagas/nova?email=${encodeURIComponent(emailInicial)}`);
            }}
            className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5"
          >
            <i className="ti ti-search"></i> Nova análise
          </a>
          <a href="#" className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5">
            <i className="ti ti-history"></i> Histórico
          </a>
          <span className="flex items-center gap-3 rounded-lg border border-white/30 bg-white/5 px-3 py-3 shadow-inner font-brand text-lg">
            <i className="ti ti-file-text"></i> Currículo
          </span>
          <a href="#" className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5">
            <i className="ti ti-robot"></i> ChatBOT
          </a>
        </nav>

        <div className="mt-auto flex flex-col gap-3">
          {emailInicial && (
            <div className="flex items-center gap-3 rounded-lg px-3 py-3">
              <span className="flex h-[44px] w-[44px] items-center justify-center rounded-full bg-[#1e5e3f] font-brand text-lg">
                {emailInicial[0]?.toUpperCase()}
              </span>
              <div className="leading-tight">
                <p className="font-brand font-semibold">{emailInicial.split("@")[0]}</p>
                <p className="text-sm text-white/80">{emailInicial}</p>
              </div>
            </div>
          )}
          <button
            onClick={() => navigate("/painel")}
            className="flex items-center gap-3 rounded-lg px-3 py-3 font-brand text-lg text-white/90 hover:bg-white/5 text-left"
          >
            <i className="ti ti-arrow-left"></i> Voltar ao painel
          </button>
        </div>
      </aside>

      <main className="flex-1 p-6 space-y-4">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">Enviar currículo</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Faça o upload do seu currículo em PDF ou DOCX para começarmos a análise.
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
        {resultado && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
            Currículo <strong>{resultado.nome_arquivo}</strong> enviado com sucesso.
          </div>
        )}

        {emailInicial && (
          <div className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-6">
            <div className="flex items-center gap-3">
              <i className="ti ti-file-upload text-[28px]"></i>
              <h2 className="font-brand text-[28px] text-black">Arquivo do currículo</h2>
            </div>

            <form onSubmit={aoEnviar} className="space-y-4">
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
                disabled={!arquivo || enviando}
                className="flex items-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
              >
                <i className="ti ti-send"></i> {enviando ? "Enviando..." : "Iniciar análise"}
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
