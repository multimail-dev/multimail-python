"""Sync and async HTTP clients for the MultiMail API."""

from __future__ import annotations
from typing import Any
import httpx

from multimail.exceptions import (
    MultiMailError, AuthenticationError, NotFoundError, RateLimitError, ValidationError,
)

DEFAULT_BASE_URL = "https://api.multimail.dev"
DEFAULT_TIMEOUT = 30.0


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    msg = body.get("error", resp.text) if isinstance(body, dict) else str(body)
    if resp.status_code == 401:
        raise AuthenticationError(msg, status_code=401, body=body)
    if resp.status_code == 404:
        raise NotFoundError(msg, status_code=404, body=body)
    if resp.status_code == 422:
        raise ValidationError(msg, status_code=422, body=body)
    if resp.status_code == 429:
        retry = resp.headers.get("retry-after")
        raise RateLimitError(msg, status_code=429, body=body, retry_after=float(retry) if retry else None)
    raise MultiMailError(msg, status_code=resp.status_code, body=body)


class MultiMail:
    """Synchronous MultiMail API client."""

    def __init__(self, api_key: str, *, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = self._client.request(method, path, **kwargs)
        _raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ── Account ──────────────────────────────────────────────

    def get_account(self) -> dict:
        return self._request("GET", "/v1/account")

    def update_account(self, **fields) -> dict:
        return self._request("PATCH", "/v1/account", json=fields)

    def delete_account(self) -> None:
        self._request("DELETE", "/v1/account")

    # ── Mailboxes ────────────────────────────────────────────

    def list_mailboxes(self) -> list[dict]:
        return self._request("GET", "/v1/mailboxes")["mailboxes"]

    def create_mailbox(self, address: str, display_name: str, *, oversight_mode: str = "gated_send", **kwargs) -> dict:
        return self._request("POST", "/v1/mailboxes", json={
            "address": address, "display_name": display_name, "oversight_mode": oversight_mode, **kwargs,
        })

    def update_mailbox(self, mailbox_id: str, **fields) -> dict:
        return self._request("PATCH", f"/v1/mailboxes/{mailbox_id}", json=fields)

    def delete_mailbox(self, mailbox_id: str) -> None:
        self._request("DELETE", f"/v1/mailboxes/{mailbox_id}")

    # ── Emails ───────────────────────────────────────────────

    def list_emails(self, mailbox_id: str, *, limit: int = 50, offset: int = 0, direction: str | None = None) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if direction:
            params["direction"] = direction
        return self._request("GET", f"/v1/mailboxes/{mailbox_id}/emails", params=params)

    def get_email(self, mailbox_id: str, email_id: str) -> dict:
        return self._request("GET", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}")

    def send_email(self, mailbox_id: str, *, to: list[str], subject: str, markdown: str,
                   cc: list[str] | None = None, bcc: list[str] | None = None,
                   attachments: list[dict] | None = None, idempotency_key: str | None = None) -> dict:
        body: dict = {"to": to, "subject": subject, "markdown": markdown}
        if cc:
            body["cc"] = cc
        if bcc:
            body["bcc"] = bcc
        if attachments:
            body["attachments"] = attachments
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        return self._request("POST", f"/v1/mailboxes/{mailbox_id}/send", json=body)

    def reply_email(self, mailbox_id: str, email_id: str, *, markdown: str,
                    cc: list[str] | None = None, bcc: list[str] | None = None,
                    attachments: list[dict] | None = None) -> dict:
        body: dict = {"markdown": markdown}
        if cc:
            body["cc"] = cc
        if bcc:
            body["bcc"] = bcc
        if attachments:
            body["attachments"] = attachments
        return self._request("POST", f"/v1/mailboxes/{mailbox_id}/reply/{email_id}", json=body)

    def cancel_email(self, mailbox_id: str, email_id: str) -> dict:
        return self._request("POST", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/cancel")

    def get_thread(self, mailbox_id: str, thread_id: str) -> dict:
        return self._request("GET", f"/v1/mailboxes/{mailbox_id}/threads/{thread_id}")

    def download_attachment(self, mailbox_id: str, email_id: str, filename: str) -> bytes:
        resp = self._client.get(f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/attachments/{filename}")
        _raise_for_status(resp)
        return resp.content

    def report_spam(self, email_id: str) -> dict:
        """Quarantine an email as spam. Returns {id, status: 'spam_quarantined', user_label: 'spam'}."""
        return self._request("POST", f"/v1/emails/{email_id}/report-spam")

    def not_spam(self, email_id: str) -> dict:
        """Clear a spam label, restoring the email to the inbox. Returns {id, status: 'unread', user_label: 'not_spam'}."""
        return self._request("POST", f"/v1/emails/{email_id}/not-spam")

    # ── Tags ─────────────────────────────────────────────────

    def get_tags(self, mailbox_id: str, email_id: str) -> dict:
        return self._request("GET", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/tags")

    def set_tags(self, mailbox_id: str, email_id: str, tags: dict[str, str]) -> dict:
        return self._request("PUT", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/tags", json={"tags": tags})

    def delete_tag(self, mailbox_id: str, email_id: str, key: str) -> None:
        self._request("DELETE", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/tags/{key}")

    # ── Contacts ─────────────────────────────────────────────

    def list_contacts(self, *, q: str | None = None) -> list[dict]:
        params = {"q": q} if q else {}
        return self._request("GET", "/v1/contacts", params=params)["contacts"]

    def add_contact(self, email: str, name: str | None = None, **fields) -> dict:
        body: dict = {"email": email}
        if name:
            body["name"] = name
        body.update(fields)
        return self._request("POST", "/v1/contacts", json=body)

    def delete_contact(self, contact_id: str) -> None:
        self._request("DELETE", f"/v1/contacts/{contact_id}")

    # ── Oversight ────────────────────────────────────────────

    def list_pending(self) -> list[dict]:
        return self._request("GET", "/v1/oversight/pending")["pending"]

    def decide(self, email_id: str, action: str, *, reason: str | None = None) -> dict:
        body: dict = {"email_id": email_id, "action": action}
        if reason:
            body["reason"] = reason
        return self._request("POST", "/v1/oversight/decide", json=body)

    def request_upgrade(self, mailbox_id: str, target_mode: str) -> dict:
        """Request an oversight-mode change (the trust ladder). Sends an approval code to the
        configured oversight email; the human shares it back to apply_upgrade(). target_mode is one
        of: read_only, gated_all, gated_send, monitored, autonomous. Returns {status: 'upgrade_requested', ...}."""
        return self._request("POST", f"/v1/mailboxes/{mailbox_id}/request-upgrade", json={"target_mode": target_mode})

    def apply_upgrade(self, mailbox_id: str, code: str) -> dict:
        """Apply a previously-requested oversight upgrade using the code the human shared back.
        Returns {status: 'upgraded', ...}. There is no automatic grant — the code is required."""
        return self._request("POST", f"/v1/mailboxes/{mailbox_id}/upgrade", json={"code": code})

    # ── API Keys ─────────────────────────────────────────────

    def list_api_keys(self) -> list[dict]:
        return self._request("GET", "/v1/api-keys")["api_keys"]

    def create_api_key(self, name: str, scopes: list[str] | None = None) -> dict:
        body: dict = {"name": name}
        if scopes:
            body["scopes"] = scopes
        return self._request("POST", "/v1/api-keys", json=body)

    def revoke_api_key(self, key_id: str) -> None:
        self._request("DELETE", f"/v1/api-keys/{key_id}")

    # ── Webhooks ─────────────────────────────────────────────

    def list_webhooks(self) -> list[dict]:
        return self._request("GET", "/v1/webhooks")["webhooks"]

    def create_webhook(self, url: str, events: list[str], *, secret: str | None = None) -> dict:
        body: dict = {"url": url, "events": events}
        if secret:
            body["secret"] = secret
        return self._request("POST", "/v1/webhooks", json=body)

    def delete_webhook(self, webhook_id: str) -> None:
        self._request("DELETE", f"/v1/webhooks/{webhook_id}")

    # ── Domains ──────────────────────────────────────────────

    def list_domains(self) -> list[dict]:
        return self._request("GET", "/v1/domains")["domains"]

    def add_domain(self, domain: str) -> dict:
        return self._request("POST", "/v1/domains", json={"domain": domain})

    def verify_domain(self, domain_id: str) -> dict:
        return self._request("POST", f"/v1/domains/{domain_id}/verify")

    def delete_domain(self, domain_id: str) -> None:
        self._request("DELETE", f"/v1/domains/{domain_id}")

    # ── Suppression ──────────────────────────────────────────

    def list_suppressions(self) -> list[dict]:
        return self._request("GET", "/v1/suppression")["suppressions"]

    def remove_suppression(self, address: str) -> None:
        self._request("DELETE", f"/v1/suppression/{address}")

    # ── Usage & Audit ────────────────────────────────────────

    def get_usage(self) -> dict:
        return self._request("GET", "/v1/usage")

    def get_audit_log(self, *, limit: int = 100) -> list[dict]:
        return self._request("GET", "/v1/audit-log", params={"limit": limit})["entries"]


class AsyncMultiMail:
    """Asynchronous MultiMail API client."""

    def __init__(self, api_key: str, *, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = await self._client.request(method, path, **kwargs)
        _raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ── Account ──────────────────────────────────────────────

    async def get_account(self) -> dict:
        return await self._request("GET", "/v1/account")

    async def update_account(self, **fields) -> dict:
        return await self._request("PATCH", "/v1/account", json=fields)

    async def delete_account(self) -> None:
        await self._request("DELETE", "/v1/account")

    # ── Mailboxes ────────────────────────────────────────────

    async def list_mailboxes(self) -> list[dict]:
        return (await self._request("GET", "/v1/mailboxes"))["mailboxes"]

    async def create_mailbox(self, address: str, display_name: str, *, oversight_mode: str = "gated_send", **kwargs) -> dict:
        return await self._request("POST", "/v1/mailboxes", json={
            "address": address, "display_name": display_name, "oversight_mode": oversight_mode, **kwargs,
        })

    async def update_mailbox(self, mailbox_id: str, **fields) -> dict:
        return await self._request("PATCH", f"/v1/mailboxes/{mailbox_id}", json=fields)

    async def delete_mailbox(self, mailbox_id: str) -> None:
        await self._request("DELETE", f"/v1/mailboxes/{mailbox_id}")

    # ── Emails ───────────────────────────────────────────────

    async def list_emails(self, mailbox_id: str, *, limit: int = 50, offset: int = 0, direction: str | None = None) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if direction:
            params["direction"] = direction
        return await self._request("GET", f"/v1/mailboxes/{mailbox_id}/emails", params=params)

    async def get_email(self, mailbox_id: str, email_id: str) -> dict:
        return await self._request("GET", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}")

    async def send_email(self, mailbox_id: str, *, to: list[str], subject: str, markdown: str,
                         cc: list[str] | None = None, bcc: list[str] | None = None,
                         attachments: list[dict] | None = None, idempotency_key: str | None = None) -> dict:
        body: dict = {"to": to, "subject": subject, "markdown": markdown}
        if cc:
            body["cc"] = cc
        if bcc:
            body["bcc"] = bcc
        if attachments:
            body["attachments"] = attachments
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        return await self._request("POST", f"/v1/mailboxes/{mailbox_id}/send", json=body)

    async def reply_email(self, mailbox_id: str, email_id: str, *, markdown: str,
                          cc: list[str] | None = None, bcc: list[str] | None = None,
                          attachments: list[dict] | None = None) -> dict:
        body: dict = {"markdown": markdown}
        if cc:
            body["cc"] = cc
        if bcc:
            body["bcc"] = bcc
        if attachments:
            body["attachments"] = attachments
        return await self._request("POST", f"/v1/mailboxes/{mailbox_id}/reply/{email_id}", json=body)

    async def cancel_email(self, mailbox_id: str, email_id: str) -> dict:
        return await self._request("POST", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/cancel")

    async def get_thread(self, mailbox_id: str, thread_id: str) -> dict:
        return await self._request("GET", f"/v1/mailboxes/{mailbox_id}/threads/{thread_id}")

    async def download_attachment(self, mailbox_id: str, email_id: str, filename: str) -> bytes:
        resp = await self._client.get(f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/attachments/{filename}")
        _raise_for_status(resp)
        return resp.content

    async def report_spam(self, email_id: str) -> dict:
        """Quarantine an email as spam. Returns {id, status: 'spam_quarantined', user_label: 'spam'}."""
        return await self._request("POST", f"/v1/emails/{email_id}/report-spam")

    async def not_spam(self, email_id: str) -> dict:
        """Clear a spam label, restoring the email to the inbox. Returns {id, status: 'unread', user_label: 'not_spam'}."""
        return await self._request("POST", f"/v1/emails/{email_id}/not-spam")

    # ── Tags ─────────────────────────────────────────────────

    async def get_tags(self, mailbox_id: str, email_id: str) -> dict:
        return await self._request("GET", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/tags")

    async def set_tags(self, mailbox_id: str, email_id: str, tags: dict[str, str]) -> dict:
        return await self._request("PUT", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/tags", json={"tags": tags})

    async def delete_tag(self, mailbox_id: str, email_id: str, key: str) -> None:
        await self._request("DELETE", f"/v1/mailboxes/{mailbox_id}/emails/{email_id}/tags/{key}")

    # ── Contacts ─────────────────────────────────────────────

    async def list_contacts(self, *, q: str | None = None) -> list[dict]:
        params = {"q": q} if q else {}
        return (await self._request("GET", "/v1/contacts", params=params))["contacts"]

    async def add_contact(self, email: str, name: str | None = None, **fields) -> dict:
        body: dict = {"email": email}
        if name:
            body["name"] = name
        body.update(fields)
        return await self._request("POST", "/v1/contacts", json=body)

    async def delete_contact(self, contact_id: str) -> None:
        await self._request("DELETE", f"/v1/contacts/{contact_id}")

    # ── Oversight ────────────────────────────────────────────

    async def list_pending(self) -> list[dict]:
        return (await self._request("GET", "/v1/oversight/pending"))["pending"]

    async def decide(self, email_id: str, action: str, *, reason: str | None = None) -> dict:
        body: dict = {"email_id": email_id, "action": action}
        if reason:
            body["reason"] = reason
        return await self._request("POST", "/v1/oversight/decide", json=body)

    async def request_upgrade(self, mailbox_id: str, target_mode: str) -> dict:
        """Request an oversight-mode change (the trust ladder). Sends an approval code to the
        configured oversight email; the human shares it back to apply_upgrade(). target_mode is one
        of: read_only, gated_all, gated_send, monitored, autonomous. Returns {status: 'upgrade_requested', ...}."""
        return await self._request("POST", f"/v1/mailboxes/{mailbox_id}/request-upgrade", json={"target_mode": target_mode})

    async def apply_upgrade(self, mailbox_id: str, code: str) -> dict:
        """Apply a previously-requested oversight upgrade using the code the human shared back.
        Returns {status: 'upgraded', ...}. There is no automatic grant — the code is required."""
        return await self._request("POST", f"/v1/mailboxes/{mailbox_id}/upgrade", json={"code": code})

    # ── API Keys ─────────────────────────────────────────────

    async def list_api_keys(self) -> list[dict]:
        return (await self._request("GET", "/v1/api-keys"))["api_keys"]

    async def create_api_key(self, name: str, scopes: list[str] | None = None) -> dict:
        body: dict = {"name": name}
        if scopes:
            body["scopes"] = scopes
        return await self._request("POST", "/v1/api-keys", json=body)

    async def revoke_api_key(self, key_id: str) -> None:
        await self._request("DELETE", f"/v1/api-keys/{key_id}")

    # ── Webhooks ─────────────────────────────────────────────

    async def list_webhooks(self) -> list[dict]:
        return (await self._request("GET", "/v1/webhooks"))["webhooks"]

    async def create_webhook(self, url: str, events: list[str], *, secret: str | None = None) -> dict:
        body: dict = {"url": url, "events": events}
        if secret:
            body["secret"] = secret
        return await self._request("POST", "/v1/webhooks", json=body)

    async def delete_webhook(self, webhook_id: str) -> None:
        await self._request("DELETE", f"/v1/webhooks/{webhook_id}")

    # ── Domains ──────────────────────────────────────────────

    async def list_domains(self) -> list[dict]:
        return (await self._request("GET", "/v1/domains"))["domains"]

    async def add_domain(self, domain: str) -> dict:
        return await self._request("POST", "/v1/domains", json={"domain": domain})

    async def verify_domain(self, domain_id: str) -> dict:
        return await self._request("POST", f"/v1/domains/{domain_id}/verify")

    async def delete_domain(self, domain_id: str) -> None:
        await self._request("DELETE", f"/v1/domains/{domain_id}")

    # ── Suppression ──────────────────────────────────────────

    async def list_suppressions(self) -> list[dict]:
        return (await self._request("GET", "/v1/suppression"))["suppressions"]

    async def remove_suppression(self, address: str) -> None:
        await self._request("DELETE", f"/v1/suppression/{address}")

    # ── Usage & Audit ────────────────────────────────────────

    async def get_usage(self) -> dict:
        return await self._request("GET", "/v1/usage")

    async def get_audit_log(self, *, limit: int = 100) -> list[dict]:
        return (await self._request("GET", "/v1/audit-log", params={"limit": limit}))["entries"]
