import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import { enviarMensagemChat, listarMensagensChat } from "../api/chatApi.js";
import { listarCurriculos } from "../api/curriculoApi.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

export default function ChatBot() {
  const [searchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [curriculosSalvos, setCurriculosSalvos] = useState([]);
  const [idCurriculoSelecionado, setIdCurriculoSelecionado] = useState("");
  const [mensagens, setMensagens] = useState([]);
  const [pergunta, setPergunta] = useState("");
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const fimDaListaRef = useRef(null);

  useEffect(() => {
    if (!emailInicial) return;
    listarCurriculos(emailInicial)
      .then((resposta) => {
        const lista = resposta.curriculos || [];
        setCurriculosSalvos(lista);
        if (lista.length > 0) setIdCurriculoSelecionado(lista[0].id_curriculo);
      })
      .catch(() => setErro("Não foi possível carregar seus currículos salvos."));
  }, [emailInicial]);

  useEffect(() => {
    if (!emailInicial || !idCurriculoSelecionado) {
      setMensagens([]);
      return;
    }
    setCarregandoHistorico(true);
    setErro("");
    listarMensagensChat(idCurriculoSelecionado, emailInicial)
      .then((resposta) => setMensagens(resposta.mensagens || []))
      .catch((e) =>
        setErro(e instanceof ApiError ? e.message : "Não foi possível carregar o histórico da conversa."),
      )
      .finally(() => setCarregandoHistorico(false));
  }, [emailInicial, idCurriculoSelecionado]);

  useEffect(() => {
    fimDaListaRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, enviando]);

  async function aoEnviarMensagem(evento) {
    evento.preventDefault();
    const perguntaNormalizada = pergunta.trim();
    if (!perguntaNormalizada || !idCurriculoSelecionado || enviando) return;

    setErro("");
    setEnviando(true);
    setPergunta("");

    try {
      const resposta = await enviarMensagemChat(idCurriculoSelecionado, emailInicial, perguntaNormalizada);
      setMensagens((atual) => [...atual, resposta.mensagem_usuario, resposta.mensagem_assistente]);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar sua mensagem. Tente novamente.");
      setPergunta(perguntaNormalizada);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900">
      <Sidebar email={emailInicial} ativo="chatbot" />

      <main className="flex-1 p-6 flex flex-col gap-6">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">ChatBOT</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Converse com a IA sobre um currículo salvo e tire suas dúvidas sobre ele.
          </p>
        </div>

        {!emailInicial && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            Entre com seu e-mail cadastrado para usar o chat.
          </div>
        )}

        {emailInicial && curriculosSalvos.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500 space-y-2">
            <i className="ti ti-file-off text-[32px] text-gray-400"></i>
            <p className="font-medium text-gray-700">Você ainda não tem nenhum currículo salvo.</p>
            <p className="text-xs">Envie um currículo para poder conversar com o ChatBOT sobre ele.</p>
          </div>
        )}

        {emailInicial && curriculosSalvos.length > 0 && (
          <div className="flex-1 flex flex-col rounded-xl border-[0.5px] border-black bg-white overflow-hidden">
            <div className="flex items-center gap-3 border-b border-gray-200 px-6 py-4 bg-gray-50">
              <i className="ti ti-file-text text-[20px] text-[#1e5e3f]"></i>
              <select
                value={idCurriculoSelecionado}
                onChange={(e) => setIdCurriculoSelecionado(e.target.value)}
                className="flex-1 rounded border border-[#dfdfe0] px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]"
              >
                {curriculosSalvos.map((curr) => (
                  <option key={curr.id_curriculo} value={curr.id_curriculo}>
                    {curr.nome_arquivo}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-[#f7f7f7]" style={{ minHeight: "50vh" }}>
              {carregandoHistorico && (
                <div className="py-12 text-center text-gray-500 flex flex-col items-center gap-2">
                  <i className="ti ti-loader text-[28px] animate-spin text-[#1e5e3f]"></i>
                  <p className="text-sm">Carregando conversa...</p>
                </div>
              )}

              {!carregandoHistorico && mensagens.length === 0 && (
                <div className="py-12 text-center text-gray-400">
                  <i className="ti ti-robot text-[32px]"></i>
                  <p className="text-sm mt-2">Pergunte algo sobre esse currículo para começar.</p>
                </div>
              )}

              {!carregandoHistorico &&
                mensagens.map((mensagem) => (
                  <div
                    key={mensagem.id_mensagem}
                    className={`flex ${mensagem.autor === "usuario" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                        mensagem.autor === "usuario"
                          ? "bg-[#1e5e3f] text-white rounded-br-sm"
                          : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
                      }`}
                    >
                      {mensagem.conteudo}
                    </div>
                  </div>
                ))}

              {enviando && (
                <div className="flex justify-start">
                  <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-2.5 text-sm text-gray-400">
                    <i className="ti ti-dots animate-pulse"></i> digitando...
                  </div>
                </div>
              )}

              <div ref={fimDaListaRef} />
            </div>

            {erro && <div className="px-6 py-2 text-sm text-red-700 bg-red-50 border-t border-red-200">{erro}</div>}

            <form
              onSubmit={aoEnviarMensagem}
              className="flex items-center gap-3 border-t border-gray-200 px-6 py-4 bg-gray-50"
            >
              <input
                type="text"
                value={pergunta}
                onChange={(e) => setPergunta(e.target.value)}
                placeholder="Digite sua pergunta sobre o currículo..."
                disabled={enviando}
                className="flex-1 rounded-full border border-[#dfdfe0] px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f] disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={enviando || !pergunta.trim()}
                className="flex items-center gap-2 rounded-full bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] disabled:opacity-60 transition-colors"
              >
                <i className="ti ti-send"></i>
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
