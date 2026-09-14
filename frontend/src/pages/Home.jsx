import { Link } from "react-router-dom";

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-900">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Analisador de Currículos</h1>
        <p className="text-gray-600">Estrutura inicial do projeto — Sprint 0 concluída.</p>
        <div className="flex items-center justify-center gap-4">
          <Link
            to="/login"
            style={{ background: "#1D9E75" }}
            className="text-white rounded-md py-2 px-4 font-medium hover:opacity-90"
          >
            Entrar
          </Link>
          <Link
            to="/cadastro"
            className="bg-gray-100 text-gray-700 rounded-md py-2 px-4 font-medium hover:bg-gray-200"
          >
            Criar conta
          </Link>
        </div>
      </div>
    </main>
  );
}
