/** The layout's shape while data loads: no spinner and no placeholder numbers (design.md). */
export function Skeleton() {
  return (
    <div className="skeleton" data-testid="skeleton" aria-hidden="true">
      <div className="skeleton-line skeleton-heading" />
      <div className="skeleton-line" />
      <div className="cards">
        <div className="card skeleton-card" />
        <div className="card skeleton-card" />
      </div>
    </div>
  );
}
