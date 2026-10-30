import json

import pytest

from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport, DiagnosticSeverity
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus
from vpn_doctor.services.gateway_service import GatewayService
from vpn_doctor.services.settings_service import SettingsService


@pytest.fixture
def controller(tmp_path):
    controller = ApplicationController()
    controller.settings = SettingsService(profile_path=tmp_path / "missing.json")
    controller.gateways = GatewayService(path=tmp_path / "gateways.json", helper=tmp_path / "no-helper")
    return controller


def run_json(controller, capsys, *argv):
    code = controller.run(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_json_flag_is_accepted_before_and_after_the_command(controller, capsys):
    assert run_json(controller, capsys, "--json", "profiles")[1] == run_json(
        controller, capsys, "profiles", "--json"
    )[1]


def test_version_json(controller, capsys):
    code, data = run_json(controller, capsys, "--json", "--version")

    assert code == 0
    assert set(data) == {"version"}


def test_profiles_json_never_exposes_user_name_or_certificate_paths(controller, capsys, monkeypatch):
    profile = VPNProfile(
        name="Office",
        backend="openfortivpn",
        host="vpn.example.com",
        port=443,
        username="demo-user",
        user_cert="/etc/openfortivpn/user.crt",
        user_key="/etc/openfortivpn/user.key",
    )
    monkeypatch.setattr(controller, "profiles", lambda: [profile])

    code, data = run_json(controller, capsys, "profiles", "--json")

    assert code == 0
    assert data == {
        "profiles": [
            {
                "name": "Office",
                "backend": "openfortivpn",
                "managed_by": "vpn-doctor",
                "vpn_type": None,
                "host": "vpn.example.com",
                "port": 443,
            }
        ]
    }


def test_status_json(controller, capsys):
    code, data = run_json(controller, capsys, "status", "--json")

    assert code == 0
    assert data["profile"] == "Demo Fortinet VPN"
    assert data["status"]["state"] == "disconnected"
    assert set(data["status"]) == {
        "backend",
        "state",
        "message",
        "suggestion",
        "prompt",
        "vpn_ip",
        "connected_seconds",
    }


def test_diagnose_json_keeps_the_exit_code(controller, capsys, monkeypatch):
    item = DiagnosticItem(
        "Gateway", False, "Unreachable", "Check the address", DiagnosticSeverity.ERROR
    )
    report = DiagnosticReport.from_items("1 problem", [item])
    monkeypatch.setattr(controller.backend_manager, "diagnose", lambda profile: report)

    code, data = run_json(controller, capsys, "diagnose", "--json")

    assert code == 1
    assert data["report"] == {
        "summary": "1 problem",
        "success": False,
        "items": [
            {
                "name": "Gateway",
                "success": False,
                "severity": "error",
                "message": "Unreachable",
                "suggestion": "Check the address",
            }
        ],
    }


def test_unknown_profile_is_a_json_error(controller, capsys):
    code, data = run_json(controller, capsys, "status", "--profile", "nope", "--json")

    assert code == 2
    assert data == {"error": "Unknown profile: nope"}


def test_connect_dry_run_json_returns_the_command(controller, capsys):
    code, data = run_json(controller, capsys, "connect", "--dry-run", "--json")

    assert code == 0
    assert data["profile"] == "Demo Fortinet VPN"
    assert isinstance(data["command"], list)


def test_connect_wait_json_collects_logs_into_the_result(controller, capsys, monkeypatch):
    def fake_connect(profile, on_log, **kwargs):
        on_log("Tunnel is up")
        return VPNStatus(backend="openfortivpn", state=VPNConnectionState.CONNECTED)

    monkeypatch.setattr(controller.backend_manager, "connect", fake_connect)

    code, data = run_json(controller, capsys, "connect", "--wait", "--json")

    assert code == 0
    assert data["status"]["state"] == "connected"
    assert data["logs"] == ["Tunnel is up"]


def test_conflicts_json_without_conflict(controller, capsys, monkeypatch):
    monkeypatch.setattr(controller, "network_conflicts", list)

    code, data = run_json(controller, capsys, "conflicts", "--json")

    assert code == 0
    assert data == {"report": {"summary": "Network conflicts", "success": True, "items": []}}


def test_gateways_json_without_helper(controller, capsys):
    code, data = run_json(controller, capsys, "gateways", "--json")

    assert code == 0
    assert data == {"enforced": False, "gateways": []}


def test_approve_gateway_json_without_helper_fails(controller, capsys):
    code, data = run_json(controller, capsys, "approve-gateway", "--json")

    assert code == 1
    assert data == {"success": False, "message": "The VPN Doctor helper is not installed"}


def test_revoke_gateway_json_rejects_bad_argument(controller, capsys):
    code, data = run_json(controller, capsys, "revoke-gateway", "nohost", "--json")

    assert code == 2
    assert data == {"error": "Expected HOST:PORT"}


def test_rdp_json_with_missing_log_file(controller, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "vpn_doctor.core.controller.probe_rdp",
        lambda host, port: DiagnosticReport.from_items("RDP", []),
    )

    code, data = run_json(
        controller, capsys, "rdp", "rdp.example.com", "--log", str(tmp_path / "none.log"), "--json"
    )

    assert code == 2
    assert data["error"].startswith("Cannot read")


def test_rdp_json(controller, capsys, monkeypatch):
    monkeypatch.setattr(
        "vpn_doctor.core.controller.probe_rdp",
        lambda host, port: DiagnosticReport.from_items("RDP", []),
    )

    code, data = run_json(controller, capsys, "rdp", "rdp.example.com", "--json")

    assert code == 0
    assert data == {
        "host": "rdp.example.com",
        "port": 3389,
        "probe": {"summary": "RDP", "success": True, "items": []},
        "log_analysis": None,
    }


def test_forget_secrets_json(controller, capsys):
    code, data = run_json(controller, capsys, "forget-secrets", "--json")

    assert code == 0
    assert data["success"] is True
    assert data["profile"] == "Demo Fortinet VPN"
