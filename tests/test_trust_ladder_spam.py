"""Tests for the trust-ladder (oversight upgrade) and spam-screening client methods.

These exercise the four methods added for API parity (GHST-862): report_spam, not_spam,
request_upgrade, apply_upgrade — on both the sync and async clients. Endpoints and request
shapes are pinned to the real worker handlers in src/workers/api.ts:
  POST /v1/emails/{id}/report-spam   -> {id, status: 'spam_quarantined', user_label: 'spam'}
  POST /v1/emails/{id}/not-spam      -> {id, status: 'unread', user_label: 'not_spam'}
  POST /v1/mailboxes/{id}/request-upgrade  body {target_mode} -> {status: 'upgrade_requested'}
  POST /v1/mailboxes/{id}/upgrade          body {code}        -> {status: 'upgraded'}
"""
import json

import httpx
import pytest
import respx

from multimail import AsyncMultiMail, MultiMail, MultiMailError, NotFoundError

BASE = "https://api.multimail.dev"
KEY = "mm_live_test_key"


# ── Spam screening ────────────────────────────────────────────

@respx.mock
def test_report_spam_posts_no_body_and_parses_result():
    route = respx.post(f"{BASE}/v1/emails/em_1/report-spam").mock(
        return_value=httpx.Response(
            200, json={"id": "em_1", "status": "spam_quarantined", "user_label": "spam"}
        )
    )
    with MultiMail(KEY, base_url=BASE) as c:
        out = c.report_spam("em_1")
    assert route.called
    assert out == {"id": "em_1", "status": "spam_quarantined", "user_label": "spam"}
    # report-spam takes no request body
    assert route.calls.last.request.content in (b"", b"null")


@respx.mock
def test_not_spam_restores_to_inbox():
    route = respx.post(f"{BASE}/v1/emails/em_2/not-spam").mock(
        return_value=httpx.Response(
            200, json={"id": "em_2", "status": "unread", "user_label": "not_spam"}
        )
    )
    with MultiMail(KEY, base_url=BASE) as c:
        out = c.not_spam("em_2")
    assert route.called
    assert out["status"] == "unread"
    assert out["user_label"] == "not_spam"


# ── Trust ladder (oversight upgrade) ──────────────────────────

@respx.mock
def test_request_upgrade_sends_target_mode():
    route = respx.post(f"{BASE}/v1/mailboxes/mb_1/request-upgrade").mock(
        return_value=httpx.Response(200, json={"status": "upgrade_requested"})
    )
    with MultiMail(KEY, base_url=BASE) as c:
        out = c.request_upgrade("mb_1", "monitored")
    assert out["status"] == "upgrade_requested"
    assert json.loads(route.calls.last.request.content) == {"target_mode": "monitored"}


@respx.mock
def test_apply_upgrade_sends_code():
    route = respx.post(f"{BASE}/v1/mailboxes/mb_1/upgrade").mock(
        return_value=httpx.Response(200, json={"status": "upgraded"})
    )
    with MultiMail(KEY, base_url=BASE) as c:
        out = c.apply_upgrade("mb_1", "ABC123")
    assert out["status"] == "upgraded"
    assert json.loads(route.calls.last.request.content) == {"code": "ABC123"}


# ── Error mapping ─────────────────────────────────────────────

@respx.mock
def test_report_spam_404_maps_to_notfound():
    respx.post(f"{BASE}/v1/emails/missing/report-spam").mock(
        return_value=httpx.Response(404, json={"error": "Email not found"})
    )
    with MultiMail(KEY, base_url=BASE) as c:
        with pytest.raises(NotFoundError):
            c.report_spam("missing")


@respx.mock
def test_request_upgrade_403_maps_to_error():
    respx.post(f"{BASE}/v1/mailboxes/mb_1/request-upgrade").mock(
        return_value=httpx.Response(403, json={"error": "Requires send scope"})
    )
    with MultiMail(KEY, base_url=BASE) as c:
        with pytest.raises(MultiMailError):
            c.request_upgrade("mb_1", "monitored")


# ── Async parity ──────────────────────────────────────────────

@respx.mock
async def test_async_spam_and_trust_ladder():
    respx.post(f"{BASE}/v1/emails/em_1/report-spam").mock(
        return_value=httpx.Response(
            200, json={"id": "em_1", "status": "spam_quarantined", "user_label": "spam"}
        )
    )
    req = respx.post(f"{BASE}/v1/mailboxes/mb_1/request-upgrade").mock(
        return_value=httpx.Response(200, json={"status": "upgrade_requested"})
    )
    appl = respx.post(f"{BASE}/v1/mailboxes/mb_1/upgrade").mock(
        return_value=httpx.Response(200, json={"status": "upgraded"})
    )
    async with AsyncMultiMail(KEY, base_url=BASE) as c:
        spam = await c.report_spam("em_1")
        r1 = await c.request_upgrade("mb_1", "gated_send")
        r2 = await c.apply_upgrade("mb_1", "CODE9")
    assert spam["status"] == "spam_quarantined"
    assert r1["status"] == "upgrade_requested"
    assert r2["status"] == "upgraded"
    assert json.loads(req.calls.last.request.content) == {"target_mode": "gated_send"}
    assert json.loads(appl.calls.last.request.content) == {"code": "CODE9"}
