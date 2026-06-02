# multimail

Python SDK for the [MultiMail API](https://multimail.dev) — email infrastructure for AI agents.

## Installation

```bash
pip install multimail
```

## Quick Start

```python
from multimail import MultiMail

mm = MultiMail("MULTIMAIL_API_KEY")

# List mailboxes
mailboxes = mm.list_mailboxes()
mailbox_id = mailboxes[0]["id"]

# Enable signed AI disclosure on a mailbox when needed
mm.update_mailbox(mailbox_id, ai_disclosure=True)

# Send an email
result = mm.send_email(
    mailbox_id,
    to=["recipient@example.com"],
    subject="Hello from my agent",
    markdown="This email was sent by an AI agent using **MultiMail**.",
)
print(result)  # {"id": "...", "status": "pending_scan", "thread_id": "..."}

# Check inbox
emails = mm.list_emails(mailbox_id, direction="inbound")

# Read a specific email
email = mm.get_email(mailbox_id, emails["emails"][0]["id"])
print(email["subject"], email["text_body"])
```

## Async Support

```python
from multimail import AsyncMultiMail

async with AsyncMultiMail("MULTIMAIL_API_KEY") as mm:
    mailboxes = await mm.list_mailboxes()
    await mm.update_mailbox(mailboxes[0]["id"], ai_disclosure=True)
    result = await mm.send_email(
        mailboxes[0]["id"],
        to=["recipient@example.com"],
        subject="Async email",
        markdown="Sent asynchronously!",
    )
```

## Oversight & Approval

MultiMail supports graduated oversight modes. When a mailbox uses `gated_send`, emails require human approval:

```python
# List emails waiting for approval
pending = mm.list_pending()

# Approve or reject
mm.decide(pending[0]["id"], "approve")
mm.decide(pending[1]["id"], "reject", reason="Not relevant")
```

## Compliance

MultiMail handles regulatory compliance at the infrastructure layer — no SDK-side code changes needed:

- **EU AI Act Article 50**: Every AI-sent email includes a cryptographically signed `ai_generated` disclosure in the `X-MultiMail-Identity` header when `ai_disclosure` is enabled on the mailbox
- **38 MCP tools**: The hosted and local MCP server expose 38 tools on top of the same compliance-aware delivery infrastructure
- **US State Laws**: Maine, New York, California, Illinois — AI disclosure built into email delivery
- **CAN-SPAM**: Unsubscribe headers and physical address footers on all outbound email
- **Formally Verified**: Lean 4 proofs of identity header tamper evidence

See [multimail.dev/use-cases/eu-ai-act-email-compliance](https://multimail.dev/use-cases/eu-ai-act-email-compliance) for details.

## All Methods

### Account
- `get_account()` / `update_account(**fields)` / `delete_account()`

### Mailboxes
- `list_mailboxes()` / `create_mailbox(address, display_name, oversight_mode=..., ai_disclosure=False)` / `update_mailbox(id, **fields)` / `delete_mailbox(id)`

### Emails
- `list_emails(mailbox_id)` / `get_email(mailbox_id, email_id)` / `send_email(mailbox_id, to=, subject=, markdown=)` / `reply_email(mailbox_id, email_id, markdown=)` / `cancel_email(mailbox_id, email_id)` / `get_thread(mailbox_id, thread_id)` / `download_attachment(mailbox_id, email_id, filename)`

### Tags
- `get_tags(mailbox_id, email_id)` / `set_tags(mailbox_id, email_id, tags)` / `delete_tag(mailbox_id, email_id, key)`

### Contacts
- `list_contacts(q=)` / `add_contact(email, name=)` / `delete_contact(contact_id)`

### Oversight
- `list_pending()` / `decide(email_id, action, reason=)`

### API Keys
- `list_api_keys()` / `create_api_key(name, scopes=)` / `revoke_api_key(key_id)`

### Webhooks
- `list_webhooks()` / `create_webhook(url, events, secret=)` / `delete_webhook(webhook_id)`

### Domains
- `list_domains()` / `add_domain(domain)` / `verify_domain(domain_id)` / `delete_domain(domain_id)`

### Suppression
- `list_suppressions()` / `remove_suppression(address)`

### Usage & Audit
- `get_usage()` / `get_audit_log(limit=)`

## Error Handling

```python
from multimail import MultiMail, AuthenticationError, RateLimitError

mm = MultiMail("MULTIMAIL_API_KEY")
try:
    mm.send_email(mailbox_id, to=["test@example.com"], subject="Hi", markdown="Hello")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
```

## Links

- [MultiMail](https://multimail.dev) — Homepage
- [API Docs](https://multimail.dev/docs) — Full API reference
- [MCP Server](https://www.npmjs.com/package/@multimail/mcp-server) — For Claude, Cursor, and other MCP clients
