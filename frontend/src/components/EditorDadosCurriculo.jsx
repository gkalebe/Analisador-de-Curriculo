import { useState } from "react";

const DADOS_VAZIOS = {
  nome_completo: "",
  titulo_profissional: "",
  contato: { email: "", telefone: "", linkedin: "", cidade: "" },
  resumo_profissional: "",
  experiencias: [],
  formacao: [],
  habilidades_tecnicas: [],
  idiomas: [],
  certificacoes: [],
  secoes_adicionais: [],
};

function normalizarDados(dados = {}) {
  return {
    ...DADOS_VAZIOS,
    ...dados,
    contato: { ...DADOS_VAZIOS.contato, ...dados.contato },
    experiencias: dados.experiencias || [],
    formacao: dados.formacao || [],
    habilidades_tecnicas: dados.habilidades_tecnicas || [],
    idiomas: dados.idiomas || [],
    certificacoes: dados.certificacoes || [],
    secoes_adicionais: dados.secoes_adicionais || [],
  };
}

function Campo({ label, value, onChange, multiline = false, ...props }) {
  const classe =
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-[#1e5e3f] focus:outline-none focus:ring-2 focus:ring-[#1e5e3f]/20";
  return (
    <label className="block space-y-1">
      <span className="text-sm font-semibold text-gray-700">{label}</span>
      {multiline ? (
        <textarea
          value={value || ""}
          onChange={(evento) => onChange(evento.target.value)}
          className={`${classe} min-h-24`}
          {...props}
        />
      ) : (
        <input
          value={value || ""}
          onChange={(evento) => onChange(evento.target.value)}
          className={classe}
          {...props}
        />
      )}
    </label>
  );
}

function BotaoAdicionar({ children = "Adicionar item", onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-[#1e5e3f]/40 px-3 py-2 text-sm font-semibold text-[#1e5e3f] hover:bg-[#f0fdf4]"
    >
      <i className="ti ti-plus mr-1"></i>{children}
    </button>
  );
}

function BotaoRemover({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Remover item"
      className="rounded-md p-2 text-gray-500 hover:bg-red-50 hover:text-red-700"
    >
      <i className="ti ti-trash"></i>
    </button>
  );
}

export default function EditorDadosCurriculo({
  dados: dadosIniciais,
  nomeCurriculo = "",
  onSalvar,
  salvando = false,
  textoBotao = "Salvar alterações",
}) {
  const [dados, setDados] = useState(() => normalizarDados(dadosIniciais));
  const [nome, setNome] = useState(nomeCurriculo);

  function alterar(campo, valor) {
    setDados((atuais) => ({ ...atuais, [campo]: valor }));
  }

  function alterarContato(campo, valor) {
    setDados((atuais) => ({
      ...atuais,
      contato: { ...atuais.contato, [campo]: valor },
    }));
  }

  function alterarItem(campo, indice, chave, valor) {
    setDados((atuais) => ({
      ...atuais,
      [campo]: atuais[campo].map((item, idx) =>
        idx === indice ? { ...item, [chave]: valor } : item
      ),
    }));
  }

  function removerItem(campo, indice) {
    setDados((atuais) => ({
      ...atuais,
      [campo]: atuais[campo].filter((_, idx) => idx !== indice),
    }));
  }

  function adicionarItem(campo, item) {
    setDados((atuais) => ({ ...atuais, [campo]: [...atuais[campo], item] }));
  }

  function enviar(evento) {
    evento.preventDefault();
    onSalvar({ ...dados, nome_curriculo: nome });
  }

  return (
    <form onSubmit={enviar} className="space-y-6">
      {nomeCurriculo !== null && (
        <Campo label="Nome deste currículo" value={nome} onChange={setNome} required />
      )}

      <section className="space-y-3">
        <h3 className="font-brand text-lg font-bold text-black">Informações pessoais</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo label="Nome completo" value={dados.nome_completo} onChange={(v) => alterar("nome_completo", v)} />
          <Campo label="Título profissional" value={dados.titulo_profissional} onChange={(v) => alterar("titulo_profissional", v)} />
          <Campo label="E-mail" type="email" value={dados.contato.email} onChange={(v) => alterarContato("email", v)} />
          <Campo label="Telefone" value={dados.contato.telefone} onChange={(v) => alterarContato("telefone", v)} />
          <Campo label="LinkedIn" value={dados.contato.linkedin} onChange={(v) => alterarContato("linkedin", v)} />
          <Campo label="Cidade" value={dados.contato.cidade} onChange={(v) => alterarContato("cidade", v)} />
        </div>
        <Campo label="Resumo profissional" value={dados.resumo_profissional} onChange={(v) => alterar("resumo_profissional", v)} multiline />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-brand text-lg font-bold text-black">Experiência profissional</h3>
          <BotaoAdicionar onClick={() => adicionarItem("experiencias", {
            cargo: "", empresa: "", periodo_inicio: "", periodo_fim: "", descricao_bullets: [],
          })} />
        </div>
        {dados.experiencias.map((item, indice) => (
          <fieldset key={indice} className="space-y-3 rounded-lg border border-gray-200 p-4">
            <div className="flex justify-end"><BotaoRemover onClick={() => removerItem("experiencias", indice)} /></div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Campo label="Cargo" value={item.cargo} onChange={(v) => alterarItem("experiencias", indice, "cargo", v)} />
              <Campo label="Empresa" value={item.empresa} onChange={(v) => alterarItem("experiencias", indice, "empresa", v)} />
              <Campo label="Início" value={item.periodo_inicio} onChange={(v) => alterarItem("experiencias", indice, "periodo_inicio", v)} />
              <Campo label="Término" value={item.periodo_fim} onChange={(v) => alterarItem("experiencias", indice, "periodo_fim", v)} />
            </div>
            <Campo
              label="Atividades (uma por linha)"
              value={(item.descricao_bullets || []).join("\n")}
              onChange={(v) => alterarItem("experiencias", indice, "descricao_bullets", v.split("\n").filter(Boolean))}
              multiline
            />
          </fieldset>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-brand text-lg font-bold text-black">Formação</h3>
          <BotaoAdicionar onClick={() => adicionarItem("formacao", { curso: "", instituicao: "", periodo: "" })} />
        </div>
        {dados.formacao.map((item, indice) => (
          <div key={indice} className="grid items-end gap-3 rounded-lg border border-gray-200 p-4 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <Campo label="Curso" value={item.curso} onChange={(v) => alterarItem("formacao", indice, "curso", v)} />
            <Campo label="Instituição" value={item.instituicao} onChange={(v) => alterarItem("formacao", indice, "instituicao", v)} />
            <Campo label="Período" value={item.periodo} onChange={(v) => alterarItem("formacao", indice, "periodo", v)} />
            <BotaoRemover onClick={() => removerItem("formacao", indice)} />
          </div>
        ))}
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <Campo
          label="Habilidades técnicas (uma por linha)"
          value={dados.habilidades_tecnicas.join("\n")}
          onChange={(v) => alterar("habilidades_tecnicas", v.split("\n").filter(Boolean))}
          multiline
        />
        <Campo
          label="Certificações (uma por linha)"
          value={dados.certificacoes.join("\n")}
          onChange={(v) => alterar("certificacoes", v.split("\n").filter(Boolean))}
          multiline
        />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-brand text-lg font-bold text-black">Idiomas</h3>
          <BotaoAdicionar onClick={() => adicionarItem("idiomas", { idioma: "", nivel: "" })} />
        </div>
        {dados.idiomas.map((item, indice) => (
          <div key={indice} className="grid items-end gap-3 rounded-lg border border-gray-200 p-4 sm:grid-cols-[1fr_1fr_auto]">
            <Campo label="Idioma" value={item.idioma} onChange={(v) => alterarItem("idiomas", indice, "idioma", v)} />
            <Campo label="Nível" value={item.nivel} onChange={(v) => alterarItem("idiomas", indice, "nivel", v)} />
            <BotaoRemover onClick={() => removerItem("idiomas", indice)} />
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-brand text-lg font-bold text-black">Outras seções</h3>
          <BotaoAdicionar onClick={() => adicionarItem("secoes_adicionais", { titulo: "", itens: [] })} />
        </div>
        {dados.secoes_adicionais.map((item, indice) => (
          <div key={indice} className="space-y-3 rounded-lg border border-gray-200 p-4">
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Campo label="Nome da seção" value={item.titulo} onChange={(v) => alterarItem("secoes_adicionais", indice, "titulo", v)} />
              </div>
              <BotaoRemover onClick={() => removerItem("secoes_adicionais", indice)} />
            </div>
            <Campo
              label="Conteúdo (uma informação por linha)"
              value={(item.itens || []).join("\n")}
              onChange={(v) => alterarItem("secoes_adicionais", indice, "itens", v.split("\n").filter(Boolean))}
              multiline
            />
          </div>
        ))}
      </section>

      <div className="sticky bottom-0 z-20 -mx-5 bg-white/95 px-5 pb-1 pt-4 backdrop-blur sm:-mx-7 sm:px-7">
        <div className="flex items-center justify-between gap-3 border-t border-gray-200 pt-4">
          <span className="hidden text-sm text-gray-500 sm:inline">Pronto? Salve para aplicar as alterações.</span>
          <button
            type="submit"
            disabled={salvando}
            className="inline-flex items-center gap-2 rounded-md bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32] disabled:opacity-60"
          >
            {salvando ? <i className="ti ti-loader animate-spin"></i> : <i className="ti ti-device-floppy"></i>}
            {salvando ? "Salvando..." : textoBotao}
          </button>
        </div>
      </div>
    </form>
  );
}
