import { afterEach, expect, it, vi } from "vitest";
import { ApiError, requisitar } from "./client.js";

vi.mock("../models/usuario.js", () => ({ lerSessao: () => ({ accessToken: "token-de-teste" }) }));

afterEach(() => {
  vi.unstubAllGlobals();
});

it("usa detail textual como mensagem", () => {
  const erro = new ApiError(409, { detail: "Esta simulação já foi avaliada." });

  expect(erro.message).toBe("Esta simulação já foi avaliada.");
  expect(erro.codigo).toBeNull();
  expect(erro.renovacao_em).toBeNull();
  expect(erro.status).toBe(409);
});

it("usa detail.mensagem e expõe codigo e renovacao_em quando detail é objeto", () => {
  const erro = new ApiError(429, {
    detail: {
      codigo: "cota_ia_excedida",
      tipo_operacao: "mensagem_chat",
      renovacao_em: "2026-12-01T00:00:00+00:00",
      mensagem: "Você atingiu o limite desta operação do seu plano.",
    },
  });

  expect(erro.message).toBe("Você atingiu o limite desta operação do seu plano.");
  expect(erro.codigo).toBe("cota_ia_excedida");
  expect(erro.renovacao_em).toBe("2026-12-01T00:00:00+00:00");
  expect(erro.body.detail.tipo_operacao).toBe("mensagem_chat");
});

it("junta as mensagens de validação quando detail é uma lista (422)", () => {
  const erro = new ApiError(422, {
    detail: [
      { loc: ["body", "respostas", 0, "resposta"], msg: "String should have at least 10 characters" },
      { loc: ["body"], msg: "Value error, Cada pergunta deve ser respondida uma única vez." },
    ],
  });

  expect(erro.message).toBe(
    "String should have at least 10 characters Cada pergunta deve ser respondida uma única vez.",
  );
  expect(erro.codigo).toBeNull();
});

it("cai em mensagens genéricas por status quando não há detail legível", () => {
  expect(new ApiError(500, null).message).toContain("servidor");
  expect(new ApiError(429, {}).message).toContain("Muitas requisições");
  expect(new ApiError(400, { detail: { sem_mensagem: true } }).message).toBe("Erro na requisição.");
});

it("requisitar lança ApiError com o corpo de erro da API", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({
        detail: { codigo: "cota_ia_excedida", renovacao_em: "2026-12-01T00:00:00+00:00", mensagem: "Limite atingido." },
      }),
    }),
  );

  await expect(requisitar("/chat/mensagens", { method: "POST", body: { pergunta: "oi" } })).rejects.toMatchObject({
    name: "Error",
    message: "Limite atingido.",
    codigo: "cota_ia_excedida",
    status: 429,
  });
});
