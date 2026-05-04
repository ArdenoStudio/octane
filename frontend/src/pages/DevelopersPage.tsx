import { ApiSection } from "../components/ApiSection";
import { EmbedSection } from "../components/EmbedSection";
import { Footer } from "../components/Footer";
import { Nav } from "../components/Nav";

export function DevelopersPage() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main>
        <EmbedSection />
        <ApiSection />
      </main>
      <Footer />
    </div>
  );
}
