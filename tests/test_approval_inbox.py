import unittest

from approval_inbox import Inbox, Refused

ROLES = {"ana": {"HR"}, "ivan": {"HR"}, "eleni": {"GR"}}


def inbox(volume=50_000):
    i = Inbox(ROLES)
    i.request("R", "agent:x", {"market": "HR", "volume": volume})
    return i


class InboxTest(unittest.TestCase):
    def test_agent_cannot_approve(self):
        with self.assertRaises(Refused):
            inbox().approve("R", "agent:x")

    def test_wrong_market(self):
        with self.assertRaises(Refused):
            inbox().approve("R", "eleni")

    def test_same_person_twice(self):
        i = inbox(200_000)
        i.approve("R", "ana")
        with self.assertRaises(Refused):
            i.approve("R", "ana")

    def test_dual_approval_needed(self):
        i = inbox(200_000)
        i.approve("R", "ana")
        with self.assertRaises(Refused):
            i.execute("R", {"proof_approved": True, "qa_passed": True})
        i.approve("R", "ivan")
        self.assertIn("SENT", i.execute("R", {"proof_approved": True, "qa_passed": True}))

    def test_recheck_at_execution(self):
        i = inbox()
        i.approve("R", "ana")
        with self.assertRaises(Refused):
            i.execute("R", {"proof_approved": False, "qa_passed": True})


if __name__ == "__main__":
    unittest.main()
