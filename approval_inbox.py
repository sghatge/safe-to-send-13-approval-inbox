"""An approval inbox for agent-initiated sends: an agent can ask, only a human can say yes.

Rules enforced:
- the requester (agent or person) can never approve its own request
- approvers need the right role for that market
- sends above a volume threshold need two different approvers
- at execution time everything is re-checked: an approval does not survive a withdrawn proof
Standard library only.
"""

DUAL_APPROVAL_OVER = 100_000


class Refused(Exception):
    pass


class Inbox:
    def __init__(self, roles):
        self.roles = roles          # person -> set of markets they may approve
        self.requests = {}

    def request(self, rid, requester, delivery):
        self.requests[rid] = {"requester": requester, "delivery": delivery, "approvals": [], "status": "pending"}
        need = 2 if delivery["volume"] > DUAL_APPROVAL_OVER else 1
        return f"{rid}: queued by {requester}, needs {need} approver(s)"

    def approve(self, rid, person):
        r = self.requests[rid]
        market = r["delivery"]["market"]
        if person == r["requester"]:
            raise Refused(f"{person} cannot approve their own request")
        if person.startswith("agent:"):
            raise Refused("agents cannot approve")
        if market not in self.roles.get(person, set()):
            raise Refused(f"{person} has no approval rights for {market}")
        if person in r["approvals"]:
            raise Refused(f"{person} already approved {rid}")
        r["approvals"].append(person)
        return f"{rid}: approved by {person} ({len(r['approvals'])}/{self.needed(rid)})"

    def needed(self, rid):
        return 2 if self.requests[rid]["delivery"]["volume"] > DUAL_APPROVAL_OVER else 1

    def execute(self, rid, current_state):
        """Re-check at execution time against the delivery as it is NOW."""
        r = self.requests[rid]
        if len(r["approvals"]) < self.needed(rid):
            raise Refused(f"{rid}: {len(r['approvals'])}/{self.needed(rid)} approvals")
        if not current_state.get("proof_approved"):
            r["status"] = "blocked"
            raise Refused(f"{rid}: proof was withdrawn after approval, send blocked")
        if not current_state.get("qa_passed"):
            r["status"] = "blocked"
            raise Refused(f"{rid}: QA no longer passes, send blocked")
        r["status"] = "sent"
        return f"{rid}: SENT to {r['delivery']['volume']:,} recipients"


def demo():
    inbox = Inbox({"ana.hr": {"HR"}, "ivan.hr": {"HR"}, "ops.lead": {"HR", "GR"}, "eleni.gr": {"GR"}})
    steps = [
        lambda: inbox.request("R1", "agent:bf-helper", {"market": "HR", "volume": 142800}),
        lambda: inbox.approve("R1", "agent:bf-helper"),
        lambda: inbox.approve("R1", "eleni.gr"),
        lambda: inbox.approve("R1", "ana.hr"),
        lambda: inbox.execute("R1", {"proof_approved": True, "qa_passed": True}),
        lambda: inbox.approve("R1", "ana.hr"),
        lambda: inbox.approve("R1", "ivan.hr"),
        lambda: inbox.execute("R1", {"proof_approved": True, "qa_passed": True}),
        lambda: inbox.request("R2", "agent:bf-helper", {"market": "GR", "volume": 61000}),
        lambda: inbox.approve("R2", "eleni.gr"),
        lambda: inbox.execute("R2", {"proof_approved": False, "qa_passed": True}),
    ]
    for step in steps:
        try:
            print("  ok     ", step())
        except Refused as e:
            print("  REFUSED", e)


if __name__ == "__main__":
    demo()
