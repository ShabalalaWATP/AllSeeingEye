"""Administrator input schemas advertise exactly the roles they accept."""

import pytest
from pydantic import ValidationError

from ase.api.schemas import ApproveIn, UpdateUserIn, UserOut
from ase.domain.users import Role


@pytest.mark.parametrize("model", [ApproveIn, UpdateUserIn])
def test_assignable_role_schema_matches_validation(model: type[ApproveIn | UpdateUserIn]) -> None:
    schema = model.model_json_schema()
    role = schema["properties"]["role"]
    alternatives = role.get("anyOf", [role])
    values: set[str] = set()
    for alternative in alternatives:
        resolved = alternative
        if "$ref" in alternative:
            resolved = schema["$defs"][alternative["$ref"].rsplit("/", 1)[1]]
        values.update(resolved.get("enum", []))
    assert values == {"user", "admin"}
    for value in values:
        assert model.model_validate({"role": value}).role is Role(value)
    with pytest.raises(ValidationError):
        model.model_validate({"role": "manager"})


def test_legacy_manager_remains_readable_in_account_output() -> None:
    assert UserOut.model_json_schema()["$defs"]["Role"]["enum"] == ["user", "manager", "admin"]


def test_role_defaults_and_nullable_update_are_preserved() -> None:
    assert ApproveIn().role is Role.USER
    assert UpdateUserIn().role is None
    assert UpdateUserIn.model_validate({"role": None}).role is None
