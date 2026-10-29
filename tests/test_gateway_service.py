import json

import pytest

from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser, ParsedLogKind
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.services import gateway_service
from vpn_doctor.services.gateway_service import ApprovedGateway, GatewayService

FINGERPRINT = "ab" * 32
FORTI = VPNProfile(
    name="Forti",
    backend="openfortivpn",
    host="VPN.example.com",
    port=443,
    trusted_cert=FINGERPRINT.upper(),
)
OFFICE = VPNProfile(name="Office", backend="networkmanager", nm_uuid="1111")


@pytest.fixture
def service(tmp_path, monkeypatch):
    helper = tmp_path / "vpn-doctor-helper"
    helper.write_text('#!/bin/sh\nread request\necho "approved $request"\n')
    helper.chmod(0o755)
    # Never call the real pkexec from tests.
    monkeypatch.setattr(
        gateway_service, "helper_command", lambda path, action="connect": (str(path), action)
    )
    return GatewayService(path=tmp_path / "gateways.json", helper=helper)


def write_approved(service, *gateways):
    service.path.write_text(json.dumps({"gateways": list(gateways)}))


def test_unapproved_gateway_needs_approval(service):
    assert service.needs_approval(FORTI)
    assert not service.needs_approval(OFFICE)


def test_approved_gateway_matches_host_port_and_certificate(service):
    write_approved(service, {"host": "vpn.example.com", "port": 443, "trusted_cert": FINGERPRINT})

    assert service.is_approved(FORTI)
    assert not service.needs_approval(FORTI)
    assert service.approved() == [ApprovedGateway("vpn.example.com", 443, FINGERPRINT)]


def test_changed_certificate_needs_a_new_approval(service):
    write_approved(service, {"host": "vpn.example.com", "port": 443, "trusted_cert": "cd" * 32})

    assert service.needs_approval(FORTI)


def test_no_approval_without_the_installed_helper(tmp_path):
    service = GatewayService(path=tmp_path / "gateways.json", helper=tmp_path / "missing")

    assert not service.enforced
    assert not service.needs_approval(FORTI)


def test_approve_sends_only_gateway_fields(service):
    ok, message = service.approve(FORTI)

    assert ok
    sent = json.loads(message.removeprefix("approved "))
    assert sent == {"host": "VPN.example.com", "port": 443, "trusted_cert": FINGERPRINT.upper()}


def test_parser_reports_unapproved_gateway():
    parsed = OpenFortiVPNLogParser().parse(
        "ERROR:  vpn-doctor-helper refused the request: gateway not approved: evil.example.com:443"
    )
    assert parsed.kind == ParsedLogKind.GATEWAY_NOT_APPROVED
