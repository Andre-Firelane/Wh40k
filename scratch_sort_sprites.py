"""Sort Sprites/ into one folder per faction.

Ownership comes from the SURVEY (which datasheet actually resolves to which
file), not from guessing at names - so a file only moves when the engine itself
says who it belongs to. Everything unclaimed is listed for a decision rather
than shovelled somewhere.
"""
import json, os, subprocess, sys

SPRITES = "Sprites"
FACTION_DIR = {"Aeldari": "Aeldari", "Orks": "Orks", "Tau Empire": "Tau Empire",
               "Necrons": "Necrons", "Death Guard": "Death Guard"}

# Cross-faction files that STAY at the top level - they belong to no army.
TOP_LEVEL = {"Blood.png", "Dice.png", "Map3.png"}

# Files the survey cannot claim because no datasheet resolves to them on a
# default build, but which plainly belong to one faction: the four badges, the
# three Storm Guardian weapon variants and the T'au Pathfinder one. Assigned by
# hand, and listed here so the assignment is visible rather than inferred.
BY_HAND = {
    "Aeldari Logo.png": "Aeldari",
    "Ork Logo.png": "Orks",
    "Tau Logo.png": "Tau Empire",
    "Necron Logo.png": "Necrons",
    "Assault Guardian - Flamer.png": "Aeldari",
    "Assault Guardian - Fusion Gun.png": "Aeldari",
    "Assault Guardian - Power Sword.png": "Aeldari",
    "Pathfinder Rail Rifle.png": "Tau Empire",
    # Aeldari datasheets that exist and whose art the code did not map yet -
    # see the mapping additions that go with this.
    "Autarch.png": "Aeldari",
    "Autarch Wayleaper.png": "Aeldari",
    "Corsair Skyrunner.png": "Aeldari",
    "Corsair Voidreavers.png": "Aeldari",
    "D-Cannon Platform.png": "Aeldari",
    "Fire Prism.png": "Aeldari",
    "Maugan Ra.png": "Aeldari",
    "Night Spinner.png": "Aeldari",
    "Spirit Seer.png": "Aeldari",
    "Vyper.png": "Aeldari",
    "Wraith Blades.png": "Aeldari",
    # Harlequins - deliberately not a built datasheet (user decision), but
    # unmistakably Aeldari, so it is filed rather than left loose.
    "Solitaire.png": "Aeldari",
}


def main(apply_it):
    survey = json.load(open("sprite_survey.json"))
    owner = {k: v[0] for k, v in survey["owner"].items() if len(v) == 1}
    files = sorted(f for f in os.listdir(SPRITES)
                   if os.path.isfile(os.path.join(SPRITES, f)))

    plan, leftover = [], []
    for f in files:
        if f in TOP_LEVEL:
            continue
        faction = owner.get(f) or BY_HAND.get(f)
        if faction is None:
            leftover.append(f)
            continue
        plan.append((f, FACTION_DIR[faction]))

    by_dir = {}
    for f, d in plan:
        by_dir.setdefault(d, []).append(f)
    for d in sorted(by_dir):
        print("%-14s %3d files" % (d, len(by_dir[d])))
    print("stay at top   %3d files  %s" % (len(TOP_LEVEL), sorted(TOP_LEVEL)))
    if leftover:
        print("\nUNSORTED (%d) - decide these by hand:" % len(leftover))
        for f in leftover:
            print("   ", f)

    if not apply_it:
        print("\n(dry run - pass --apply to move)")
        return
    for d in sorted(by_dir):
        os.makedirs(os.path.join(SPRITES, d), exist_ok=True)
    moved = 0
    for f, d in plan:
        src = os.path.join(SPRITES, f)
        dst = os.path.join(SPRITES, d, f)
        if os.path.exists(dst):
            print("SKIP (target exists):", dst)
            continue
        r = subprocess.run(["git", "mv", src, dst], capture_output=True, text=True)
        if r.returncode != 0:
            # Untracked files are not known to git; move them plainly.
            os.rename(src, dst)
        moved += 1
    print("\nmoved %d files" % moved)


if __name__ == "__main__":
    main("--apply" in sys.argv)
