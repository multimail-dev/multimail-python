"""MultiMail quickstart — send your first email in 10 lines."""

from multimail import MultiMail

mm = MultiMail("MULTIMAIL_API_KEY")

# Find your mailbox
mailboxes = mm.list_mailboxes()
mailbox = mailboxes[0]
print(f"Using mailbox: {mailbox['address']} ({mailbox['oversight_mode']})")

# Send an email
result = mm.send_email(
    mailbox["id"],
    to=["recipient@example.com"],
    subject="Hello from my AI agent",
    markdown="This email was composed and sent by an AI agent using **MultiMail**.\n\nThe agent is operating under human oversight.",
)
print(f"Email {result['id']} — status: {result['status']}")

# If gated_send, check pending approvals
if mailbox["oversight_mode"] == "gated_send":
    pending = mm.list_pending()
    print(f"{len(pending)} email(s) awaiting approval")
