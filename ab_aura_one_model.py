import io, os, re, shutil, subprocess, sys
RENDERER = os.path.join("game", "renderer.py")
MAIN = "main.py"
SUITE = "test_aura_ruler.py"

def read(p): return io.open(p, encoding="utf-8").read()
def write(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)

def run():
    for root, dirs, _f in os.walk("."):
        for n in list(dirs):
            if n == "__pycache__":
                shutil.rmtree(os.path.join(root, n), ignore_errors=True); dirs.remove(n)
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    t = out.stdout + out.stderr
    m = re.search(r"(\d+)/(\d+) checks passed", t)
    return (int(m.group(1)), int(m.group(2)), t) if m else (None, None, t)

PROBES = [
    ("the ruler ringing EVERY model again (THE REPORT)", RENDERER,
     "        models = squad.models\n        if model is not None and model.squad is squad:\n            models = [model]",
     "        models = squad.models"),
    ("the anchor not passed from main()", MAIN,
     "aura_ruler.active_radius(), model=movement_controller.selected_model,",
     "aura_ruler.active_radius(),"),
    ("a stale anchor honoured across units", RENDERER,
     "if model is not None and model.squad is squad:",
     "if model is not None:"),
]

base, total, txt = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + txt[-1500:]); raise SystemExit(2)
print(f"baseline: {base}/{total}\n")
bad = 0
for label, path, new, old in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print(f"  SKIP     {label}: anchor not unique in {path}"); bad += 1; continue
    try:
        write(path, src.replace(new, old))
        got, tot, t = run()
        if got is None: verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base: verdict, detail = "BITES", f"{got}/{tot}"
        else: verdict, detail = "NO BITE", f"{got}/{tot} - FINDING ABOUT THE TEST"; bad += 1
        print(f"  {verdict:8} {label}: {detail}")
        if got is not None and got < base:
            for line in t.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:100]}"); break
    finally:
        write(path, src)
for root, dirs, _f in os.walk("."):
    for n in list(dirs):
        if n == "__pycache__":
            shutil.rmtree(os.path.join(root, n), ignore_errors=True); dirs.remove(n)
print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
