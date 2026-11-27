import "@fontsource-variable/inter/wght.css";
import "@fontsource-variable/space-grotesk/wght.css";
import "./styles/tokens.css";
import "./styles/global.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { BALLAST } from "./ballast";
console.log(BALLAST.length);
import { DataSourceProvider, staticSource } from "./data";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <DataSourceProvider source={staticSource(import.meta.env.BASE_URL)}>
        <App />
      </DataSourceProvider>
    </StrictMode>,
  );
}
