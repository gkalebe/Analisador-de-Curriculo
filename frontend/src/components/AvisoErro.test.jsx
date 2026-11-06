import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AvisoErro, { paraErroTela } from "./AvisoErro.jsx";
import { ApiError } from "../api/client.js";

afterEach(cleanup);

function renderizar(erro) {
  return render(
    <MemoryRouter>
      <AvisoErro erro={erro} />
    </MemoryRouter>,
  );
}

it("mostra renovação e link para /planos quando a cota de IA acabou (ex.: chat)", () => {
  const erro = paraErroTela(
    new ApiError(429, {
      detail: {
        codigo: "cota_ia_excedida",
        renovacao_em: "2026-12-15T03:00:00+00:00",
        mensagem: "Você atingiu o limite desta operação do seu plano.",
      },
    }),
    "Não foi possível enviar sua mensagem.",
  );

  renderizar(erro);

  expect(screen.getByRole("alert").textContent).toContain("Você atingiu o limite desta operação do seu plano.");
  expect(screen.getByRole("alert").textContent).toContain("15 de dezembro de 2026");
  expect(screen.getByRole("link", { name: "Ver planos" }).getAttribute("href")).toBe("/planos");
});

it("outros erros mostram só a mensagem, sem convite para planos", () => {
  renderizar(paraErroTela(new ApiError(502, { detail: "A IA não conseguiu gerar uma resposta." }), "padrão"));

  expect(screen.getByRole("alert").textContent).toBe("A IA não conseguiu gerar uma resposta.");
  expect(screen.queryByRole("link")).toBeNull();
});

it("falhas que não são ApiError usam a mensagem padrão e nada é exibido sem erro", () => {
  expect(paraErroTela(new TypeError("Failed to fetch"), "Tente novamente.").mensagem).toBe("Tente novamente.");

  renderizar(null);
  expect(screen.queryByRole("alert")).toBeNull();
});
