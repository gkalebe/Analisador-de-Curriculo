import { beforeEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RecomendacoesCompetencias from "./RecomendacoesCompetencias.jsx";

const { obterRecomendacoesCompetencias } = vi.hoisted(() => ({ obterRecomendacoesCompetencias: vi.fn() }));
vi.mock("../api/analiseApi.js", () => ({ obterRecomendacoesCompetencias }));

beforeEach(() => vi.clearAllMocks());

it("mostra cada competência em lacuna com suas orientações", async () => {
  obterRecomendacoesCompetencias.mockResolvedValue({
    id_analise: "a1",
    sem_lacunas: false,
    recomendacoes: [
      {
        competencia: "Docker",
        tipo: "obrigatorio",
        status: "parcial",
        orientacoes: ["Use o termo Docker no bullet de deploy."],
        onde_evidenciar: "experiencia_profissional",
        origem: "ia",
      },
      {
        competencia: "Kubernetes",
        tipo: "desejavel",
        status: "nao_evidenciado",
        orientacoes: ["Se você tem experiência real com Kubernetes, inclua-a."],
        onde_evidenciar: null,
        origem: "padrao",
      },
    ],
  });

  render(<RecomendacoesCompetencias idAnalise="a1" />);

  expect(await screen.findByText("Docker")).toBeTruthy();
  expect(obterRecomendacoesCompetencias).toHaveBeenCalledWith("a1");
  expect(screen.getAllByTestId("recomendacao-competencia")).toHaveLength(2);
  expect(screen.getByText("Use o termo Docker no bullet de deploy.")).toBeTruthy();
  expect(screen.getByText("Pouco destacada")).toBeTruthy();
  expect(screen.getByText("Não encontrada")).toBeTruthy();
  expect(screen.getByText(/Onde evidenciar: Experiência profissional/)).toBeTruthy();
  expect(screen.getByText(/Inclua no currículo apenas o que você realmente fez/)).toBeTruthy();
});

it("informa quando não há competências em lacuna", async () => {
  obterRecomendacoesCompetencias.mockResolvedValue({ id_analise: "a1", sem_lacunas: true, recomendacoes: [] });

  render(<RecomendacoesCompetencias idAnalise="a1" />);

  expect(await screen.findByText(/Nenhuma competência em lacuna/)).toBeTruthy();
});
