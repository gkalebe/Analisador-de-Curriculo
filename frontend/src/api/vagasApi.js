import { requisitar } from "./client";

export function listarVagas(email) {
  return requisitar("/api/vagas", { params: { email } });
}

export function criarVaga(formulario) {
  return requisitar("/api/vagas", { method: "POST", body: formulario });
}
