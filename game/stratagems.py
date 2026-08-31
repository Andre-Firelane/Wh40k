class Stratagem:
    """Rule 15.01: a stratagem's shape - what CP it costs, WHEN it can be
    used, its TARGET, and its EFFECT. The actual Core Stratagems ("see
    overleaf") haven't been given to us yet, so this only carries the
    generic shape every stratagem shares, for whichever concrete ones come
    later.

    `effect(controller, player, targets)` is called once the stratagem is
    confirmed usable and its CP has already been spent - it's a plain
    callable, so it can freely open a DecisionManager breakpoint for
    stratagems that need an interactive player choice, or just resolve
    immediately for ones that don't. Which applies is decided per
    stratagem, not by this framework (per the user: "wir entscheiden das
    von Stratagem zu Stratagem")."""

    def __init__(
        self, name, cp_cost, effect, when=None, allow_repeat_target=False, max_per_battle=None,
        allow_battle_shocked_target=False,
    ):
        self.name = name
        self.cp_cost = cp_cost
        self.effect = effect
        self.when = when  # optional callable(controller, player) -> bool - phase/timing restriction
        self.allow_repeat_target = allow_repeat_target  # rule 15.01: "unless otherwise stated"
        self.max_per_battle = max_per_battle  # e.g. rule 15.04's "cannot use this stratagem more than once per battle" - stricter than, and on top of, the once-per-phase default below; None means no extra cap
        # Rule 01.07 says a battle-shocked unit can't be the target of any
        # stratagem - but rule 15.04 (Insane Bravery) exists specifically to
        # rescue a unit from a battle-shock roll it's mandated to make
        # *because* it's already battle-shocked (rule 08.03); a blanket
        # 01.07 block would make that exact, obvious use case impossible.
        # Real 10th-edition FAQ rulings confirm Insane Bravery is meant to
        # work here, so this is a narrow, explicit escape hatch - off by
        # default for every other stratagem.
        self.allow_battle_shocked_target = allow_battle_shocked_target


