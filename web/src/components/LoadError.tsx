/** Shown when data is missing, malformed or unreachable: a plain message, never figures. */
export function LoadError() {
  return (
    <section className="load-error" role="alert">
      <h2>This example could not be loaded</h2>
      <p>
        Please try again later. Nothing on this page is shown without its data. The methodology and
        source code are linked below.
      </p>
    </section>
  );
}
