import { AlertSignup } from "./components/AlertSignup";
import { ApiSection } from "./components/ApiSection";
import { EmbedSection } from "./components/EmbedSection";
import { Footer } from "./components/Footer";
import { HeroSection } from "./components/HeroSection";
import { HistoryChart } from "./components/HistoryChart";
import { LastVisitBanner } from "./components/LastVisitBanner";
import { MobilePriceBar } from "./components/MobilePriceBar";
import { Nav } from "./components/Nav";
import { PriceStrip } from "./components/PriceStrip";
import { TripCalculator } from "./components/TripCalculator";
import { WorldComparison } from "./components/WorldComparison";

export default function App() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main className="pb-20 sm:pb-0">
        <HeroSection />
        <PriceStrip />
        <LastVisitBanner />
        <AlertSignup />
        <WorldComparison />
        <TripCalculator />
        <HistoryChart />
        <EmbedSection />
        <ApiSection />
      </main>
      <Footer />
      <MobilePriceBar />
    </div>
  );
}
