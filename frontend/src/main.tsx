import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import { ChangesPage } from "./pages/ChangesPage";
import { DataPage } from "./pages/DataPage";
import { ManageAlerts } from "./pages/ManageAlerts";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/manage" element={<ManageAlerts />} />
        <Route path="/data" element={<DataPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
