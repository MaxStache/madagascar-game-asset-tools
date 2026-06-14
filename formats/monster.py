# Base class of a Monster
class Monster:
    name = ""
    armorClass = 0
    hitPoints = 0
    speeds = {
        "ground": 0,
        "air": 0,
    }
    challengeRating = 0
    description = ""

    def __init__(
        self,
        name: str,
        armorClass: int,
        hitPoints: int,
        speeds: dict,
        challengeRating: float,
        description: str = "",
    ):
        self.name = name
        self.armorClass = armorClass
        self.hitPoints = hitPoints
        self.speeds = speeds
        self.challengeRating = challengeRating
        self.description = description

    def print_stats(self):
        print(f"-- Stats for {self.name} --")
        print(f" Armor Class: {self.armorClass}")

        print(f" Hit Points: {self.hitPoints}")

        print(" Speeds:")
        for speed_type, speed_value in self.speeds.items():
            if speed_value > 0:
                print(f" \t{speed_type.capitalize()}: {speed_value}")

        print(f" Challenge Rating: {self.challengeRating}")

        # If a description is set (Not None etc.) then print it
        if self.description:
            print(f" Description: {self.description}")


# Add more monsters here
monsters = [
    Monster(
        name="Orc",
        armorClass=13,
        hitPoints=15,
        speeds={"ground": 30, "air": 0},
        challengeRating=0.5,
        description="Orcs are brutish, aggressive humanoids with green or gray skin. They often live in tribal societies and are known for their strength and ferocity in battle.",
    ),
]

MonsterToSearchFor = "Goblin"

found_monster = None
for monster in monsters:  # Iterate throgh monsters
    if (
        monster.name == MonsterToSearchFor
    ):  # Check if the name matches the one we are looking for
        found_monster = monster
        break  # End the loop since we found the monster we were looking for

if found_monster: # Monster was found?
    found_monster.print_stats()  # Print the stats of the monster we found
else:
    print(f"Monster '{MonsterToSearchFor}' not found in the list.")