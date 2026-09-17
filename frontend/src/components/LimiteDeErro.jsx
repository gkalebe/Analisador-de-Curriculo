import { Component } from "react";

export default class LimiteDeErro extends Component {
  constructor(props) {
    super(props);
    this.state = { comErro: false };
  }

  static getDerivedStateFromError() {
    return { comErro: true };
  }

  componentDidCatch(erro, info) {
    console.error(erro, info);
  }

  componentDidUpdate(propsAnteriores) {
    if (propsAnteriores.chave !== this.props.chave && this.state.comErro) {
      this.setState({ comErro: false });
    }
  }

  render() {
    if (this.state.comErro) {
      return (
        <div className="h-full flex flex-col items-center justify-center gap-2 text-center text-gray-500 p-6">
          <i className="ti ti-alert-triangle text-[32px] text-amber-500"></i>
          <p className="text-sm">Não foi possível exibir a pré-visualização deste currículo.</p>
          <p className="text-xs text-gray-400">Você ainda pode baixar o arquivo original abaixo.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
