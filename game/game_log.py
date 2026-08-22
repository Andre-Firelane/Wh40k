MAX_ENTRIES = 400

# Categories a log entry can be tagged with, so the on-screen panel can show
# one kind of event instead of the whole stream (user: "das log unten rechts so
# wie es momentan ist, bringt mir nicht viel. ich möchte dort lieber von mir
# ausgesuchte sachen sehen, anstatt alles").
#
# Untagged entries are category None and only appear under "All". Adding a
# category is meant to be two lines - a constant plus a CATEGORIES row - and
# then tagging the add() calls that belong to it; the panel builds its filter
# buttons from this table, so nothing else has to change.
FAILED_ORDER = "failed"

CATEGORIES = (
    # (key, button label, what it covers)
    (FAILED_ORDER, "Failed",
     "an order the AI could not carry out after every attempt failed"),
)

CATEGORY_LABELS = {key: label for key, label, _why in CATEGORIES}


class LogEntry(str):
    """A log line that also knows what kind of event it was.

    A str SUBCLASS rather than a (message, category) pair on purpose: every
    existing reader - the panel, the tests - treats an entry as a plain string,
    and this keeps all of that working unchanged while the panel can still ask
    for `.category`."""

    __slots__ = ("category",)

    def __new__(cls, message, category=None):
        entry = super().__new__(cls, message)
        entry.category = category
        return entry


class GameLog:
    """`entries` stays an in-memory ring buffer for the on-screen log
    panel - `file_path`, if given, additionally appends EVERY entry,
    unmodified, to a plain-text file for the lifetime of the run.
    User request ("wäre es sinnvoll, dass jedes spiel eine log datei
    produziert, die alle steps und alle bewegungen dokumentiert"): the
    ring buffer already loses anything older within a single
    session, and closing the game loses it entirely - a persistent file
    lets a reported bug be diagnosed from the actual sequence of decisions/
    rolls/positions that led to it, instead of trying to reconstruct a
    guess at the scenario after the fact (see the "Umbau Bewegung" scatter
    report this was added for - several hours of attempted synthetic
    reproduction never found the actual bug, if there is one; a real log
    of the real game would have settled it immediately).

    The buffer holds far more than fits on screen because the panel now
    FILTERS it: 50 entries is a couple of minutes of play and can easily
    contain none at all of the category being looked at, which would make a
    filter look broken. Strings are cheap; the panel stops laying out boxes as
    soon as it runs out of room either way."""

    def __init__(self, file_path=None):
        self.entries = []
        self._file = None
        if file_path is not None:
            self._file = open(file_path, "a", encoding="utf-8")

    def add(self, message, file_only=False, category=None):
        """`file_only=True` records a message in the persistent file (see
        class docstring) without cluttering the on-screen log panel -
        for verbose diagnostic detail (e.g. every model's exact position
        after a move) that's only ever useful when reading the file back
        after the fact.

        `category` is one of the constants above and decides which of the
        panel's filters the line shows up under; untagged lines only appear
        under "All"."""
        if not file_only:
            self.entries.append(LogEntry(message, category))
            if len(self.entries) > MAX_ENTRIES:
                self.entries = self.entries[-MAX_ENTRIES:]
        if self._file is not None:
            self._file.write(message + "\n")
            self._file.flush()

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
