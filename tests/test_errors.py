"""Typed error contract: codes, HTTP status mapping and the JSON envelope.

Every failure the service can hand a caller is represented here, so a caller
can branch on the machine-readable code without parsing English.
"""
from __future__ import annotations

from easylpac.errors import (
    AppError,
    BadRequest,
    Conflict,
    Forbidden,
    NotFound,
    PayloadTooLarge,
    RateLimited,
    ServiceUnavailable,
    Unauthorized,
    error_payload,
)


def test_every_error_carries_a_stable_code_and_status():
    assert [
        (BadRequest.status_code, BadRequest.code),
        (Unauthorized.status_code, Unauthorized.code),
        (Forbidden.status_code, Forbidden.code),
        (NotFound.status_code, NotFound.code),
        (Conflict.status_code, Conflict.code),
        (PayloadTooLarge.status_code, PayloadTooLarge.code),
        (RateLimited.status_code, RateLimited.code),
        (ServiceUnavailable.status_code, ServiceUnavailable.code),
    ] == [
        (400, "bad_request"),
        (401, "unauthorized"),
        (403, "forbidden"),
        (404, "not_found"),
        (409, "conflict"),
        (413, "payload_too_large"),
        (429, "rate_limited"),
        (503, "service_unavailable"),
    ]


def test_the_base_error_falls_back_to_its_own_docstring():
    error = AppError()
    assert error.message == AppError.__doc__
    assert (error.status_code, error.code) == (500, "internal_error")


def test_to_dict_omits_details_when_there_is_no_context():
    assert BadRequest("bad input").to_dict() == {"error": "bad_request", "message": "bad input"}


def test_to_dict_includes_context_when_supplied():
    payload = NotFound("gone", resource="profile", iccid="8914").to_dict()
    assert payload["error"] == "not_found"
    assert payload["details"] == {"resource": "profile", "iccid": "8914"}


def test_repr_is_debuggable():
    assert repr(BadRequest("nope", field="address")) == "BadRequest('nope', {'field': 'address'})"


def test_error_payload_is_the_canonical_envelope():
    assert error_payload("bad_request", "nope") == {"error": "bad_request", "message": "nope"}


def test_error_payload_attaches_details():
    assert error_payload("bad_request", "nope", field="x")["details"] == {"field": "x"}
