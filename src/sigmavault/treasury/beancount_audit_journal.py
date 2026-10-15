from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from sigmavault.treasury.signed_decision_record import (
    SignedDecisionRecord,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)


class BeancountAuditJournal:
    """Append cryptographically verified treasury decision events."""

    def __init__(
        self,
        path: str | Path,
        public_key: Ed25519PublicKey,
    ) -> None:
        self.path = Path(path)
        self.public_key = public_key

    def append(self, record: SignedDecisionRecord) -> None:
        """Append a decision only after complete audit verification."""

        verified = verify_complete_decision_audit(
            payload=record.payload,
            journal_entry=record.journal_entry,
            signature=record.signature,
            public_key=self.public_key,
        )

        if not verified:
            raise ValueError(
                "Signed decision audit verification failed"
            )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open("a", encoding="utf-8") as journal:
            journal.write(record.journal_entry)

            if not record.journal_entry.endswith("\n"):
                journal.write("\n")

            journal.write("\n")