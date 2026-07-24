import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import { PageLoader } from "./components/PageLoader";
import { ChangesPage } from "./pages/ChangesPage";
import { DataPage } from "./pages/DataPage";
import { DevelopersPage } from "./pages/DevelopersPage";
import { DesignLabPage } from "./pages/DesignLabPage";
import { ConfirmAlert } from "./pages/ConfirmAlert";
import { ManageAlerts } from "./pages/ManageAlerts";
import { PrivacyPage } from "./pages/PrivacyPage";
import { TermsPage } from "./pages/TermsPage";
import { LocaleProvider } from "./i18n/LocaleProvider";
import "@calcom/cal-sans-ui/ui.css";
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
          <Route path="/confirm" element={<ConfirmAlert />} />
          <Route path="/manage" element={<ManageAlerts />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/developers" element={<DevelopersPage />} />
          <Route path="/design-lab" element={<DesignLabPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LocaleProvider>
      <Root />
    </LocaleProvider>
  </React.StrictMode>,
);
