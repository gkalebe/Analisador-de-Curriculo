export default function ModalConfirmarExclusao({ aberto, excluindo, onConfirmar, onCancelar }) {
  if (!aberto) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl bg-[#06331d] p-6 text-center text-white shadow-2xl">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white/10">
          <i className="ti ti-alert-triangle text-2xl text-amber-400"></i>
        </div>
        <h2 className="font-brand text-xl font-bold">Deletar!</h2>
        <p className="mt-2 text-sm text-white/90">
          Você tem certeza de que deseja <span className="font-semibold text-rose-400">deletar</span>?
        </p>
        <p className="text-xs text-white/60">Essa ação é irreversível.</p>

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={onCancelar}
            disabled={excluindo}
            className="flex-1 rounded-lg border border-white/30 bg-transparent px-4 py-2.5 font-semibold text-white hover:bg-white/10 transition-colors disabled:opacity-50"
          >
            Desistir
          </button>
          <button
            type="button"
            onClick={onConfirmar}
            disabled={excluindo}
            className="flex-1 rounded-lg bg-rose-600 px-4 py-2.5 font-semibold text-white hover:bg-rose-700 transition-colors disabled:opacity-50"
          >
            {excluindo ? <i className="ti ti-loader animate-spin"></i> : "Deletar"}
          </button>
        </div>
      </div>
    </div>
  );
}
