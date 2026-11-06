import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PlanoDesenvolvimento from "./PlanoDesenvolvimento.jsx";

const { obterPlanoDesenvolvimento } = vi.hoisted(() => ({ obterPlanoDesenvolvimento: vi.fn() }));
vi.mock("../api/analiseApi.js", () => ({ obterPlanoDesenvolvimento }));
vi.mock("../models/usuario.js", () => ({ lerSessao: () => ({ email: "ana@example.com", accessToken: "t" }) }));
vi.mock("../components/Sidebar.jsx", () => ({ default: () => null }));

const item = (competencia, prioridade, extra = {}) => ({
  competencia,
  tipo: "obrigatorio",
  status: "nao_evidenciado",
  prioridade,
  certificacoes: [],
  trilha: [`Estude ${competencia}`, `Pratique ${competencia}`],
  origem: "ia",
  vagas: [{ id_analise: `id-${competencia}`, vaga_titulo: "Backend Pleno" }],
  frequencia: 1,
  ...extra,
});

function renderizar() {
  return render(
    <MemoryRouter>
      <PlanoDesenvolvimento />
    </MemoryRouter>
  );
}

beforeEach(() => vi.clearAllMocks());

it("mostra resumo, trilha e certificação de cada requisito não atendido e filtra por prioridade", async () => {
  obterPlanoDesenvolvimento.mockResolvedValue({
    total_analises: 2,
    sem_analises: false,
    sem_lacunas: false,
    mensagem: "Siga as trilhas abaixo.",
    resumo: { alta: 1, media: 1, baixa: 0, total: 2 },
    itens: [
      item("AWS", "alta", {
        certificacoes: [{ nome: "AWS Certified Cloud Practitioner", emissor: "Amazon Web Services", motivo: "" }],
      }),
      item("Scrum", "media", { tipo: "desejavel", status: "parcial" }),
    ],
    certificacoes_opcionais: [],
  });

  renderizar();

  expect(await screen.findByText("AWS")).toBeTruthy();
  expect(screen.getAllByTestId("item-plano")).toHaveLength(2);
  expect(screen.getByText("Estude AWS")).toBeTruthy();
  expect(screen.getByText("AWS Certified Cloud Practitioner")).toBeTruthy();
  expect(screen.getAllByRole("link", { name: "Backend Pleno" })[0].getAttribute("href")).toContain("id=id-AWS");

  fireEvent.click(screen.getByRole("button", { name: "Alta" }));
  expect(screen.getAllByTestId("item-plano")).toHaveLength(1);
  expect(screen.queryByText("Scrum")).toBeNull();
});

it("sem lacunas informa e mostra certificações opcionais", async () => {
  obterPlanoDesenvolvimento.mockResolvedValue({
    total_analises: 1,
    sem_analises: false,
    sem_lacunas: true,
    mensagem: "Seu currículo atende a todos os requisitos identificados.",
    resumo: { alta: 0, media: 0, baixa: 0, total: 0 },
    itens: [],
    certificacoes_opcionais: [{ nome: "PCAP", emissor: "Python Institute", motivo: "Diferencial" }],
  });

  renderizar();

  expect(await screen.findByText("Nenhuma lacuna nas vagas analisadas.")).toBeTruthy();
  expect(screen.getByText("PCAP")).toBeTruthy();
  expect(screen.getByText("Certificações opcionais para se diferenciar")).toBeTruthy();
});

it("sem análises convida a fazer a primeira", async () => {
  obterPlanoDesenvolvimento.mockResolvedValue({
    total_analises: 0,
    sem_analises: true,
    sem_lacunas: false,
    mensagem: "",
    resumo: { alta: 0, media: 0, baixa: 0, total: 0 },
    itens: [],
    certificacoes_opcionais: [],
  });

  renderizar();

  expect(await screen.findByText("Você ainda não tem análises.")).toBeTruthy();
  expect(screen.getByRole("link", { name: /Fazer uma análise/ })).toBeTruthy();
});
