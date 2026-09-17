import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Sidebar from "../components/Sidebar.jsx";
import { enviarMensagemChat, listarMensagensChat } from "../api/chatApi.js";
import { listarCurriculos } from "../api/curriculoApi.js";
import { listarVagas } from "../api/vagasApi.js";
import { lerSessao } from "../models/usuario.js";
import { ApiError } from "../api/client.js";

export default function ChatBot() {
  const [searchParams] = useSearchParams();
  const emailInicial = searchParams.get("email") || lerSessao()?.email || "";

  const [curriculosSalvos, setCurriculosSalvos] = useState([]);
  const [idCurriculoSelecionado, setIdCurriculoSelecionado] = useState("");

  const [vagasSalvas, setVagasSalvas] = useState([]);
  const [idVagaSelecionada, setIdVagaSelecionada] = useState("");

  const [mensagens, setMensagens] = useState([]);
  const [pergunta, setPergunta] = useState("");
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const fimDaListaRef = useRef(null);

  // Carrega currículos e vagas do usuário
  useEffect(() => {
    if (!emailInicial) return;

    Promise.all([
      listarCurriculos(emailInicial).catch(() => ({ curriculos: [] })),
      listarVagas(emailInicial).catch(() => ({ vagas: [] })),
    ]).then(([resCurriculos, resVagas]) => {
      const listaCurriculos = resCurriculos.curriculos || [];
      const listaVagas = resVagas.vagas || [];

      setCurriculosSalvos(listaCurriculos);
      setVagasSalvas(listaVagas);

      if (listaCurriculos.length > 0) {
        setIdCurriculoSelecionado(listaCurriculos[0].id_curriculo);
      }
      if (listaVagas.length > 0) {
        // Se houver vaga, pode vir desmarcada ou selecionada
        // Não forçamos seleção de vaga caso o usuário prefira só CV, mas se não tiver CV selecionamos a vaga
        if (listaCurriculos.length === 0) {
          setIdVagaSelecionada(listaVagas[0].id_vaga);
        }
      }
    });
  }, [emailInicial]);

  // Carrega histórico quando o contexto (currículo ou vaga) muda
  useEffect(() => {
    if (!emailInicial || (!idCurriculoSelecionado && !idVagaSelecionada)) {
      setMensagens([]);
      return;
    }

    setCarregandoHistorico(true);
    setErro("");

    listarMensagensChat({
      email: emailInicial,
      idCurriculo: idCurriculoSelecionado || undefined,
      idVaga: idVagaSelecionada || undefined,
    })
      .then((resposta) => setMensagens(resposta.mensagens || []))
      .catch((e) =>
        setErro(e instanceof ApiError ? e.message : "Não foi possível carregar o histórico da conversa."),
      )
      .finally(() => setCarregandoHistorico(false));
  }, [emailInicial, idCurriculoSelecionado, idVagaSelecionada]);

  useEffect(() => {
    fimDaListaRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, enviando]);

  const modoIntegrado = Boolean(idCurriculoSelecionado && idVagaSelecionada);
  const modoApenasCurriculo = Boolean(idCurriculoSelecionado && !idVagaSelecionada);
  const modoApenasVaga = Boolean(!idCurriculoSelecionado && idVagaSelecionada);
  const nenhumSelecionado = !idCurriculoSelecionado && !idVagaSelecionada;

  const sugestoesPerguntas = modoIntegrado
    ? [
        "Qual o meu nível de aderência a essa vaga?",
        "Quais requisitos dessa vaga eu ainda não atendo?",
        "Como adequar minhas experiências para destacar nesta vaga?",
        "Simule 3 perguntas de entrevista técnica para este cargo",
      ]
    : modoApenasVaga
      ? [
          "Quais são os principais requisitos e tecnologias dessa vaga?",
          "O que os recrutadores mais valorizam para este perfil?",
          "Como devo me preparar para a entrevista dessa oportunidade?",
        ]
      : modoApenasCurriculo
        ? [
            "Quais são os principais pontos fortes do meu currículo?",
            "Como posso melhorar o resumo profissional?",
            "Quais melhorias sugeridas para as experiências?",
          ]
        : [];

  async function aoEnviarMensagem(evento, textoDireto = null) {
    if (evento) evento.preventDefault();
    const textoPergunta = (textoDireto || pergunta).trim();
    if (!textoPergunta || nenhumSelecionado || enviando) return;

    setErro("");
    setEnviando(true);
    if (!textoDireto) setPergunta("");

    try {
      const resposta = await enviarMensagemChat({
        email: emailInicial,
        pergunta: textoPergunta,
        idCurriculo: idCurriculoSelecionado || undefined,
        idVaga: idVagaSelecionada || undefined,
      });
      setMensagens((atual) => [...atual, resposta.mensagem_usuario, resposta.mensagem_assistente]);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível enviar sua mensagem. Tente novamente.");
      if (!textoDireto) setPergunta(textoPergunta);
    } finally {
      setEnviando(false);
    }
  }

  const temRecursos = curriculosSalvos.length > 0 || vagasSalvas.length > 0;

  return (
    <div className="min-h-screen md:h-screen flex flex-col md:flex-row bg-[#f3f3f3] text-gray-900 md:overflow-hidden">
      <Sidebar email={emailInicial} ativo="chatbot" />

      <main className="flex-1 p-6 flex flex-col gap-6 md:h-screen md:overflow-y-auto">
        <div>
          <h1 className="font-brand text-[32px] font-bold text-black">ChatBOT</h1>
          <p className="mt-1 text-lg font-semibold text-[#727272]">
            Tire dúvidas com o assistente sobre o seu currículo, sobre vagas cadastradas ou faça uma análise correlacionada entre eles.
          </p>
        </div>

        {!emailInicial && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            Entre com seu e-mail cadastrado para usar o chat.
          </div>
        )}

        {emailInicial && !temRecursos && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500 space-y-3">
            <i className="ti ti-file-off text-[36px] text-gray-400"></i>
            <p className="font-medium text-gray-700 text-lg">Você ainda não possui currículos nem vagas cadastradas.</p>
            <p className="text-sm max-w-md mx-auto text-gray-500">
              Faça o upload de um currículo na tela de Análise ou cadastre uma vaga para começar a conversar e receber orientações personalizadas.
            </p>
          </div>
        )}

        {emailInicial && temRecursos && (
          <div className="flex-1 flex flex-col rounded-xl border-[0.5px] border-black bg-white overflow-hidden shadow-sm">
            {/* Barra superior de seleção de contexto */}
            <div className="border-b border-gray-200 px-6 py-4 bg-gray-50 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3 flex-1 w-full lg:w-auto">
                {/* Seletor de Currículo */}
                <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gray-300 flex-1 min-w-[220px]">
                  <i className="ti ti-file-text text-[18px] text-[#1e5e3f]"></i>
                  <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">Currículo:</span>
                  <select
                    value={idCurriculoSelecionado}
                    onChange={(e) => setIdCurriculoSelecionado(e.target.value)}
                    className="flex-1 text-sm bg-transparent text-gray-800 focus:outline-none cursor-pointer"
                  >
                    <option value="">(Nenhum currículo)</option>
                    {curriculosSalvos.map((curr) => (
                      <option key={curr.id_curriculo} value={curr.id_curriculo}>
                        {curr.nome_arquivo}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Seletor de Vaga */}
                <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gray-300 flex-1 min-w-[220px]">
                  <i className="ti ti-briefcase text-[18px] text-[#1e5e3f]"></i>
                  <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">Vaga:</span>
                  <select
                    value={idVagaSelecionada}
                    onChange={(e) => setIdVagaSelecionada(e.target.value)}
                    className="flex-1 text-sm bg-transparent text-gray-800 focus:outline-none cursor-pointer truncate"
                  >
                    <option value="">(Nenhuma vaga)</option>
                    {vagasSalvas.map((v) => (
                      <option key={v.id_vaga} value={v.id_vaga}>
                        {v.titulo ? `${v.titulo} (${v.area || "Geral"})` : `Vaga - ${v.area || "Sem título"}`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Badge indicativa do Modo de Conversa */}
              <div>
                {modoIntegrado && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-100 text-[#1e5e3f] border border-emerald-300">
                    <i className="ti ti-sparkles"></i> Análise Integrada (Currículo + Vaga)
                  </span>
                )}
                {modoApenasVaga && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-300">
                    <i className="ti ti-briefcase"></i> Foco na Vaga
                  </span>
                )}
                {modoApenasCurriculo && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-300">
                    <i className="ti ti-file-text"></i> Foco no Currículo
                  </span>
                )}
                {nenhumSelecionado && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                    <i className="ti ti-alert-triangle"></i> Selecione um currículo ou vaga
                  </span>
                )}
              </div>
            </div>

            {/* Histórico da Conversa */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-[#f7f7f7]" style={{ minHeight: "50vh" }}>
              {carregandoHistorico && (
                <div className="py-12 text-center text-gray-500 flex flex-col items-center gap-2">
                  <i className="ti ti-loader text-[28px] animate-spin text-[#1e5e3f]"></i>
                  <p className="text-sm">Carregando conversa...</p>
                </div>
              )}

              {nenhumSelecionado && !carregandoHistorico && (
                <div className="py-12 text-center text-gray-500 max-w-md mx-auto space-y-2">
                  <i className="ti ti-hand-click text-[36px] text-[#1e5e3f]"></i>
                  <p className="font-semibold text-gray-700">Selecione o assunto da conversa acima</p>
                  <p className="text-xs text-gray-500">
                    Escolha um currículo para avaliar seu perfil, uma vaga para tirar dúvidas sobre ela, ou selecione ambos para ver como o seu currículo se encaixa na vaga pretendida.
                  </p>
                </div>
              )}

              {!nenhumSelecionado && !carregandoHistorico && mensagens.length === 0 && (
                <div className="py-10 text-center text-gray-400 space-y-3">
                  <i className="ti ti-messages text-[36px] text-gray-300"></i>
                  <p className="text-sm font-medium text-gray-600">
                    {modoIntegrado
                      ? "Pergunte como adequar seu currículo à vaga ou quais pontos fortes você tem para ela."
                      : modoApenasVaga
                        ? "Tire dúvidas sobre os requisitos, perfil desejado ou processo seletivo desta vaga."
                        : "Pergunte algo sobre seu currículo para receber dicas personalizadas."}
                  </p>

                  {/* Pills de perguntas sugeridas de início rápido */}
                  <div className="flex flex-wrap justify-center gap-2 pt-2 max-w-2xl mx-auto">
                    {sugestoesPerguntas.map((sugestao, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => aoEnviarMensagem(null, sugestao)}
                        className="text-xs bg-white border border-gray-300 hover:border-[#1e5e3f] hover:text-[#1e5e3f] text-gray-700 rounded-full px-3 py-1.5 transition-all shadow-2xs hover:shadow-xs text-left"
                      >
                        ✨ {sugestao}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {!carregandoHistorico &&
                mensagens.map((mensagem) => (
                  <div
                    key={mensagem.id_mensagem}
                    className={`flex ${mensagem.autor === "usuario" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-xs ${
                        mensagem.autor === "usuario"
                          ? "bg-[#1e5e3f] text-white rounded-br-sm whitespace-pre-wrap"
                          : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
                      }`}
                    >
                      {mensagem.autor === "usuario" ? (
                        <div>{mensagem.conteudo}</div>
                      ) : (
                        <div className="chat-markdown space-y-2.5">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              h1: ({ node, ...props }) => (
                                <h1 className="text-base font-bold text-gray-900 mt-3 mb-1.5 border-b border-gray-200 pb-1" {...props} />
                              ),
                              h2: ({ node, ...props }) => (
                                <h2 className="text-sm font-bold text-gray-900 mt-3 mb-1" {...props} />
                              ),
                              h3: ({ node, ...props }) => (
                                <h3 className="text-sm font-bold text-gray-900 mt-2.5 mb-1" {...props} />
                              ),
                              p: ({ node, ...props }) => <p className="mb-2 last:mb-0 leading-relaxed text-gray-800" {...props} />,
                              ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2 space-y-1 text-gray-800" {...props} />,
                              ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2 space-y-1 text-gray-800" {...props} />,
                              li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
                              strong: ({ node, ...props }) => <strong className="font-semibold text-gray-900" {...props} />,
                              em: ({ node, ...props }) => <em className="italic text-gray-700" {...props} />,
                              hr: ({ node, ...props }) => <hr className="my-3 border-gray-200" {...props} />,
                              blockquote: ({ node, ...props }) => (
                                <blockquote className="border-l-4 border-[#1e5e3f] pl-3 py-1 my-2 bg-gray-50 text-gray-700 rounded-r text-xs italic" {...props} />
                              ),
                              code: ({ node, inline, children, ...props }) => (
                                <code className="bg-gray-100 text-[#1e5e3f] px-1.5 py-0.5 rounded text-xs font-mono font-medium" {...props}>
                                  {children}
                                </code>
                              ),
                              pre: ({ node, children, ...props }) => (
                                <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs my-2 font-mono" {...props}>
                                  {children}
                                </pre>
                              ),
                            }}
                          >
                            {mensagem.conteudo}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

              {enviando && (
                <div className="flex justify-start">
                  <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-2.5 text-sm text-gray-400 flex items-center gap-2 shadow-xs">
                    <i className="ti ti-loader animate-spin text-[#1e5e3f]"></i> Analisando e formulando resposta...
                  </div>
                </div>
              )}

              <div ref={fimDaListaRef} />
            </div>

            {/* Atalhos de perguntas rápidas contextuais após mensagens */}
            {!nenhumSelecionado && mensagens.length > 0 && (
              <div className="px-6 py-2 bg-gray-50 border-t border-gray-200 flex items-center gap-2 overflow-x-auto text-xs text-gray-600">
                <span className="font-semibold text-gray-500 whitespace-nowrap">Sugestões:</span>
                {sugestoesPerguntas.slice(0, 3).map((sug, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setPergunta(sug)}
                    className="whitespace-nowrap px-2.5 py-1 bg-white hover:bg-gray-100 rounded-full border border-gray-200 text-gray-700 transition-colors"
                  >
                    {sug}
                  </button>
                ))}
              </div>
            )}

            {erro && <div className="px-6 py-2 text-sm text-red-700 bg-red-50 border-t border-red-200">{erro}</div>}

            {/* Formulário de Envio */}
            <form
              onSubmit={(e) => aoEnviarMensagem(e)}
              className="flex items-center gap-3 border-t border-gray-200 px-6 py-4 bg-white"
            >
              <input
                type="text"
                value={pergunta}
                onChange={(e) => setPergunta(e.target.value)}
                placeholder={
                  nenhumSelecionado
                    ? "Selecione um currículo ou vaga acima para iniciar a conversa..."
                    : modoIntegrado
                      ? "Pergunte sobre a correlação entre o seu currículo e esta vaga..."
                      : modoApenasVaga
                        ? "Tire dúvidas sobre os requisitos, perfil ou rotina desta vaga..."
                        : "Digite sua pergunta sobre o currículo..."
                }
                disabled={enviando || nenhumSelecionado}
                className="flex-1 rounded-full border border-[#dfdfe0] px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e5e3f] disabled:opacity-60 disabled:bg-gray-100"
              />
              <button
                type="submit"
                disabled={enviando || !pergunta.trim() || nenhumSelecionado}
                className="flex items-center gap-2 rounded-full bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] disabled:opacity-60 transition-colors shadow-xs"
              >
                <span>Enviar</span>
                <i className="ti ti-send"></i>
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
