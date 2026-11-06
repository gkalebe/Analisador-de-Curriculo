import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SimulacaoEntrevista from "./SimulacaoEntrevista.jsx";
import { ApiError } from "../api/client.js";

const mocks = vi.hoisted(() => ({
  avaliarSimulacao: vi.fn(),
  excluirSimulacao: vi.fn(),
  iniciarSimulacao: vi.fn(),
  listarSimulacoes: vi.fn(),
  obterSimulacao: vi.fn(),
  repetirSimulacao: vi.fn(),
  obterUsoPlano: vi.fn(),
  listarVagas: vi.fn(),
}));

vi.mock("../api/simuladorApi.js", () => ({
  avaliarSimulacao: mocks.avaliarSimulacao,
  excluirSimulacao: mocks.excluirSimulacao,
  iniciarSimulacao: mocks.iniciarSimulacao,
  listarSimulacoes: mocks.listarSimulacoes,
  obterSimulacao: mocks.obterSimulacao,
  repetirSimulacao: mocks.repetirSimulacao,
}));
vi.mock("../api/assinaturaApi.js", () => ({ obterUsoPlano: mocks.obterUsoPlano }));
vi.mock("../api/vagasApi.js", () => ({ listarVagas: mocks.listarVagas }));
vi.mock("../models/usuario.js", () => ({
  lerSessao: () => ({ email: "ana@example.com", accessToken: "token" }),
}));
vi.mock("../components/Sidebar.jsx", () => ({ default: () => null }));

const RESUMO_PENDENTE = {
  id_simulacao: "sim-pendente",
  id_vaga: "vaga-1",
  vaga_titulo: "Dev Backend",
  data_criacao: "2026-11-05T12:00:00Z",
  status: "pendente",
  legada: false,
  avaliada_em: null,
  nota_final: null,
  total_perguntas: 2,
  total_respondidas: 0,
};
const RESUMO_AVALIADA = {
  ...RESUMO_PENDENTE,
  id_simulacao: "sim-avaliada",
  vaga_titulo: "Analista de Dados",
  status: "avaliada",
  avaliada_em: "2026-11-04T12:00:00Z",
  nota_final: 8.25,
  total_respondidas: 2,
};

const DIMENSAO = { nota: 8, comentario: "Boa dimensão." };
const PERGUNTAS_PENDENTES = [
  { id_pergunta: "p1", tipo: "tecnica", texto: "Como projeta uma API?", resposta: null, feedback: null },
  { id_pergunta: "p2", tipo: "situacional", texto: "E com prazo apertado?", resposta: null, feedback: null },
];
const SIM_PENDENTE = { ...RESUMO_PENDENTE, feedback_geral: null, perguntas: PERGUNTAS_PENDENTES };
const SIM_AVALIADA = {
  ...RESUMO_AVALIADA,
  feedback_geral: "Entrevista sólida no geral.",
  perguntas: PERGUNTAS_PENDENTES.map((p) => ({
    ...p,
    resposta: "Resposta que o candidato deu.",
    feedback: {
      clareza: DIMENSAO,
      objetividade: DIMENSAO,
      coerencia: DIMENSAO,
      alinhamento: DIMENSAO,
      feedback_geral: `Feedback de ${p.id_pergunta}.`,
    },
  })),
};

function renderizar(url = "/analises/simulacao") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <SimulacaoEntrevista />
    </MemoryRouter>,
  );
}

