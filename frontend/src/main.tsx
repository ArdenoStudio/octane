import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import { PageLoader } from "./components/PageLoader";
import { ChangesPage } from "./pages/ChangesPage";
import { DataPage } from "./pages/DataPage";
import { DevelopersPage } from "./pages/DevelopersPage";
import { ManageAlerts } from "./pages/ManageAlerts";
import { DesignLabPage } from "./pages/__design_lab/page";
import "./index.css";

function Root() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 900);
    return () => clearTimeout(t);
  }, []);

  return (
    <>
      <PageLoader show={loading} />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/changes" element={<ChangesPage />} />
          <Route path="/manage" element={<ManageAlerts />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/developers" element={<DevelopersPage />} />
          <Route path="/__design_lab" element={<DesignLabPage />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
