import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Planos from "./Planos.jsx";

const { alterarPlano, obterPlanos, obterUsoPlano } = vi.hoisted(() => ({
  alterarPlano: vi.fn(),
  obterPlanos: vi.fn(),
  obterUsoPlano: vi.fn(),
}));

vi.mock("../api/assinaturaApi.js", () => ({
  alterarPlano,
  abrirPortalAssinatura: vi.fn(),
  cancelarRenovacao: vi.fn(),
  criarCheckout: vi.fn(),
  obterPlanos,
  obterUsoPlano,
}));
vi.mock("../models/usuario.js", () => ({
  lerSessao: () => ({ email: "ana@example.com", accessToken: "test-token" }),
}));
vi.mock("../components/Sidebar.jsx", () => ({ default: () => null }));

beforeEach(() => {
  vi.clearAllMocks();
  obterPlanos.mockResolvedValue({
    planos: [
      {
        codigo: "max",
        nome: "MAX",
        preco_centavos: 5499,
        limite_analises: 28,
        limite_estruturacoes: 5,
        limite_mensagens_chat: 25,
        limite_entrevistas: 15,
        limite_curriculos: 300,
      },
    ],
  });
  obterUsoPlano.mockResolvedValue({
    uso: {
      plano: {
        codigo: "max",
        nome: "MAX",
        limite_analises: 28,
        limite_estruturacoes: 5,
        limite_mensagens_chat: 25,
        limite_entrevistas: 15,
      },
      assinatura_status: "active",
      inicio_janela: "2026-11-01T00:00:00Z",
      fim_janela: "2026-12-01T00:00:00Z",
      usos: { analise_vaga: 2 },
    },
  });
});

it("mostra a comparação tabular ao lado do uso do plano atual", async () => {
  render(
    <MemoryRouter>
      <Planos />
    </MemoryRouter>,
  );

  const tabela = await screen.findByRole("table", { name: "Tabela de comparação de planos" });
  const painelUso = screen.getByRole("complementary", { name: "Meu uso" });
  expect(tabela).toBeTruthy();
  expect(screen.getByRole("columnheader", { name: /MAX/ })).toBeTruthy();
  expect(screen.getByRole("rowheader", { name: "Mensagens do chatbot" })).toBeTruthy();
  expect(screen.getByText("25")).toBeTruthy();
  expect(within(painelUso).getByText("Entrevistas iniciadas")).toBeTruthy();
  expect(within(painelUso).getByText("Entrevistas avaliadas")).toBeTruthy();
  expect(within(painelUso).getAllByText("0 / 15")).toHaveLength(2);
  expect(within(painelUso).queryByText("Respostas de entrevista avaliadas")).toBeNull();
  expect(within(painelUso).getByText("Análises de currículo")).toBeTruthy();
  expect(within(painelUso).getByText("2 / 28")).toBeTruthy();
  expect(tabela.parentElement.parentElement.parentElement.className).toContain("xl:grid-cols-");
});

it("mantém a comparação disponível quando não consegue carregar o uso atual", async () => {
  obterUsoPlano.mockRejectedValue(new Error("Falha ao carregar uso"));

  render(
    <MemoryRouter>
      <Planos />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("table", { name: "Tabela de comparação de planos" })).toBeTruthy();
  expect(screen.getByText("Não foi possível carregar seu consumo agora.")).toBeTruthy();
});

it("exige confirmação antes de cobrar o upgrade e atualiza o plano após sucesso", async () => {
  obterPlanos.mockResolvedValue({
    planos: [
      { codigo: "pro", nome: "PRO", preco_centavos: 1999, limite_analises: 10 },
      { codigo: "max", nome: "MAX", preco_centavos: 5499, limite_analises: 28 },
    ],
  });
  obterUsoPlano
    .mockResolvedValueOnce({
      uso: {
        plano: { codigo: "pro", nome: "PRO", limite_analises: 10 },
        usos: {},
        assinatura_status: "active",
      },
    })
    .mockResolvedValueOnce({
      uso: {
        plano: { codigo: "max", nome: "MAX", limite_analises: 28 },
        usos: {},
        assinatura_status: "active",
      },
    });
  alterarPlano.mockResolvedValue({ mensagem: "Upgrade confirmado e plano atualizado." });

  const { container } = render(
    <MemoryRouter>
      <Planos />
    </MemoryRouter>,
  );

  fireEvent.click(await screen.findByRole("button", { name: "Fazer upgrade" }));
  expect(container.querySelector('[aria-labelledby="uso-atual-titulo"]').textContent).toContain("PRO");

  const dialog = await screen.findByRole("dialog", { name: "Confirmar upgrade para MAX" });
  expect(dialog.textContent).toContain("cobrará agora");
  expect(dialog.textContent).toContain("54,99 por mês");
  expect(alterarPlano).not.toHaveBeenCalled();

  fireEvent.click(within(dialog).getByRole("button", { name: "Voltar" }));
  expect(alterarPlano).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Fazer upgrade" }));
  fireEvent.click(await screen.findByRole("button", { name: "Confirmar upgrade e pagar" }));

  await waitFor(() => expect(alterarPlano).toHaveBeenCalledWith("max"));
  expect((await screen.findByRole("status")).textContent).toContain(
    "Upgrade confirmado e plano atualizado.",
  );
  await waitFor(() => {
    expect(container.querySelector('[aria-labelledby="uso-atual-titulo"]').textContent).toContain("MAX");
  });
});
