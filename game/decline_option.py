"""Which option on a decision means "no" - ONE definition.

WHY IT EXISTS. game/ui/button_style.py's own docstring already fixes what the
red "danger" accent means in this HUD: "this button abandons/declines the
current action". ActionPanel has honoured that for a long time - every Cancel,
every "Decline Charge", every "Decline Consolidation" is drawn red - but
DecisionOverlay, the modal box that carries ~90 of this game's break points,
painted every option the same flat grey. User: "Decline Buttons auch in den
overlays rot einfaerben."

WHY A LABEL PREDICATE RATHER THAN A FLAG AT THE CALL SITE. The alternative was
a fourth slot in DecisionManager.request()'s option tuples, set by hand at
~100 call sites. Nothing would ever go red-hot if one was missed - the button
would simply stay grey, i.e. exactly today's bug - so the flag would rot
silently. The labels, on the other hand, are already written for humans and
already say "no" in a small, closed vocabulary; the AST sweep in
test_decline_buttons.py pins that vocabulary against every literal option label
in game/, so a NEW way of spelling "no" turns that test red instead of
quietly drawing another grey Decline.

WHAT COUNTS. Only the branch that declines an OFFER - the one that leaves the
board as it found it. A genuine two-way choice ("Leap to Defend" vs "Into the
Fray", "[LETHAL HITS]" vs "[SUSTAINED HITS 1]") has no "no" branch and gets no
red, because red would then be saying something false about half a real
decision.
"""

# Matched as PREFIXES, longest thought first. Prefixes rather than exact
# strings because several of these are built with an f-string and carry their
# own numbers - "Keep the Advance roll (7)", "Decline (2 CP)" - and the part
# that says "no" is always the front of the label.
DECLINE_PREFIXES = (
    "Decline",                    # 41 call sites, plus the panel's "Decline Charge"/"Decline Consolidation"
    "Cancel",
    "Do not ",                    # "Do not use it", "Do not mark", "Do not heal"
    "Don't ",
    "Keep it",                    # decline a re-roll: the dice stand
    "Keep result",
    "Keep them all",
    "Keep the ",                  # "Keep the token[ - one ability]", "Keep the card", "Keep the <roll> roll (n)"
    "Stay put",
    "Stay on the battlefield",
    "Save it",                    # "Save it", "Save it for later" - a once-per-battle resource kept back
    "Leave them unguarded",
    "Leave the pool alone",
    "No more",                    # the end of a repeating offer
)


def is_decline(label):
    """True when this option label is the "no" branch of an offer."""
    if not label:
        return False
    return label.strip().startswith(DECLINE_PREFIXES)