const USO_PRO = {
  uso: { plano: { limite_entrevistas: 5 }, usos: { entrevista_inicio: 2 }, fim_janela: "2026-12-01T00:00:00Z" },
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.listarVagas.mockResolvedValue({ vagas: [{ id_vaga: "vaga-1", titulo: "Dev Backend", area: "TI" }] });
  mocks.listarSimulacoes.mockResolvedValue({
    simulacoes: [RESUMO_PENDENTE, RESUMO_AVALIADA],
    paginacao: { total: 2, limit: 20, offset: 0 },
  });
  mocks.obterUsoPlano.mockResolvedValue(USO_PRO);
  mocks.obterSimulacao.mockImplementation(async (id) => (id === "sim-avaliada" ? SIM_AVALIADA : SIM_PENDENTE));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("lista o histórico com vaga, status e nota, e abre uma entrevista avaliada em somente leitura", async () => {
  renderizar();

  const historico = await screen.findByRole("complementary", { name: "Histórico de entrevistas" });
  expect(within(historico).getByText("Dev Backend")).toBeTruthy();
  expect(within(historico).getByText("Pendente de respostas")).toBeTruthy();
  expect(within(historico).getByText("Nota 8,3/10")).toBeTruthy();

  fireEvent.click(within(historico).getByText("Analista de Dados"));

  expect(await screen.findByText("Entrevista sólida no geral.")).toBeTruthy();
  expect(screen.getByText("Feedback de p1.")).toBeTruthy();
  expect(screen.getByText("Feedback de p2.")).toBeTruthy();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button", { name: "Enviar para avaliação" })).toBeNull();
  expect(screen.getByRole("button", { name: "Repetir entrevista" })).toBeTruthy();
});

it("repetir entrevista cria uma nova simulação pendente sem alterar a antiga", async () => {
  mocks.repetirSimulacao.mockResolvedValue({
    ...SIM_PENDENTE,
    id_simulacao: "sim-nova",
    perguntas: [{ ...PERGUNTAS_PENDENTES[0], id_pergunta: "n1" }],
  });
  renderizar("/analises/simulacao?simulacao=sim-avaliada");

  fireEvent.click(await screen.findByRole("button", { name: "Repetir entrevista" }));

  await waitFor(() => expect(mocks.repetirSimulacao).toHaveBeenCalledWith("sim-avaliada"));
  expect(await screen.findByRole("button", { name: "Enviar para avaliação" })).toBeTruthy();
  // A antiga continua no histórico e a nova aparece junto.
  const historico = screen.getByRole("complementary", { name: "Histórico de entrevistas" });
  expect(within(historico).getByText("Analista de Dados")).toBeTruthy();
  expect(within(historico).getAllByText("Dev Backend").length).toBeGreaterThanOrEqual(2);
  // A tela não recarrega a simulação nova do servidor (já veio na resposta).
  expect(mocks.obterSimulacao).toHaveBeenCalledTimes(1);
});

it("só libera o envio com todas as respostas preenchidas e envia tudo numa chamada", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mocks.avaliarSimulacao.mockResolvedValue(SIM_AVALIADA);
  renderizar("/analises/simulacao?simulacao=sim-pendente");

  const enviar = await screen.findByRole("button", { name: "Enviar para avaliação" });
  expect(enviar.disabled).toBe(true);

  fireEvent.change(screen.getByLabelText("Resposta da pergunta 1"), { target: { value: "Uso FastAPI com camadas." } });
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "curta" } });
  expect(enviar.disabled).toBe(true);

  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "  Priorizo e comunico o risco.  " } });
  expect(enviar.disabled).toBe(false);

  fireEvent.click(enviar);

  await waitFor(() =>
    expect(mocks.avaliarSimulacao).toHaveBeenCalledWith("sim-pendente", {
      p1: "Uso FastAPI com camadas.",
      p2: "Priorizo e comunico o risco.",
    }),
  );
  expect(window.confirm).toHaveBeenCalledTimes(1);
  expect(await screen.findByText("Entrevista sólida no geral.")).toBeTruthy();
  expect(screen.queryByRole("textbox")).toBeNull();
});

it("não envia se o usuário cancelar a confirmação", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(false);
  renderizar("/analises/simulacao?simulacao=sim-pendente");

  fireEvent.change(await screen.findByLabelText("Resposta da pergunta 1"), { target: { value: "Uso FastAPI com camadas." } });
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "Priorizo e comunico o risco." } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar para avaliação" }));

  expect(window.confirm).toHaveBeenCalled();
  expect(mocks.avaliarSimulacao).not.toHaveBeenCalled();
});

it("mostra data de renovação e link para os planos quando a cota de IA acaba", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mocks.avaliarSimulacao.mockRejectedValue(
    new ApiError(429, {
      detail: {
        codigo: "cota_ia_excedida",
        renovacao_em: "2026-12-01T12:00:00+00:00",
        mensagem: "Você atingiu o limite desta operação do seu plano.",
      },
    }),
  );
  renderizar("/analises/simulacao?simulacao=sim-pendente");

  fireEvent.change(await screen.findByLabelText("Resposta da pergunta 1"), { target: { value: "Uso FastAPI com camadas." } });
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "Priorizo e comunico o risco." } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar para avaliação" }));

  const alerta = await screen.findByRole("alert");
  expect(alerta.textContent).toContain("Você atingiu o limite desta operação do seu plano.");
  expect(alerta.textContent).toContain("1 de dezembro de 2026");
  expect(within(alerta).getByRole("link", { name: "Ver planos" }).getAttribute("href")).toBe("/planos");
  // As respostas continuam na tela para o usuário tentar de novo depois.
  expect(screen.getByLabelText("Resposta da pergunta 1").value).toBe("Uso FastAPI com camadas.");
});

