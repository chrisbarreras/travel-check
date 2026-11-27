import { LandingComparison } from "./components/LandingComparison";
import { Footer } from "./components/Footer";
import { useLandingView } from "./data";

export function App() {
  const landing = useLandingView();
  return (
    <>
      <header className="header">
        <h1>Travel Check</h1>
        <p className="lead">How often did a flight connection actually work?</p>
        <p className="notice">
          Early version: one real example from a year of U.S. on-time data. The full explorer, with
          more routes, follows.
        </p>
      </header>
      <main id="main" aria-busy={landing.state === "loading"}>
        {landing.state === "ready" ? <LandingComparison view={landing.view} /> : null}
      </main>
      {landing.state === "ready" ? (
        <Footer index={landing.view.index} builtAt={landing.view.builtAt} />
      ) : null}
    </>
  );
}
