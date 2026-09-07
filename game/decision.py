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
        self._queue = []  # [{"player", "prompt", "subject", "options", "is_stratagem", "is_battle_focus"}, ...] - front is the pending one

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
    def subject(self):
        """What this break point is ABOUT, when naming it is what makes the
        question answerable - Burden of Trust's objective, say. Shown as its
        own heading by the board-pick screen (game/unit_pick.py); None for the
        ordinary prompts, whose text already carries their subject."""
        return self._queue[0].get("subject") if self._queue else None

    @property
    def options(self):
        return self._queue[0]["options"] if self._queue else None

    @property
    def is_stratagem(self):
        return self._queue[0]["is_stratagem"] if self._queue else False

    @property
    def is_battle_focus(self):
        return self._queue[0]["is_battle_focus"] if self._queue else False

    @property
    def accent(self):
        """Which of button_style's accent palettes this break point belongs
        to, or None for a plain core/datasheet decision.

        ONE derived answer rather than letting DecisionOverlay grow a second
        if/else over the flags: the two flags are separate RULES questions
        (is this a 15.01 CP spend / is this an Agile Manoeuvre spending a
        Battle Focus token) and both deserve to keep their own names, but
        "what colour is the heading" is one question with one answer, and a
        third category should cost one line here instead of another branch
        at the draw site. They are mutually exclusive by construction - a
        Stratagem is not an Agile Manoeuvre - so the order below never
        actually arbitrates; it is written down so it cannot drift."""
        if self.is_stratagem:
            return "stratagem"
        if self.is_battle_focus:
            return "battle_focus"
        return None

    def request(self, player, prompt, options, is_stratagem=False, is_battle_focus=False, subject=None):
        """options: [(label, callback), ...] - or [(label, callback, squad),
        ...] for an option that names a UNIT. Enqueued behind whatever's
        already pending, if anything - never dropped.

        THE THIRD SLOT IS WHAT MAKES A PROMPT ANSWERABLE ON THE BOARD.
        User: "Immer wenn man eine einheit auf dem schlachtfeld wählen muss (zb
        wall of mirrors) will ich die einheit nicht aus einer liste wählen,
        sondern auf dem schlachtfeld. Wie bei overwatch." Tagging an option with
        its squad is the whole of what a call site has to do; game/unit_pick.py
        decides whether the prompt really can be clicked (it refuses when a
        tagged unit is off the board or offered twice) and the panel, the board
        highlight and main.py's click branch read that one answer.

        It rides IN the option tuple rather than in a parallel `squads=` list on
        purpose: ~55 call sites would each have had to keep two lists aligned by
        hand, and a misalignment resolves a click on one unit into another
        unit's callback without ever raising. Here there is nothing to align.

        `options` itself is unchanged for every reader - the label/callback pair
        still sits at the same index - so choose(index), the overlay and
        ai/agent_driver.py's _maybe_resolve_decision() are untouched by this.

        subject: see the property of the same name.

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
        overlay unterbricht, zb für Abwehrfeuer oder Heroic Intervention".

        is_battle_focus: the same idea one colour over - this break point is
        an Aeldari Agile Manoeuvre (game/battle_focus.py) offering to spend a
        Battle Focus TOKEN. User: "colorcode für agile manouvers ist momentan
        lila wie stratagems. soll aber türkis sein. (buttons, überschriften)"
        - the buttons live in ActionPanel, and "überschriften" is this
        overlay's heading, so both read the same turquoise. Mutually
        exclusive with is_stratagem; see the accent property."""
        self._queue.append({
            "player": player,
            "prompt": prompt,
            "subject": subject,
            "options": [self._option(entry) for entry in options],
            "is_stratagem": is_stratagem,
            "is_battle_focus": is_battle_focus,
        })

    @staticmethod
    def _option(entry):
        """(label, callback) or (label, callback, squad) -> the stored dict.

        The squad key is always present so every reader can ask for it with a
        plain [] and a mixed list (units plus a "Decline") needs no condition."""
        label, callback = entry[0], entry[1]
        squad = entry[2] if len(entry) > 2 else None
        return {"label": label, "callback": callback, "squad": squad}

    def index_of_squad(self, squad):
        """The pending option index that offers `squad`, or None.

        Resolution still goes through choose(index) - this only translates a
        CLICK into the index the overlay would have produced, so there is one
        resolution path rather than a second one beside it."""
        if not self.is_pending or squad is None:
            return None
        for index, option in enumerate(self.options):
            if option.get("squad") is squad:
                return index
        return None

    def choose(self, index):
        if not self.is_pending or not (0 <= index < len(self.options)):
            return
        entry = self._queue.pop(0)
        callback = entry["options"][index]["callback"]
        if callback is not None:
            callback()
