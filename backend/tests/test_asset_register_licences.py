"""Research cannot bypass map dataset policy through packaged register scans."""

from unittest.mock import Mock

from ase.adapters.research.asset_register import AssetRegisterProvider
from ase.domain.research import CollectionStatus
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from test_asset_register_research import DUBLIN, query


async def test_denied_registers_are_not_scanned(monkeypatch):
    scan = Mock(side_effect=AssertionError("Blocked register was read"))
    monkeypatch.setattr("ase.adapters.research.asset_register.scan_registers", scan)
    provider = AssetRegisterProvider(licences=SourceLicencePolicy((), commercial_use=True))
    result = await provider.collect(query(area=DUBLIN))
    assert result.items == ()
    assert result.attempts[0].status == CollectionStatus.UNSUPPORTED
    assert "licence terms" in result.attempts[0].explanation
    scan.assert_not_called()


async def test_only_permitted_register_classes_are_scanned(monkeypatch):
    scan = Mock(return_value=())
    monkeypatch.setattr("ase.adapters.research.asset_register.scan_registers", scan)
    licences = SourceLicencePolicy(
        (SourceLicence("map:data_centres", "allowed", True, "reference"),),
        commercial_use=True,
    )
    result = await AssetRegisterProvider(licences=licences).collect(query(area=DUBLIN))
    assert {entry.value for entry in scan.call_args.args[0]} == {"data_centres"}
    assert "Excluded due to licence terms" in result.attempts[0].explanation
