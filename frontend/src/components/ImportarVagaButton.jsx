import { useState } from "react";
import { importarVaga } from "../api/vagasApi.js";
import { ApiError } from "../api/client.js";

export default function ImportarVagaButton({ email, onImported, disabled = false }) {
  const [aberto, setAberto] = useState(false);
  const [url, setUrl] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function importar(evento) {
    evento.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const vaga = await importarVaga(email, url.trim());
      onImported(vaga);
      setUrl("");
      setAberto(false);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível importar essa vaga.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => { setAberto((atual) => !atual); setErro(""); }}
        disabled={disabled || enviando}
        className="inline-flex items-center gap-2 rounded-md border border-[#1e5e3f] px-4 py-2 text-sm font-bold text-[#1e5e3f] hover:bg-[#f0fdf4] disabled:opacity-60"
      >
        <i className="ti ti-cloud-download"></i>
        Importar vaga
      </button>

      {aberto && (
        <form onSubmit={importar} className="rounded-lg border border-[#d6e4dc] bg-[#f7fcf9] p-4 space-y-3">
          <label className="block text-sm font-medium text-[#595859]" htmlFor="url-vaga-importada">
            URL pública da vaga
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              id="url-vaga-importada"
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://exemplo.com/vaga"
              className="min-w-0 flex-1 rounded border border-[#dfdfe0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
            />
            <button
              type="submit"
              disabled={enviando || !email}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-[#1e5e3f] px-4 py-2 text-sm font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
            >
              <i className={enviando ? "ti ti-loader-2 animate-spin" : "ti ti-download"}></i>
              {enviando ? "Importando..." : "Buscar e salvar"}
            </button>
          </div>
          {erro && <p className="text-sm text-red-700">{erro}</p>}
        </form>
      )}
    </div>
  );
}