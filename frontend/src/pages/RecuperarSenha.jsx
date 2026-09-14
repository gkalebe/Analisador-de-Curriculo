import { useState } from "react";
import { Link } from "react-router-dom";
import { solicitarRecuperacaoSenha } from "../api/authApi.js";
import { ApiError } from "../api/client.js";

const MENSAGEM_RECUPERACAO_SENHA =
  "Se o e-mail informado estiver cadastrado, enviaremos instruções de recuperação de senha.";

export default function RecuperarSenha() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  async function aoEnviar(evento) {
    evento.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      await solicitarRecuperacaoSenha(email.trim());
      setEnviado(true);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Falha de conexão com o servidor. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-white text-gray-900">
      <div className="bg-[#06331d] text-white w-full md:w-1/2 flex flex-col justify-between gap-10 p-10 md:p-14">
        <div className="font-brand text-[28px]">
          currículo<span className="font-normal">IA</span>
        </div>

        <div className="space-y-4 max-w-md">
          <h2 className="font-brand text-[32px] font-semibold leading-tight">
            Esqueceu a senha? A gente resolve rapidinho.
          </h2>
          <p className="text-white/80 text-lg">
            Informe o e-mail cadastrado e enviaremos um link seguro para você criar uma nova senha.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md">
          <div className="flex items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-3 py-3 text-sm">
            <i className="ti ti-mail text-lg"></i> Link enviado por e-mail
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-3 py-3 text-sm">
            <i className="ti ti-clock text-lg"></i> Expira em 60 minutos
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-3 py-3 text-sm">
            <i className="ti ti-shield-check text-lg"></i> Sem expor se o e-mail existe
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-3 py-3 text-sm">
            <i className="ti ti-repeat text-lg"></i> Pode reenviar quando quiser
          </div>
        </div>
      </div>

      <div className="w-full md:w-1/2 flex items-center justify-center p-6 md:p-14 bg-[#f3f3f3]">
        <div className="w-full max-w-sm space-y-6">
          <div className="md:hidden font-brand text-[24px] text-[#06331d] mb-2">
            currículo<span className="font-normal">IA</span>
          </div>

          <div>
            <h1 className="font-brand text-[28px] font-bold text-black">Recuperar senha</h1>
            <p className="mt-1 text-[#727272]">
              Informe seu e-mail cadastrado para receber um link de recuperação de senha.
            </p>
          </div>

          {enviado && (
            <div className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
              <i className="ti ti-circle-check mt-0.5"></i>
              <span>{MENSAGEM_RECUPERACAO_SENHA}</span>
            </div>
          )}
          {enviado && (
            <p className="text-sm text-[#8c8c8c]">
              O link expira em 60 minutos. Se não chegar, você pode solicitar novamente preenchendo o formulário
              abaixo.
            </p>
          )}
          {erro && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
              <i className="ti ti-alert-circle mt-0.5"></i>
              <span>{erro}</span>
            </div>
          )}

          <form onSubmit={aoEnviar} className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-[#595859]" htmlFor="email">
                E-mail
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="seu@email.com"
                className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
              />
            </div>
            <button
              type="submit"
              disabled={enviando}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
            >
              <i className="ti ti-mail-forward"></i>
              {enviado ? "Reenviar link" : "Enviar link de recuperação"}
            </button>
          </form>

          <p className="text-xs text-[#8c8c8c]">
            Por segurança, mostramos sempre a mesma mensagem, mesmo quando o e-mail não está cadastrado.
          </p>

          <Link to="/login" className="inline-flex items-center gap-1 text-sm font-medium text-[#1e5e3f] hover:underline">
            <i className="ti ti-arrow-left"></i> Voltar para o login
          </Link>
        </div>
      </div>
    </div>
  );
}