class StratagemController:
    """Rule 15.01's usage restrictions and resolution sequence, shared by
    every stratagem: (1) select targets, (2) spend CP, (3) resolve the
    effect. Both restrictions ("not the same stratagem twice in a phase",
    "not the same unit targeted twice in a phase") are tracked here and
    reset every phase - stratagems can be used in any phase, so this resets
    unconditionally on every phase change (see main.py's advance_turn_phase()),
    unlike the other reset_*_phase() methods that only fire on entering one
    specific phase."""

    def __init__(self, game_log=None, command_points=None):
        self.game_log = game_log
        self.command_points = command_points
        self.used_this_phase = set()      # {(player, stratagem_name)}
        self.targeted_this_phase = set()  # {(player, target)}
        self.used_this_battle = {}        # {(player, stratagem_name): count} - never reset, see Stratagem.max_per_battle
        # User-supplied UX: a modal, must-click-away notice naming whichever
        # Stratagem the AI just used (game/ui/stratagem_notice_overlay.py,
        # wired here by main.py) - a plain callback, same pattern as
        # fight_controller.on_unit_finished_fighting, since this is the one
        # chokepoint EVERY Stratagem use (including Command Re-roll, which
        # is itself just another Stratagem, see game/command_reroll.py)
        # already funnels through, same as the game_log line right below.
        self.on_stratagem_used = None
        # Optional collaborators that lower a use's CP cost, each with
        # available_discount(player, stratagem, targets) -> int and
        # consume(player, stratagem, targets). This controller deliberately
        # doesn't know which ability any of them is. Consulted through
        # _cost_for() so can_use() and use() can never disagree about the
        # price.
        #
        # A LIST, and the stratagem is passed in, because there are now two
        # sources and they need different things: Commander Farsight's
        # Puretide's Teachings (game/puretide.py) keys off the TARGET and
        # ignores which stratagem it is, while the Aeldari Seer Council's
        # Strands of Fate (game/strands_of_fate.py) keys off exactly that -
        # each Fate die value discounts one named stratagem and nothing else.
        # Two sources cannot in practice apply to the same player (one is
        # T'au, the other Aeldari), but a list costs nothing and removes the
        # question - the same generalisation ShootingController.
        # target_reactions got when it grew a second consumer.
        self.cost_discounts = []
        # The MIRROR of cost_discounts, for an effect that makes an OPPONENT's
        # Stratagem dearer - Seer Council's Torc of Morai-Heg is the first.
        # A separate list rather than a discount returning a negative number:
        # "discount" would be a lying name, and the two are clamped
        # differently (see _cost_for).
        self.cost_surcharges = []
        # Optional listeners notified after a use has actually been paid for,
        # each called as listener(player, stratagem, targets). A LIST for the
        # same reason cost_discounts above is one.
        #
        # Distinct from on_stratagem_used, which is the AI-notice callback and
        # deliberately does NOT carry the targets: the one consumer here is
        # Retaliation Cadre's Puretide Engram Neurochip Enhancement, whose
        # printed trigger is "each time you TARGET THE BEARER'S UNIT with a
        # Stratagem" - so which units were targeted is the whole question, and
        # widening on_stratagem_used' signature would have touched a callback
        # main.py wires to an overlay that has no use for them.
        #
        # Fired after stratagem.effect() rather than before, so a Neurochip CP
        # can never be spent by the very use that granted it.
        self.on_targets_chosen = []

    def reset_phase(self):
        self.used_this_phase = set()
        self.targeted_this_phase = set()

    def _cost_for(self, player, stratagem, targets, extra_cp):
        """The CP this use actually costs, discount included. One definition,
        read by both can_use() and use() - a Stratagem that looked affordable
        and then failed to pay would be the obvious bug if they diverged.

        A pure query: asking the price never spends the discount's own
        once-per-round availability (see PuretideController)."""
        cost = stratagem.cp_cost + extra_cp
        for discount in self.cost_discounts:
            cost -= discount.available_discount(player, stratagem, targets)
        # CLAMPED BEFORE THE SURCHARGE, and the order is the whole difference:
        # a discount cannot take a cost below zero (nobody is PAID command
        # points), and a surcharge then applies to what is actually owed. The
        # two orders agree except when a discount exceeds the cost - where the
        # other one would let any discount at all cancel the surcharge.
        cost = max(0, cost)
        for surcharge in self.cost_surcharges:
            cost += surcharge.available_surcharge(player, stratagem, targets)
        return max(0, cost)

    def can_use(self, player, stratagem, targets, extra_cp=0):
        if (player, stratagem.name) in self.used_this_phase:
            return False
        if stratagem.max_per_battle is not None:
            if self.used_this_battle.get((player, stratagem.name), 0) >= stratagem.max_per_battle:
                return False
        if stratagem.when is not None and not stratagem.when(self, player):
            return False
        cost = self._cost_for(player, stratagem, targets, extra_cp)
        if self.command_points is not None and self.command_points.cp.get(player, 0) < cost:
            return False
        for target in targets:
            # Rule 01.07: a battle-shocked unit can't be targeted by any
            # stratagem, regardless of whose it is - except a stratagem that
            # explicitly opts out (see Stratagem.allow_battle_shocked_target).
            if getattr(target, "battle_shocked", False) and not stratagem.allow_battle_shocked_target:
                return False
            if not stratagem.allow_repeat_target and (player, target) in self.targeted_this_phase:
                return False
        return True

    def _surcharge_for(self, player, stratagem, targets):
        """The extra CP this usage carries - a pure query, like _cost_for."""
        return sum(s.available_surcharge(player, stratagem, targets)
                   for s in self.cost_surcharges)

    def blocked_by_surcharge(self, player, stratagem, targets, extra_cp=0):
        """Whether this usage fails ONLY because of a surcharge.

        Torc of Morai-Heg's printed FAQ: made unaffordable by the surcharge,
        "no CP are spent and that Stratagem's effects are not resolved (but
        that Stratagem still counts as having been used this phase)". So the
        two ways of being unaffordable have to be told apart - unaffordable
        anyway is the old behaviour and records nothing."""
        surcharge = self._surcharge_for(player, stratagem, targets)
        if surcharge <= 0 or self.command_points is None:
            return False
        have = self.command_points.cp.get(player, 0)
        cost = self._cost_for(player, stratagem, targets, extra_cp)
        return have < cost and have >= cost - surcharge

    def use(self, player, stratagem, targets, extra_cp=0):
        if not self.can_use(player, stratagem, targets, extra_cp):
            # THE FAQ CLAUSE. Priced out by a surcharge, the Stratagem still
            # counts as used this phase - so the opponent cannot simply retry
            # it once the Torc is spent, which is most of what it buys.
            if self.blocked_by_surcharge(player, stratagem, targets, extra_cp):
                for surcharge in self.cost_surcharges:
                    surcharge.consume(player, stratagem, targets)
                self.used_this_phase.add((player, stratagem.name))
                if self.game_log is not None:
                    self.game_log.add(
                        f"{player} cannot afford {stratagem.name} at the increased "
                        f"cost - no CP are spent and it is not resolved, but it "
                        f"counts as used this phase.")
            return False
        cost = self._cost_for(player, stratagem, targets, extra_cp)
        if self.command_points is not None and not self.command_points.spend_cp(player, cost):
            return False
        # Only now, once the CP have genuinely been spent at the reduced
        # price, does a discount count as used.
        for discount in self.cost_discounts:
            discount.consume(player, stratagem, targets)
        for surcharge in self.cost_surcharges:
            surcharge.consume(player, stratagem, targets)

        self.used_this_phase.add((player, stratagem.name))
        for target in targets:
            self.targeted_this_phase.add((player, target))
        if stratagem.max_per_battle is not None:
            key = (player, stratagem.name)
            self.used_this_battle[key] = self.used_this_battle.get(key, 0) + 1

        if self.game_log is not None:
            self.game_log.add(f"{player} uses {stratagem.name}.")
        if self.on_stratagem_used is not None:
            self.on_stratagem_used(player, stratagem)

        stratagem.effect(self, player, targets)
        for listener in self.on_targets_chosen or ():
            listener(player, stratagem, targets)
        return True
