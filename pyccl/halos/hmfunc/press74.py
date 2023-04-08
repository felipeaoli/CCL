from ...base import warn_api
from ...base.parameters import physical_constants as const
from ..halo_model_base import MassFunc
import numpy as np


__all__ = ("MassFuncPress74",)


class MassFuncPress74(MassFunc):
    """ Implements mass function described in 1974ApJ...187..425P.
    This parametrization is only valid for 'fof' masses.

    Args:
        mass_def (:class:`~pyccl.halos.massdef.MassDef` or str):
            a mass definition object, or a name string.
            This parametrization accepts FoF masses only.
            The default is 'fof'.
        mass_def_strict (bool): if False, consistency of the mass
            definition will be ignored.
    """
    name = 'Press74'

    @warn_api
    def __init__(self, *,
                 mass_def="fof",
                 mass_def_strict=True):
        super().__init__(mass_def=mass_def, mass_def_strict=mass_def_strict)
        self._norm = np.sqrt(2/np.pi)

    def _check_mass_def_strict(self, mass_def):
        return mass_def.Delta != "fof"

    def _get_fsigma(self, cosmo, sigM, a, lnM):
        delta_c = const.DELTA_C
        nu = delta_c/sigM
        return self._norm * nu * np.exp(-0.5 * nu**2)
