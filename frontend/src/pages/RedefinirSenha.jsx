import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { redefinirSenha } from "../api/authApi.js";
import { ApiError } from "../api/client.js";

export default function RedefinirSenha() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [erros, setErros] = useState({});
  const [banner, setBanner] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [sucesso, setSucesso] = useState(false);

  async function aoEnviar(evento) {
    evento.preventDefault();
    setBanner(null);
    const novosErros = {};
    if (novaSenha.length < 8) novosErros.novaSenha = "A senha deve ter no mínimo 8 caracteres.";
    if (novaSenha !== confirmarSenha) novosErros.confirmarSenha = "As senhas não coincidem.";
    setErros(novosErros);
    if (Object.keys(novosErros).length > 0) return;

    setEnviando(true);
    try {
      await redefinirSenha({ token, nova_senha: novaSenha });
      setBanner({ texto: "Senha redefinida com sucesso! Redirecionando para o login...", sucesso: true });
      setSucesso(true);
      setTimeout(() => {
        window.location.href = "/login";
      }, 1800);
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) {
        setBanner({ texto: "Link inválido ou expirado. Solicite a recuperação novamente.", sucesso: false });
      } else if (e instanceof ApiError && e.status === 422) {
        setBanner({ texto: e.message || "Não foi possível redefinir a senha.", sucesso: false });
      } else {
        setBanner({ texto: "Falha de conexão com o servidor. Tente novamente.", sucesso: false });
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-white text-gray-900">
      <div className="bg-[#06331d] text-white w-full md:w-1/2 flex flex-col justify-between gap-10 p-10 md:p-14">
        <Link to="/" className="font-brand text-[28px] text-white no-underline">
          currículo<span className="font-normal">IA</span>
        </Link>

        <div className="space-y-4 max-w-md">
          <h2 className="font-brand text-[32px] font-semibold leading-tight">
            Escolha uma nova senha para continuar.
          </h2>
          <p className="text-white/80 text-lg">
            Defina uma nova senha para sua conta. Esse link só pode ser usado uma vez.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md">
          <div className="flex items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-3 py-3 text-sm">
            <i className="ti ti-lock text-lg"></i> Mínimo de 8 caracteres
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-3 py-3 text-sm">
            <i className="ti ti-clock text-lg"></i> Link expira em 60 minutos
          </div>
        </div>
      </div>

      <div className="w-full md:w-1/2 flex items-center justify-center p-6 md:p-14 bg-[#f3f3f3]">
        <div className="w-full max-w-sm space-y-6">
          <div className="md:hidden font-brand text-[24px] text-[#06331d] mb-2">
            currículo<span className="font-normal">IA</span>
          </div>

          <div>
            <h1 className="font-brand text-[28px] font-bold text-black">Redefinir senha</h1>
            <p className="mt-1 text-[#727272]">Digite sua nova senha abaixo.</p>
          </div>

          {!token && (
            <>
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                <i className="ti ti-alert-circle mt-0.5"></i>
                <span>Link inválido. Solicite a recuperação de senha novamente.</span>
              </div>
              <Link
                to="/usuarios/recuperar-senha"
                className="inline-flex items-center gap-1 text-sm font-medium text-[#1e5e3f] hover:underline"
              >
                <i className="ti ti-arrow-left"></i> Solicitar novo link
              </Link>
            </>
          )}

          {token && (
            <>
              {banner && (
                <div
                  className="rounded-lg px-4 py-3 text-sm"
                  style={{
                    background: banner.sucesso ? "#f0fdf4" : "#fef2f2",
                    color: banner.sucesso ? "#15803d" : "#b91c1c",
                    border: `1px solid ${banner.sucesso ? "#bbf7d0" : "#fecaca"}`,
                  }}
                >
                  {banner.texto}
                </div>
              )}

              {!sucesso && (
                <form onSubmit={aoEnviar} noValidate className="rounded-lg border-[0.5px] border-black bg-white p-6 space-y-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-[#595859]" htmlFor="nova-senha">
                      Nova senha
                    </label>
                    <input
                      type="password"
                      id="nova-senha"
                      required
                      minLength={8}
                      placeholder="Mínimo 8 caracteres"
                      value={novaSenha}
                      onChange={(e) => setNovaSenha(e.target.value)}
                      className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                    />
                    <span className="text-xs text-red-600">{erros.novaSenha}</span>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-[#595859]" htmlFor="confirmar-senha">
                      Confirmar nova senha
                    </label>
                    <input
                      type="password"
                      id="confirmar-senha"
                      required
                      minLength={8}
                      placeholder="Repita a nova senha"
                      value={confirmarSenha}
                      onChange={(e) => setConfirmarSenha(e.target.value)}
                      className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm placeholder-[#8c8c8c] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
                    />
                    <span className="text-xs text-red-600">{erros.confirmarSenha}</span>
                  </div>
                  <button
                    type="submit"
                    disabled={enviando}
                    className="flex w-full items-center justify-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-3 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
                  >
                    <i className="ti ti-key"></i> Redefinir senha
                  </button>
                </form>
              )}

              <Link to="/login" className="inline-flex items-center gap-1 text-sm font-medium text-[#1e5e3f] hover:underline">
                <i className="ti ti-arrow-left"></i> Voltar para o login
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
