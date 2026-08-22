class DecisionManager:
    """Generic 'decision break point': certain rules, abilities or
    stratagems trigger at specific moments and must interrupt the game,
    offering the relevant player a choice between named options before
    anything else can continue - e.g. "fire Overwatch with this unit?" at
    the end of the opponent's Shooting phase, or "use a Command Reroll on
    this die?" after any dice roll.

    A real QUEUE, not a single slot - user report: "stratagem prompts
    werden immer noch durch andere prompts überschrieben, da KI im
    Hintergrund weitermacht... hier braucht es generell eine Queue, die
    sowas verhindert." The previous single-slot design's request() simply
    did nothing ("if self.is_pending: return") whenever a second decision
    was requested while an earlier one was still unresolved - not an
    overwrite in the sense of replacing what's on screen, but just as
    lossy: whatever triggered that second request (a reactive Stratagem
    offer, a [LETHAL HITS]/[PRECISION]/[TWIN-LINKED] choice mid-attack,
    Command Reroll, ...) got silently dropped and never asked at all,
    exactly the kind of "the AI keeps going in the background and steps on
    another pending decision" bug already fixed elsewhere for
    ai_action_paused_this_frame/rapid_ingress_controller.pending_squad -
    this is the same class of bug, but structural: no per-call-site gate
    can fix it, since ANY code path that calls request() while another
    decision is already open is a potential victim. Queuing instead - same
    pattern as game/ui/stratagem_notice_overlay.py's StratagemNoticeOverlay,
    which never had this problem for exactly this reason - guarantees every
    requested decision eventually gets its turn, in the order it was
    asked, instead of some of them vanishing.

    Only the FRONT of the queue is ever "pending" (visible via
    is_pending/player/prompt/options/is_stratagem, chosen via choose()) -
    everything else about the external interface is unchanged, so callers
    that only ever dealt with "one decision at a time" keep working
    unmodified. Resolving the front entry (choose()) pops it and, if
    another was already queued behind it, that one becomes pending
    immediately - including one a callback enqueues as it runs (e.g.
    Heroic Intervention's mode-choice), which lands at the BACK of
    whatever's left, preserving first-asked-first-shown order rather than
    jumping the queue."""

    def __init__(self):
        self._queue = []  # [{"player", "prompt", "options", "is_stratagem"}, ...] - front is the pending one

    @property
    def is_pending(self):
        return bool(self._queue)

    @property
    def player(self):
        return self._queue[0]["player"] if self._queue else None

    @property
    def prompt(self):
        return self._queue[0]["prompt"] if self._queue else None

    @property
    def options(self):
        return self._queue[0]["options"] if self._queue else None

    @property
    def is_stratagem(self):
        return self._queue[0]["is_stratagem"] if self._queue else False

    def request(self, player, prompt, options, is_stratagem=False):
        """options: [(label, callback), ...]. Enqueued behind whatever's
        already pending, if anything - never dropped.

        is_stratagem: whether this break point exists because a Stratagem
        (15.01) is being offered or resolved - e.g. Fire Overwatch/Rapid
        Ingress/Counteroffensive/Heroic Intervention (including Heroic
        Intervention's own follow-up mode choice, since CP is already
        spent by the time that one opens) - as opposed to a core/datasheet
        rule's own decision point ([LETHAL HITS]/[PRECISION]/
        [TWIN-LINKED], Suppression Volley, ...), which isn't a Stratagem
        spend at all. DecisionOverlay reads this to color its heading with
        the same violet "stratagem" accent already used for Stratagem
        buttons (game/ui/button_style.py) and StratagemNoticeOverlay - User:
        "der violette color code für stratagems muss sich auch in den
        überschriften wiederfinden, wenn das spiel mit einem confirmation
        overlay unterbricht, zb für Abwehrfeuer oder Heroic Intervention"."""
        self._queue.append({
            "player": player,
            "prompt": prompt,
            "options": [{"label": label, "callback": callback} for label, callback in options],
            "is_stratagem": is_stratagem,
        })

    def choose(self, index):
        if not self.is_pending or not (0 <= index < len(self.options)):
            return
        entry = self._queue.pop(0)
        callback = entry["options"][index]["callback"]
        if callback is not None:
            callback()
