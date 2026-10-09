import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Self-hosted fonts (no third-party requests; the CSP allows only 'self').
import "@fontsource-variable/plus-jakarta-sans/wght.css";
import "@fontsource-variable/plus-jakarta-sans/wght-italic.css";
import "@fontsource-variable/outfit/wght.css";
import "@fontsource-variable/jetbrains-mono/wght.css";

import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
