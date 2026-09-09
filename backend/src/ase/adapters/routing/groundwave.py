"""NTIA LFMF 1.1 native solver with explicit antenna reference normalisation.

NTIA's native field calculation uses a 4.77 dBi transmitting antenna. Its basic
transmission loss removes antenna gains and power, so the user's received-power
budget applies arbitrary gains and combined losses to that returned loss.
No terrain, skywave or empirical range multiplier is introduced here.
"""

from importlib import import_module
from math import isfinite, log10

from ase.domain.groundwave import GroundwaveInput, GroundwaveSample


class NtiaGroundwaveSolver:
    def calculate(self, inputs: GroundwaveInput) -> tuple[GroundwaveSample, ...]:
        # Lazy import keeps unrelated app features usable on unsupported platforms.
        native = import_module("ITS.Propagation.LFMF")

        budget_dbm = (
            30
            + 10 * log10(inputs.tx_power_w)
            + inputs.tx_gain_dbi
            + inputs.rx_gain_dbi
            - inputs.system_loss_db
        )
        samples: list[GroundwaveSample] = []
        for index in range(inputs.sample_count):
            # Start at 1 km, outside two wavelengths even at the study's 1.6 MHz floor.
            distance = inputs.max_distance_km ** (index / (inputs.sample_count - 1))
            result = native.LFMF(
                inputs.tx_height_m,
                inputs.rx_height_m,
                inputs.frequency_mhz,
                inputs.tx_power_w,
                inputs.surface_refractivity,
                distance,
                inputs.relative_permittivity,
                inputs.conductivity_sm,
                native.Polarization.Vertical,
            )
            loss, field = float(result.A_btl__db), float(result.E__dBuVm)
            if not isfinite(loss) or not isfinite(field) or result.method not in (0, 1):
                raise ValueError("The native groundwave solver returned an invalid result.")
            samples.append(
                GroundwaveSample(
                    distance,
                    loss,
                    field,
                    budget_dbm - loss,
                    "flat_earth" if result.method == 0 else "residue_series",
                )
            )
        return tuple(samples)
