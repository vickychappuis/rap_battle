/**
 * PlayerCard - Profile card for the battle opponent.
 */

import type { OpponentProfile } from "../data/opponents";

type PlayerCardProps = {
  opponent: OpponentProfile;
};

export function PlayerCard({ opponent }: PlayerCardProps) {
  return (
    <div className="player-card">
      <img
        src={opponent.imageSrc}
        alt={opponent.name}
        className="player-card__avatar"
      />
      <div className="player-card__info">
        <h2 className="player-card__name">{opponent.name}</h2>
        <p className="player-card__subtitle">Age: {opponent.age}</p>
        <p className="player-card__detail">Claims: {opponent.claims}</p>
        <p className="player-card__detail">Reality: {opponent.reality}</p>
        <p className="player-card__detail">Extra Info: {opponent.extraInfo}</p>
      </div>
    </div>
  );
}