it("no plano gratuito convida a conhecer os planos no lugar do botão de iniciar", async () => {
  mocks.obterUsoPlano.mockResolvedValue({ uso: { plano: { limite_entrevistas: 0 }, usos: {} } });
  renderizar();

  const convite = await screen.findByRole("link", { name: /Ver planos/ });
  expect(convite.getAttribute("href")).toBe("/planos");
  expect(screen.queryByRole("button", { name: "Iniciar simulação" })).toBeNull();
  expect(screen.queryByRole("radio")).toBeNull();
});

it("inicia uma nova entrevista para a vaga escolhida", async () => {
  mocks.iniciarSimulacao.mockResolvedValue({ ...SIM_PENDENTE, id_simulacao: "sim-nova" });
  renderizar();

  fireEvent.click(await screen.findByRole("radio"));
  fireEvent.click(screen.getByRole("button", { name: "Iniciar simulação" }));

  await waitFor(() => expect(mocks.iniciarSimulacao).toHaveBeenCalledWith("vaga-1"));
  expect(await screen.findByRole("button", { name: "Enviar para avaliação" })).toBeTruthy();
});

it("exclui uma entrevista do histórico após confirmar, sem mexer nas outras", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mocks.excluirSimulacao.mockResolvedValue(null);
  renderizar();

  const historico = await screen.findByRole("complementary", { name: "Histórico de entrevistas" });
  fireEvent.click(within(historico).getByRole("button", { name: /Excluir entrevista Analista de Dados/ }));

  await waitFor(() => expect(mocks.excluirSimulacao).toHaveBeenCalledWith("sim-avaliada"));
  await waitFor(() => expect(within(historico).queryByText("Analista de Dados")).toBeNull());
  expect(within(historico).getByText("Dev Backend")).toBeTruthy();
});

it("não exclui quando o usuário cancela a confirmação", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(false);
  renderizar();

  const historico = await screen.findByRole("complementary", { name: "Histórico de entrevistas" });
  fireEvent.click(within(historico).getByRole("button", { name: /Excluir entrevista Analista de Dados/ }));

  expect(mocks.excluirSimulacao).not.toHaveBeenCalled();
  expect(within(historico).getByText("Analista de Dados")).toBeTruthy();
});

it("excluir a entrevista aberta fecha o painel e a remove do histórico", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mocks.excluirSimulacao.mockResolvedValue(null);
  renderizar("/analises/simulacao?simulacao=sim-avaliada");

  fireEvent.click(await screen.findByRole("button", { name: "Excluir" }));

  await waitFor(() => expect(mocks.excluirSimulacao).toHaveBeenCalledWith("sim-avaliada"));
  await waitFor(() => expect(screen.queryByText("Entrevista sólida no geral.")).toBeNull());
});

it("clicar em 'Nova entrevista' durante o carregamento cancela o spinner e abre o seletor de vaga", async () => {
  mocks.obterSimulacao.mockImplementation(() => new Promise(() => {}));
  renderizar("/analises/simulacao?simulacao=sim-pendente");

  expect(await screen.findByText("Carregando simulação...")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: /Nova entrevista/ }));

  expect(await screen.findByText("Para qual vaga você quer treinar?")).toBeTruthy();
  expect(screen.queryByText("Carregando simulação...")).toBeNull();
});

