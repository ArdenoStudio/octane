import { AlertSignup } from "./components/AlertSignup";
import { ApiSection } from "./components/ApiSection";
import { EmbedSection } from "./components/EmbedSection";
import { Footer } from "./components/Footer";
import { HistoryChart } from "./components/HistoryChart";
import { Nav } from "./components/Nav";
import { PriceStrip } from "./components/PriceStrip";
import { TripCalculator } from "./components/TripCalculator";
import { WorldComparison } from "./components/WorldComparison";

export default function App() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main>
        <PriceStrip />
        <WorldComparison />
        <TripCalculator />
        <HistoryChart />
        <AlertSignup />
        <EmbedSection />
        <ApiSection />
      </main>
      <Footer />
    </div>
  );
}
