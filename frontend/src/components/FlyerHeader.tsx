/**
 * FlyerHeader - Logo over background.
 */

export function FlyerHeader() {
  return (
    <header className="flyer-header relative z-10" role="banner">
      <img
        src="/rap_arena_logo.webp"
        alt="Rap Arena"
        className="h-24 absolute -bottom-8 left-1/2 -translate-x-1/2"
      />
    </header>
  );
}
