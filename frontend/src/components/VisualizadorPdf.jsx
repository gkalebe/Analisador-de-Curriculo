import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist/build/pdf.mjs";
import { baixarArquivoCurriculo } from "../api/curriculoApi.js";
import { ApiError } from "../api/client.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url,
).toString();

const ESCALA_RENDERIZACAO = 1.4;

/**
 * Renderiza o PDF original do currículo em canvases próprios (via pdfjs-dist),
 * em vez de delegar ao visualizador nativo do navegador (iframe/embed) — mantém
 * o conteúdo fiel ao arquivo enviado, dentro do design do site.
 */
export default function VisualizadorPdf({ idCurriculo, email }) {
  const containerRef = useRef(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let cancelado = false;
    let documentoPdf = null;
    let tarefaRenderizacaoAtual = null;

    async function carregarERenderizar() {
      setCarregando(true);
      setErro("");
      if (containerRef.current) containerRef.current.innerHTML = "";

      try {
        const { blob } = await baixarArquivoCurriculo(idCurriculo, email);
        const dados = await blob.arrayBuffer();
        if (cancelado) return;

        documentoPdf = await pdfjsLib.getDocument({ data: dados }).promise;
        if (cancelado) return;

        for (let numeroPagina = 1; numeroPagina <= documentoPdf.numPages; numeroPagina++) {
          if (cancelado) return;
          const pagina = await documentoPdf.getPage(numeroPagina);
          if (cancelado) return;

          const viewport = pagina.getViewport({ scale: ESCALA_RENDERIZACAO });
          const canvas = document.createElement("canvas");
          canvas.className = "block w-full h-auto rounded-lg border border-gray-200 bg-white shadow-sm";
          canvas.width = viewport.width;
          canvas.height = viewport.height;

          const contexto = canvas.getContext("2d");
          tarefaRenderizacaoAtual = pagina.render({ canvasContext: contexto, viewport });
          await tarefaRenderizacaoAtual.promise;
          tarefaRenderizacaoAtual = null;

          if (cancelado) return;

          const paginaWrapper = document.createElement("div");
          paginaWrapper.className = "w-full max-w-2xl mx-auto mb-4";
          paginaWrapper.appendChild(canvas);
          containerRef.current?.appendChild(paginaWrapper);
        }
      } catch (e) {
        // Ao cancelar (fechar a modal), a tarefa de renderização em andamento rejeita
        // de propósito — não é um erro de verdade, então não mostramos nada nesse caso.
        if (!cancelado) {
          setErro(
            e instanceof ApiError
              ? e.message
              : "Não foi possível carregar a pré-visualização do currículo.",
          );
        }
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }

    carregarERenderizar();

    return () => {
      cancelado = true;

      // Guarda as referências desta execução do efeito antes de soltar a UI —
      // em StrictMode (dev) o efeito roda, limpa e roda de novo, então cada
      // limpeza só pode mexer no que ELA criou, nunca no que a próxima já criou.
      const tarefaParaCancelar = tarefaRenderizacaoAtual;
      const documentoParaLiberar = documentoPdf;

      // Destruir o documento do pdfjs (que por sua vez encerra a worker thread e
      // libera os canvases grandes) é um trabalho pesado e síncrono. Fazer isso
      // no mesmo frame em que a modal fecha é o que prendia a tela em preto por
      // um instante — adiamos para depois do navegador pintar o fechamento, para
      // a limpeza pesada acontecer em segundo plano sem travar a transição.
      setTimeout(() => {
        try {
          tarefaParaCancelar?.cancel();
        } catch {
          /* renderização já concluída ou já cancelada */
        }
        try {
          documentoParaLiberar?.destroy();
        } catch {
          /* documento já destruído */
        }
      }, 0);

      if (containerRef.current) containerRef.current.innerHTML = "";
    };
  }, [idCurriculo, email]);

  return (
    <div className="w-full p-4">
      {carregando && (
        <div className="py-12 text-center text-gray-500 flex flex-col items-center gap-2">
          <i className="ti ti-loader text-[28px] animate-spin text-[#1e5e3f]"></i>
          <p className="text-sm">Carregando currículo...</p>
        </div>
      )}
      {erro && !carregando && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{erro}</div>
      )}
      <div ref={containerRef} />
    </div>
  );
}
