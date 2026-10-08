import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PreviewExportarCurriculo from "./PreviewExportarCurriculo.jsx";

const { exportarCurriculo, listarAnalises, listarTemplates } = vi.hoisted(() => ({
  exportarCurriculo: vi.fn(),
  listarAnalises: vi.fn(),
  listarTemplates: vi.fn(),
}));

vi.mock("../api/templateApi.js", () => ({ exportarCurriculo, listarTemplates }));
vi.mock("../api/analiseApi.js", () => ({ listarAnalises }));
vi.mock("../models/usuario.js", () => ({
  lerSessao: () => ({ email: "ana@example.com" }),
}));
vi.mock("../components/Sidebar.jsx", () => ({ default: () => null }));
vi.mock("../components/LimiteDeErro.jsx", () => ({ default: ({ children }) => children }));
vi.mock("../components/VisualizadorPdf.jsx", () => ({
  default: () => <div data-testid="visualizador-pdf">PDF carregado</div>,
}));

beforeEach(() => {
  vi.clearAllMocks();
  listarTemplates.mockResolvedValue({
    templates: [{ id_template: "template-1", nome: "ATS" }],
  });
  listarAnalises.mockResolvedValue({
    analises: [{
      id_analise: "analise-1",
      id_curriculo: "curriculo-1",
      nome_curriculo: "Curriculo da Ana",
      data_analise: "2026-09-01",
      curriculo_possui_edicao: true,
    }],
  });
  exportarCurriculo.mockResolvedValue({ blob: new Blob(["pdf"]) });
});

it("gera a prévia da versão selecionada e descarta a prévia anterior ao trocar de versão", async () => {
  render(
    <MemoryRouter
      initialEntries={["/templates/exportar?template=template-1&curriculo=curriculo-1&versao=original"]}
    >
      <PreviewExportarCurriculo />
    </MemoryRouter>,
  );

  const otimizada = await screen.findByRole("radio", { name: "Otimizada (sugestões aplicadas)" });
  fireEvent.click(screen.getByRole("button", { name: "Pré-visualizar" }));

  await waitFor(() => {
    expect(exportarCurriculo).toHaveBeenLastCalledWith(
      "ana@example.com",
      "curriculo-1",
      "template-1",
      "pdf",
      "original",
    );
  });
  expect(await screen.findByTestId("visualizador-pdf")).toBeTruthy();

  fireEvent.click(otimizada);
  expect(screen.queryByTestId("visualizador-pdf")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Pré-visualizar" }));

  await waitFor(() => {
    expect(exportarCurriculo).toHaveBeenLastCalledWith(
      "ana@example.com",
      "curriculo-1",
      "template-1",
      "pdf",
      "editada",
    );
  });
  expect(await screen.findByTestId("visualizador-pdf")).toBeTruthy();
});
