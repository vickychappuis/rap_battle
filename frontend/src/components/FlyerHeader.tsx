/**
 * FlyerHeader - Decorative header banner using the provided neo-deco frame.
 */

export function FlyerHeader() {
  return (
    <div className="flyer-header" role="banner">
      <div className="flyer-heading">
        <span className="flyer-kicker flyer-kicker--live">Live Session</span>
        <h1>Rap Battle</h1>
      </div>
    </div>
  );
}
