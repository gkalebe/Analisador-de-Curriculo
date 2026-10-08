import { requisitar } from "./client";

export function listarVagas(email) {
  return requisitar("/api/vagas");
}

export function criarVaga(formulario) {
  const { email, ...vaga } = formulario;
  return requisitar("/api/vagas", { method: "POST", body: vaga });
}

export function importarVaga(email, url) {
  return requisitar("/api/vagas/importar", { method: "POST", body: { url } });
}
