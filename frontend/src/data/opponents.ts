export type OpponentProfile = {
  id: string;
  name: string;
  age: number;
  claims: string;
  reality: string;
  extraInfo: string;
  imageSrc: string;
};

export const OPPONENTS: OpponentProfile[] = [
  {
    id: "max-gorilla",
    name: "Max Gorilla",
    age: 35,
    claims: "Enlightened, above clout and beef",
    reality: "Obsessed with being respected",
    extraInfo: "Checks Reddit threads about himself every night before bed",
    imageSrc: "/max_gorilla.png",
  },
  {
    id: "bad-panda",
    name: "Bad Panda",
    age: 18,
    claims: "Street-certified, dangerous",
    reality: "Never been in a real fight",
    extraInfo: "Got pressed once and apologized immediately",
    imageSrc: "/bad_panda.png",
  },
  {
    id: "rat-killai",
    name: "Rat Killai",
    age: 26,
    claims: "Viral star, next big thing",
    reality: "One hit wonder",
    extraInfo: "Introduces himself using a song nobody remembers",
    imageSrc: "/rat_killa.png",
  },
];
