"""审批门测试"""
import os
import tempfile

import pytest

from root.left.app.left.src.core_mod.approval_gate import ApprovalGate
from root.left.app.left.src.utils_main.exceptions import SafetyBoundaryException


class TestApprovalGate:
    """审批门测试"""

    def test_auto_pass_non_destructive(self) -> None:
        gate = ApprovalGate({"mode": "auto_reject"})
        assert gate.check("shell", {"command": "echo hi"}) is True

    def test_auto_reject_destructive(self) -> None:
        gate = ApprovalGate({"mode": "auto_reject"})
        with pytest.raises(SafetyBoundaryException):
            gate.check("file_delete", {"path": "/tmp/x"})

    def test_auto_pass_mode(self) -> None:
        gate = ApprovalGate({"mode": "auto_pass"})
        assert gate.check("file_delete", {"path": "/tmp/x"}) is True

    def test_shell_destructive_keyword(self) -> None:
        gate = ApprovalGate({"mode": "auto_reject"})
        with pytest.raises(SafetyBoundaryException):
            gate.check("shell", {"command": "rm -rf /tmp/target"})

    def test_file_token_approval(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file_delete:/tmp/x")
            path = f.name
        try:
            gate = ApprovalGate({"mode": "file_token", "approval_file": path})
            assert gate.check("file_delete", {"path": "/tmp/x"}) is True
        finally:
            os.remove(path)

    def test_file_token_mismatch(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("other")
            path = f.name
        try:
            gate = ApprovalGate({"mode": "file_token", "approval_file": path})
            with pytest.raises(SafetyBoundaryException):
                gate.check("file_delete", {"path": "/tmp/x"})
        finally:
            os.remove(path)

    def test_custom_handler(self) -> None:
        gate = ApprovalGate({"mode": "custom", "handler": lambda _a, _p: True})
        assert gate.check("file_delete", {"path": "/tmp/x"}) is True

    def test_pending_mode(self) -> None:
        gate = ApprovalGate({"mode": "pending"})
        with pytest.raises(SafetyBoundaryException):
            gate.check("file_delete", {"path": "/tmp/x"})
