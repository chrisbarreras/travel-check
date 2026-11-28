import { Footer } from "./components/Footer";
import { LoadError } from "./components/LoadError";
import { Skeleton } from "./components/Skeleton";
import { useShowcase } from "./data";
import { Explorer } from "./explorer/Explorer";

export function App() {
  const showcase = useShowcase();
  return (
    <>
      <header className="header">
        <h1>Travel Check</h1>
        <p className="lead">How often did a flight connection actually work?</p>
        <p className="notice">
          Twelve example routes from a year of U.S. on-time data. Pick a route, then an itinerary.
        </p>
      </header>
      <main id="main" aria-busy={showcase.state === "loading"}>
        {showcase.state === "loading" ? <Skeleton /> : null}
        {showcase.state === "ready" ? <Explorer index={showcase.view.index} /> : null}
        {showcase.state === "error" ? <LoadError /> : null}
      </main>
      {showcase.state === "ready" ? (
        <Footer index={showcase.view.index} builtAt={showcase.view.builtAt} />
      ) : (
        <Footer />
      )}
    </>
  );
}