it("trocar de entrevista durante a avaliação não sobrescreve a entrevista aberta nem apaga seu rascunho", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  let concluirAvaliacao;
  mocks.avaliarSimulacao.mockImplementation(
    () =>
      new Promise((resolve) => {
        concluirAvaliacao = resolve;
      }),
  );
  renderizar("/analises/simulacao?simulacao=sim-pendente");

  fireEvent.change(await screen.findByLabelText("Resposta da pergunta 1"), { target: { value: "Uso FastAPI com camadas." } });
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "Priorizo e comunico o risco." } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar para avaliação" }));

  await waitFor(() => expect(mocks.avaliarSimulacao).toHaveBeenCalled());
  // Enquanto avalia, o botão Excluir fica desabilitado.
  expect(screen.getByRole("button", { name: "Excluir" }).disabled).toBe(true);

  // Usuário abre outra entrevista do histórico enquanto a IA ainda está respondendo.
  const historico = screen.getByRole("complementary", { name: "Histórico de entrevistas" });
  fireEvent.click(within(historico).getByText("Analista de Dados"));

  expect(await screen.findByText("Entrevista sólida no geral.")).toBeTruthy();

  // Agora a avaliação da primeira termina: a tela continua na entrevista aberta (Analista de Dados)
  // e o histórico reflete a primeira como avaliada.
  concluirAvaliacao({
    ...SIM_AVALIADA,
    id_simulacao: "sim-pendente",
    vaga_titulo: "Dev Backend",
    feedback_geral: "Feedback da primeira entrevista.",
  });

  await waitFor(() => expect(within(historico).queryByText("Pendente de respostas")).toBeNull());
  expect(screen.getByText("Entrevista sólida no geral.")).toBeTruthy();
  expect(screen.queryByText("Feedback da primeira entrevista.")).toBeNull();
});

it("no 409 limpa o rascunho obsoleto e recarrega a entrevista já avaliada", async () => {
  const dados = new Map();
  vi.stubGlobal("localStorage", {
    getItem: (chave) => (dados.has(chave) ? dados.get(chave) : null),
    setItem: (chave, valor) => dados.set(chave, String(valor)),
    removeItem: (chave) => dados.delete(chave),
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mocks.avaliarSimulacao.mockRejectedValue(new ApiError(409, { detail: "Esta simulação já foi avaliada." }));
  mocks.obterSimulacao
    .mockResolvedValueOnce(SIM_PENDENTE)
    .mockResolvedValueOnce({ ...SIM_AVALIADA, id_simulacao: "sim-pendente", vaga_titulo: "Dev Backend" });

  renderizar("/analises/simulacao?simulacao=sim-pendente");

  fireEvent.change(await screen.findByLabelText("Resposta da pergunta 1"), { target: { value: "Uso FastAPI com camadas." } });
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "Priorizo e comunico o risco." } });
  expect(dados.get("simulacao_rascunho_v1:sim-pendente")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Enviar para avaliação" }));

  expect(await screen.findByText("Entrevista sólida no geral.")).toBeTruthy();
  expect(dados.has("simulacao_rascunho_v1:sim-pendente")).toBe(false);
});

it("pagina o histórico com 'Carregar mais' e deduplica itens por id_simulacao", async () => {
  const terceira = { ...RESUMO_AVALIADA, id_simulacao: "sim-3", vaga_titulo: "Engenheiro de Dados" };
  mocks.listarSimulacoes
    .mockResolvedValueOnce({
      simulacoes: [RESUMO_PENDENTE, RESUMO_AVALIADA],
      paginacao: { total: 3, limit: 20, offset: 0 },
    })
    .mockResolvedValueOnce({
      simulacoes: [RESUMO_AVALIADA, terceira],
      paginacao: { total: 3, limit: 20, offset: 2 },
    });

  renderizar();

  const botaoMais = await screen.findByRole("button", { name: "Carregar mais" });
  fireEvent.click(botaoMais);

  await waitFor(() => expect(mocks.listarSimulacoes).toHaveBeenLastCalledWith({ limit: 20, offset: 2 }));
  const historico = screen.getByRole("complementary", { name: "Histórico de entrevistas" });
  expect(within(historico).getByText("Engenheiro de Dados")).toBeTruthy();
  expect(within(historico).getAllByText("Analista de Dados")).toHaveLength(1);
});

it("avisa antes de responder quando a cota de avaliação do ciclo já acabou", async () => {
  mocks.obterUsoPlano.mockResolvedValue({
    uso: {
      plano: { limite_entrevistas: 5 },
      usos: { entrevista_inicio: 2, entrevista_avaliacao: 5 },
      fim_janela: "2026-12-01T12:00:00Z",
    },
  });
  renderizar("/analises/simulacao?simulacao=sim-pendente");

  expect(await screen.findByText(/Você já usou todas as avaliações do seu plano neste ciclo/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 1"), { target: { value: "Uso FastAPI com camadas." } });
  fireEvent.change(screen.getByLabelText("Resposta da pergunta 2"), { target: { value: "Priorizo e comunico o risco." } });
  expect(screen.getByRole("button", { name: "Enviar para avaliação" }).disabled).toBe(true);
});
