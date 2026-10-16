import { useState } from "react";
import { criarVaga, visualizarImportacaoVaga } from "../api/vagasApi.js";
import { ApiError } from "../api/client.js";

export default function ImportarVagaButton({
  email,
  onImported,
  disabled = false,
  saveOnImport = false,
}) {
  const [aberto, setAberto] = useState(false);
  const [url, setUrl] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function importar(evento) {
    evento.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const previa = await visualizarImportacaoVaga(url.trim());
      const vaga = saveOnImport ? await criarVaga({ ...previa, email }) : previa;
      await onImported(vaga);
      setUrl("");
      setAberto(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setErro("Sua sessão expirou ou é inválida. Entre novamente na sua conta e tente importar.");
      } else if (e instanceof ApiError && e.status === 409) {
        setErro(e.message);
      } else if (e instanceof ApiError) {
        setErro(`${e.message} Você pode fechar esta janela e preencher a vaga manualmente.`);
      } else {
        setErro("Não foi possível importar essa vaga. Confira sua conexão e tente novamente.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setAberto((atual) => !atual);
          setErro("");
        }}
        disabled={disabled || enviando}
        aria-expanded={aberto}
        aria-controls="painel-importar-vaga"
        className="inline-flex items-center gap-2 rounded-md border border-[#1e5e3f] px-4 py-2 text-sm font-bold text-[#1e5e3f] hover:bg-[#f0fdf4] disabled:opacity-60"
      >
        <i className="ti ti-brand-linkedin"></i>
        Importar vaga
      </button>

      {aberto && (
        <section
          id="painel-importar-vaga"
          aria-labelledby="titulo-importar-vaga"
          className="absolute right-0 top-full z-50 mt-2 w-[min(28rem,calc(100vw-2rem))] rounded-xl border border-[#d6e4dc] bg-white p-5 shadow-2xl"
        >
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 id="titulo-importar-vaga" className="font-brand text-xl font-bold text-black">
              Importar vaga do LinkedIn
            </h2>
            <button
              type="button"
              onClick={() => setAberto(false)}
              disabled={enviando}
              aria-label="Fechar importador"
              className="rounded p-2 text-gray-500 hover:bg-gray-100 hover:text-black disabled:opacity-60"
            >
              <i className="ti ti-x"></i>
            </button>
          </div>

          <form onSubmit={importar} className="space-y-3">
            <label className="block text-sm font-medium text-[#595859]" htmlFor="url-vaga-importada">
              Link da vaga
            </label>
            <input
              id="url-vaga-importada"
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.linkedin.com/jobs/view/..."
              className="w-full rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
            />
            <p className="text-xs text-gray-500">
              Se o LinkedIn não permitir a leitura automática, feche esta janela e cole a descrição no formulário abaixo.
            </p>
            {erro && <p role="alert" className="text-sm text-red-700">{erro}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setAberto(false)}
                disabled={enviando}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-60"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={enviando || !email}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-2 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
              >
                <i className={enviando ? "ti ti-loader-2 animate-spin" : "ti ti-download"}></i>
                {enviando ? "Importando..." : "Importar"}
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}
