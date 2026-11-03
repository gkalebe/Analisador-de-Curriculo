import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ImportarVagaButton from "./ImportarVagaButton.jsx";

const { criarVaga, visualizarImportacaoVaga } = vi.hoisted(() => ({
  criarVaga: vi.fn(),
  visualizarImportacaoVaga: vi.fn(),
}));

vi.mock("../api/vagasApi.js", () => ({ criarVaga, visualizarImportacaoVaga }));

beforeEach(() => {
  vi.clearAllMocks();
  criarVaga.mockResolvedValue({ id_vaga: "vaga-1", descricao: "Criar serviços de dados." });
  visualizarImportacaoVaga.mockResolvedValue({
    titulo: "Desenvolvedor",
    descricao: "Criar serviços de dados.",
    empresa: "Empresa Exemplo",
    url_origem: "https://www.linkedin.com/jobs/view/1",
  });
});

afterEach(() => {
  cleanup();
});

it("mostra o painel flutuante abaixo do botão e preenche o formulário sem salvar", async () => {
  const onImported = vi.fn();
  render(<ImportarVagaButton email="ana@example.com" onImported={onImported} />);

  fireEvent.click(screen.getByRole("button", { name: "Importar vaga" }));
  const painel = screen.getByRole("region", { name: "Importar vaga do LinkedIn" });
  expect(painel.className).toContain("absolute");
  expect(painel.className).toContain("top-full");
  expect(painel.className).toContain("z-50");
  expect(screen.queryByLabelText(/Descrição da vaga/)).toBeNull();
  expect(screen.queryByLabelText(/Título/)).toBeNull();

  fireEvent.change(screen.getByLabelText("Link da vaga"), {
    target: { value: "https://www.linkedin.com/jobs/view/1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Importar" }));

  await waitFor(() => {
    expect(onImported).toHaveBeenCalledWith(expect.objectContaining({
      descricao: "Criar serviços de dados.",
      empresa: "Empresa Exemplo",
    }));
  });
  expect(criarVaga).not.toHaveBeenCalled();
  expect(screen.queryByRole("region", { name: "Importar vaga do LinkedIn" })).toBeNull();
});

it("mostra a alternativa de preenchimento manual quando a leitura da URL falha", async () => {
  visualizarImportacaoVaga.mockRejectedValue(new Error("página indisponível"));
  const onImported = vi.fn();
  render(<ImportarVagaButton email="ana@example.com" onImported={onImported} />);

  fireEvent.click(screen.getByRole("button", { name: "Importar vaga" }));
  fireEvent.change(screen.getByLabelText("Link da vaga"), {
    target: { value: "https://www.linkedin.com/jobs/view/1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Importar" }));

  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByText(/cole a descrição no formulário abaixo/i)).toBeTruthy();
  expect(screen.queryByLabelText(/Descrição da vaga/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(screen.queryByRole("region", { name: "Importar vaga do LinkedIn" })).toBeNull();
  expect(criarVaga).not.toHaveBeenCalled();
  expect(onImported).not.toHaveBeenCalled();
});

it("salva a vaga importada diretamente quando usado no fluxo de análise", async () => {
  const onImported = vi.fn();
  render(<ImportarVagaButton email="ana@example.com" onImported={onImported} saveOnImport />);

  fireEvent.click(screen.getByRole("button", { name: "Importar vaga" }));
  fireEvent.change(screen.getByLabelText("Link da vaga"), {
    target: { value: "https://www.linkedin.com/jobs/view/1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Importar" }));

  await waitFor(() => {
    expect(criarVaga).toHaveBeenCalledWith(expect.objectContaining({
      email: "ana@example.com",
      descricao: "Criar serviços de dados.",
      empresa: "Empresa Exemplo",
    }));
  });
  expect(onImported).toHaveBeenCalledWith({ id_vaga: "vaga-1", descricao: "Criar serviços de dados." });
});
