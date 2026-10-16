import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import EditorDadosCurriculo from "./EditorDadosCurriculo.jsx";

afterEach(cleanup);

it("edita os campos estruturados sem descartar os dados extraídos", () => {
  const onSalvar = vi.fn();
  render(
    <EditorDadosCurriculo
      dados={{
        nome_completo: "Ana Original",
        titulo_profissional: "Desenvolvedora",
        contato: { email: "ana@example.com" },
        resumo_profissional: "Resumo original",
        experiencias: [{
          cargo: "Dev",
          empresa: "Empresa A",
          periodo_inicio: "2022",
          periodo_fim: "atual",
          descricao_bullets: ["Construiu APIs"],
        }],
        formacao: [{ curso: "Computação", instituicao: "UnB", periodo: "2020-2024" }],
        habilidades_tecnicas: ["Python"],
        idiomas: [{ idioma: "Inglês", nivel: "Avançado" }],
        certificacoes: ["AWS"],
        secoes_adicionais: [{ titulo: "Projetos", itens: ["Projeto A"] }],
        texto_bruto: "Texto extraído preservado",
      }}
      nomeCurriculo="Currículo da Ana"
      onSalvar={onSalvar}
    />,
  );

  fireEvent.change(screen.getByLabelText("Nome completo"), { target: { value: "Ana Revisada" } });
  fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

  expect(onSalvar).toHaveBeenCalledWith(expect.objectContaining({
    nome_completo: "Ana Revisada",
    nome_curriculo: "Currículo da Ana",
    experiencias: [expect.objectContaining({ descricao_bullets: ["Construiu APIs"] })],
    formacao: [{ curso: "Computação", instituicao: "UnB", periodo: "2020-2024" }],
    texto_bruto: "Texto extraído preservado",
  }));
});

it("salva os dados e o nome alterado com um único botão", () => {
  const onSalvar = vi.fn();
  render(
    <EditorDadosCurriculo
      dados={{ nome_completo: "Ana" }}
      nomeCurriculo="Meu currículo"
      onSalvar={onSalvar}
      textoBotao="Salvar currículo"
    />,
  );

  fireEvent.change(screen.getByLabelText("Nome deste currículo"), {
    target: { value: "Currículo atualizado" },
  });
  const botaoSalvar = screen.getByRole("button", { name: "Salvar currículo" });
  expect(botaoSalvar.closest(".sticky")).not.toBeNull();
  fireEvent.click(botaoSalvar);

  expect(onSalvar).toHaveBeenCalledWith(expect.objectContaining({
    nome_completo: "Ana",
    nome_curriculo: "Currículo atualizado",
  }));
  expect(screen.getAllByRole("button", { name: /Salvar currículo/ })).toHaveLength(1);
});
