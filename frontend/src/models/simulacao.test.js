import { afterEach, expect, it, vi } from "vitest";
import {
  lerRascunho,
  limparRascunho,
  respostaValida,
  salvarRascunho,
  todasRespondidas,
} from "./simulacao.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

function storageEmMemoria() {
  const dados = new Map();
  return {
    getItem: (chave) => (dados.has(chave) ? dados.get(chave) : null),
    setItem: (chave, valor) => dados.set(chave, String(valor)),
    removeItem: (chave) => dados.delete(chave),
  };
}

it("valida o tamanho da resposta depois de remover espaços", () => {
  expect(respostaValida("")).toBe(false);
  expect(respostaValida("   curta   ")).toBe(false);
  expect(respostaValida("x".repeat(10))).toBe(true);
  expect(respostaValida(`  ${"x".repeat(10)}  `)).toBe(true);
  expect(respostaValida("x".repeat(4001))).toBe(false);
});

it("exige todas as perguntas respondidas", () => {
  const perguntas = [{ id_pergunta: "a" }, { id_pergunta: "b" }];
  expect(todasRespondidas(perguntas, { a: "x".repeat(10) })).toBe(false);
  expect(todasRespondidas(perguntas, { a: "x".repeat(10), b: "y".repeat(12) })).toBe(true);
  expect(todasRespondidas([], {})).toBe(false);
});

it("guarda, recupera e limpa o rascunho por simulação", () => {
  vi.stubGlobal("localStorage", storageEmMemoria());

  salvarRascunho("sim-1", { a: "texto" });
  expect(lerRascunho("sim-1")).toEqual({ a: "texto" });
  expect(lerRascunho("sim-2")).toEqual({});

  salvarRascunho("sim-1", { a: "   " });
  expect(lerRascunho("sim-1")).toEqual({});

  salvarRascunho("sim-1", { a: "texto" });
  limparRascunho("sim-1");
  expect(lerRascunho("sim-1")).toEqual({});
});

it("funciona sem localStorage (bloqueado ou com JSON corrompido)", () => {
  vi.stubGlobal("localStorage", {
    getItem: () => {
      throw new Error("bloqueado");
    },
    setItem: () => {
      throw new Error("bloqueado");
    },
    removeItem: () => {
      throw new Error("bloqueado");
    },
  });

  expect(lerRascunho("sim-1")).toEqual({});
  expect(() => salvarRascunho("sim-1", { a: "texto" })).not.toThrow();
  expect(() => limparRascunho("sim-1")).not.toThrow();

  vi.stubGlobal("localStorage", { ...storageEmMemoria(), getItem: () => "{não é json" });
  expect(lerRascunho("sim-1")).toEqual({});
});
