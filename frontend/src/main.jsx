import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import LimiteDeErroGlobal from "./components/LimiteDeErroGlobal.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <LimiteDeErroGlobal>
        <App />
      </LimiteDeErroGlobal>
    </BrowserRouter>
  </React.StrictMode>
);
