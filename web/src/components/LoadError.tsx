import { METHODOLOGY, REPOSITORY } from "../links";

/** Shown when data is missing, malformed or unreachable: a plain message, never figures. */
export function LoadError() {
  return (
    <section className="load-error" role="alert">
      <h2>This example could not be loaded</h2>
      <p>Please try again later. Nothing on this page is shown without its data.</p>
      <ul className="links">
        <li>
          <a href={REPOSITORY}>Source code</a>
        </li>
        <li>
          <a href={METHODOLOGY}>How the numbers work (methodology)</a>
        </li>
      </ul>
    </section>
  );
}
