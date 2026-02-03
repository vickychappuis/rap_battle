/**
 * PlayerCard - Profile card for the battle opponent.
 */

export function PlayerCard() {
  return (
    <div className="player-card">
      <img src="/max_gorilla.png" alt="Max Gorilla" className="player-card__avatar" />
      <div className="player-card__info">
        <h2 className="player-card__name">Max Gorilla</h2>
        <p className="player-card__subtitle">Age: 35</p>
        <p className="player-card__detail">Claims: Enlightened, above clout and beef</p>
        <p className="player-card__detail">Reality: Obsessed with being respected</p>
        <p className="player-card__detail">Extra Info: Checks Reddit threads about himself every night before bed</p>
      </div>
    </div>
  );
}
