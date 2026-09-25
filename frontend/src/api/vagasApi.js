import { requisitar } from "./client";

export function listarVagas(email) {
  return requisitar("/api/vagas", { params: { email } });
}

export function criarVaga(formulario) {
  return requisitar("/api/vagas", { method: "POST", body: formulario });
}

export function importarVaga(email, url) {
  return requisitar("/api/vagas/importar", { method: "POST", body: { email, url } });
}
