import { Component } from "react";
import { Link, useLocation } from "react-router-dom";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { comErro: false };
  }

  static getDerivedStateFromError() {
    return { comErro: true };
  }

  componentDidCatch(erro, info) {
    console.error("Erro não tratado ao renderizar a aplicação.", erro, info);
  }

  render() {
    if (this.state.comErro) {
      return (
        <main
          role="alert"
          className="min-h-screen flex items-center justify-center bg-[#f3f3f3] p-6 text-gray-900"
        >
          <section className="w-full max-w-lg rounded-xl border-[0.5px] border-black bg-white p-8 text-center shadow-sm">
            <i className="ti ti-alert-triangle text-[42px] text-amber-500" aria-hidden="true"></i>
            <h1 className="mt-3 font-brand text-2xl font-bold text-black">Ocorreu um erro inesperado</h1>
            <p className="mt-2 text-sm text-gray-600">
              Não foi possível exibir esta página. Volte ao início para continuar navegando.
            </p>
            <Link
              to="/"
              className="mt-6 inline-flex rounded-lg bg-[#1e5e3f] px-5 py-2.5 font-bold text-white hover:bg-[#174a32]"
            >
              Voltar para o início
            </Link>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

export default function LimiteDeErroGlobal({ children }) {
  const location = useLocation();

  return <ErrorBoundary key={location.key}>{children}</ErrorBoundary>;
}
