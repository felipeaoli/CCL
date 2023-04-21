"""Utility functions to analyze status and error messages passed from CCL, as
well as wrappers to automatically vectorize functions.
"""
__all__ = (
    "CLevelErrors", "IntegrationMethods", "check", "debug_mode",
    "get_pk_spline_lk", "get_pk_spline_a", "resample_array")

from enum import Enum
from typing import Iterable

import numpy as np

from . import CCLError, lib, spline_params
from .base.parameters.fftlog_params import extrap_types


NoneArr = np.array([])


class IntegrationMethods(Enum):
    QAG_QUAD = "qag_quad"
    SPLINE = "spline"


integ_types = {
    'qag_quad': lib.integration_qag_quad,
    'spline': lib.integration_spline}


# This is defined here instead of in `errors.py` because SWIG needs `CCLError`
# from `.errors`, resulting in a cyclic import.
CLevelErrors = {
    lib.CCL_ERROR_CLASS: 'CCL_ERROR_CLASS',
    lib.CCL_ERROR_INCONSISTENT: 'CCL_ERROR_INCONSISTENT',
    lib.CCL_ERROR_INTEG: 'CCL_ERROR_INTEG',
    lib.CCL_ERROR_LINSPACE: 'CCL_ERROR_LINSPACE',
    lib.CCL_ERROR_MEMORY: 'CCL_ERROR_MEMORY',
    lib.CCL_ERROR_ROOT: 'CCL_ERROR_ROOT',
    lib.CCL_ERROR_SPLINE: 'CCL_ERROR_SPLINE',
    lib.CCL_ERROR_SPLINE_EV: 'CCL_ERROR_SPLINE_EV',
    lib.CCL_ERROR_COMPUTECHI: 'CCL_ERROR_COMPUTECHI',
    lib.CCL_ERROR_MF: 'CCL_ERROR_MF',
    lib.CCL_ERROR_HMF_INTERP: 'CCL_ERROR_HMF_INTERP',
    lib.CCL_ERROR_PARAMETERS: 'CCL_ERROR_PARAMETERS',
    lib.CCL_ERROR_NU_INT: 'CCL_ERROR_NU_INT',
    lib.CCL_ERROR_EMULATOR_BOUND: 'CCL_ERROR_EMULATOR_BOUND',
    lib.CCL_ERROR_MISSING_CONFIG_FILE: 'CCL_ERROR_MISSING_CONFIG_FILE',
}


def check(status, cosmo=None):
    """Check the status returned by a ccllib function.

    Args:
        status (int or :obj:`~pyccl.core.error_types`):
            Flag or error describing the success of a function.
        cosmo (:class:`~pyccl.core.Cosmology`, optional):
            A Cosmology object.
    """
    # Check for normal status (no action required)
    if status == 0:
        return

    # Get status message from Cosmology object, if there is one
    if cosmo is not None:
        msg = cosmo.cosmo.status_message
    else:
        msg = ""

    # Check for known error status
    if status in CLevelErrors.keys():
        raise CCLError(f"Error {CLevelErrors[status]}: {msg}")

    # Check for unknown error
    if status != 0:
        raise CCLError(f"Error {status}: {msg}")


def debug_mode(debug):
    """Toggle debug mode on or off. If debug mode is on, the C backend is
    forced to print error messages as soon as they are raised, even if the
    flow of the program continues. This makes it easier to track down errors.

    If debug mode is off, the C code will not print errors, and the Python
    wrapper will raise the last error that was detected. If multiple errors
    were raised, all but the last will be overwritten within the C code, so the
    user will not necessarily be informed of the root cause of the error.

    Args:
        debug (bool): Switch debug mode on (True) or off (False).

    """
    if debug:
        lib.set_debug_policy(lib.CCL_DEBUG_MODE_ON)
    else:
        lib.set_debug_policy(lib.CCL_DEBUG_MODE_OFF)


# This function is not used anymore so we don't want Coveralls to
# include it, but we keep it in case it is needed at some point.
# def _vectorize_fn_simple(fn, fn_vec, x,
#                          returns_status=True):  # pragma: no cover
#     """Generic wrapper to allow vectorized (1D array) access to CCL
#     functions with one vector argument (but no dependence on cosmology).
#
#     Args:
#         fn (callable): Function with a single argument.
#         fn_vec (callable): Function that has a vectorized implementation in
#                            a .i file.
#         x (float or array_like): Argument to fn.
#         returns_stats (bool): Indicates whether fn returns a status.
#
#     """
#     status = 0
#     if isinstance(x, int):
#         x = float(x)
#     if isinstance(x, float):
#         # Use single-value function
#         if returns_status:
#             f, status = fn(x, status)
#         else:
#             f = fn(x)
#     elif isinstance(x, np.ndarray):
#         # Use vectorised function
#         if returns_status:
#             f, status = fn_vec(x, x.size, status)
#         else:
#             f = fn_vec(x, x.size)
#     else:
#         # Use vectorised function
#         if returns_status:
#             f, status = fn_vec(x, len(x), status)
#         else:
#             f = fn_vec(x, len(x))
#
#     # Check result and return
#     check(status)
#     return f


def _vectorize_fn(fn, fn_vec, cosmo, x, returns_status=True):
    """Generic wrapper to allow vectorized (1D array) access to CCL
    functions with one vector argument, with a cosmology dependence.

    Args:
        fn (callable): Function with a single argument.
        fn_vec (callable): Function that has a vectorized implementation in
                           a .i file.
        cosmo (ccl_cosmology or Cosmology): The input cosmology which gets
                                            converted to a ccl_cosmology.
        x (float or array_like): Argument to fn.
        returns_stats (bool): Indicates whether fn returns a status.

    """

    # Access ccl_cosmology object
    cosmo_in = cosmo
    cosmo = cosmo.cosmo

    status = 0

    if isinstance(x, int):
        x = float(x)
    if isinstance(x, float):
        # Use single-value function
        if returns_status:
            f, status = fn(cosmo, x, status)
        else:
            f = fn(cosmo, x)
    elif isinstance(x, np.ndarray):
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, x, x.size, status)
        else:
            f = fn_vec(cosmo, x, x.size)
    else:
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, x, len(x), status)
        else:
            f = fn_vec(cosmo, x, len(x))

    # Check result and return
    check(status, cosmo_in)
    return f


def _vectorize_fn3(fn, fn_vec, cosmo, x, n, returns_status=True):
    """Generic wrapper to allow vectorized (1D array) access to CCL
    functions with one vector argument and one integer argument,
    with a cosmology dependence.

    Args:
        fn (callable): Function with a single argument.
        fn_vec (callable): Function that has a vectorized implementation in
                           a .i file.
        cosmo (ccl_cosmology or Cosmology): The input cosmology which gets
                                            converted to a ccl_cosmology.
        x (float or array_like): Argument to fn.
        n (int): Integer argument to fn.
        returns_stats (bool): Indicates whether fn returns a status.

    """
    # Access ccl_cosmology object
    cosmo_in = cosmo
    cosmo = cosmo.cosmo
    status = 0

    if isinstance(x, int):
        x = float(x)
    if isinstance(x, float):
        # Use single-value function
        if returns_status:
            f, status = fn(cosmo, x, n, status)
        else:
            f = fn(cosmo, x, n)
    elif isinstance(x, np.ndarray):
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, n, x, x.size, status)
        else:
            f = fn_vec(cosmo, n, x, x.size)
    else:
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, n, x, len(x), status)
        else:
            f = fn_vec(cosmo, n, x, len(x))

    # Check result and return
    check(status, cosmo_in)
    return f


def _vectorize_fn4(fn, fn_vec, cosmo, x, a, d, returns_status=True):
    """Generic wrapper to allow vectorized (1D array) access to CCL
    functions with one vector argument and two float arguments, with
    a cosmology dependence.

    Args:
        fn (callable): Function with a single argument.
        fn_vec (callable): Function that has a vectorized implementation in
                           a .i file.
        cosmo (ccl_cosmology or Cosmology): The input cosmology which gets
                                            converted to a ccl_cosmology.
        x (float or array_like): Argument to fn.
        a (float): Float argument to fn.
        d (float): Float argument to fn.
        returns_stats (bool): Indicates whether fn returns a status.

    """
    # Access ccl_cosmology object
    cosmo_in = cosmo
    cosmo = cosmo.cosmo
    status = 0

    if isinstance(x, int):
        x = float(x)
    if isinstance(x, float):
        if returns_status:
            f, status = fn(cosmo, x, a, d, status)
        else:
            f = fn(cosmo, x, a, d)
    elif isinstance(x, np.ndarray):
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, a, d, x, x.size, status)
        else:
            f = fn_vec(cosmo, a, d, x, x.size)
    else:
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, a, d, x, len(x), status)
        else:
            f = fn_vec(cosmo, a, d, x, len(x))

    # Check result and return
    check(status, cosmo_in)
    return f


def _vectorize_fn5(fn, fn_vec, cosmo, x1, x2, returns_status=True):
    """Generic wrapper to allow vectorized (1D array) access to CCL
    functions with two vector arguments of the same length,
    with a cosmology dependence.

    Args:
        fn (callable): Function with a single argument.
        fn_vec (callable): Function that has a vectorized implementation in
                           a .i file.
        cosmo (ccl_cosmology or Cosmology): The input cosmology which gets
                                            converted to a ccl_cosmology.
        x1 (float or array_like): Argument to fn.
        x2 (float or array_like): Argument to fn.
        returns_stats (bool): Indicates whether fn returns a status.

    """
    # Access ccl_cosmology object
    cosmo_in = cosmo
    cosmo = cosmo.cosmo
    status = 0

    # If a scalar was passed, convert to an array
    if isinstance(x1, int):
        x1 = float(x1)
        x2 = float(x2)
    if isinstance(x1, float):
        # Use single-value function
        if returns_status:
            f, status = fn(cosmo, x1, x2, status)
        else:
            f = fn(cosmo, x1, x2)
    elif isinstance(x1, np.ndarray):
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, x1, x2, x1.size, status)
        else:
            f = fn_vec(cosmo, x1, x2, x1.size)
    else:
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, x1, x2, len(x2), status)
        else:
            f = fn_vec(cosmo, x1, x2, len(x2))

    # Check result and return
    check(status, cosmo_in)
    return f


def _vectorize_fn6(fn, fn_vec, cosmo, x1, x2, returns_status=True):
    """Generic wrapper to allow vectorized (1D array) access to CCL
    functions with two vector arguments of the any length,
    with a cosmology dependence.

    Args:
        fn (callable): Function with a single argument.
        fn_vec (callable): Function that has a vectorized implementation in
                           a .i file.
        cosmo (ccl_cosmology or Cosmology): The input cosmology which gets
                                            converted to a ccl_cosmology.
        x1 (float or array_like): Argument to fn.
        x2 (float or array_like): Argument to fn.
        returns_stats (bool): Indicates whether fn returns a status.

    """
    # Access ccl_cosmology object
    cosmo_in = cosmo
    cosmo = cosmo.cosmo
    status = 0

    # If a scalar was passed, convert to an array
    if isinstance(x1, int):
        x1 = float(x1)
        x2 = float(x2)
    if isinstance(x1, float):
        # Use single-value function
        if returns_status:
            f, status = fn(cosmo, x1, x2, status)
        else:
            f = fn(cosmo, x1, x2)
    elif isinstance(x1, np.ndarray):
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, x1, x2, int(x1.size*x2.size), status)
        else:
            f = fn_vec(cosmo, x1, x2, int(x1.size*x2.size))
    else:
        # Use vectorised function
        if returns_status:
            f, status = fn_vec(cosmo, x1, x2, int(len(x1)*len(x2)), status)
        else:
            f = fn_vec(cosmo, x1, x2, int(len(x1)*len(x2)))

    # Check result and return
    check(status, cosmo_in)
    return f


def loglin_spacing(logstart, xmin, xmax, num_log, num_lin):
    """Create an array spaced first logarithmically, then linearly.

    .. note::

        The number of logarithmically spaced points used is ``num_log - 1``
        because the first point of the linearly spaced points is the same as
        the end point of the logarithmically spaced points.

    .. code-block:: text

        |=== num_log ==|   |============== num_lin ================|
      --*-*--*---*-----*---*---*---*---*---*---*---*---*---*---*---*--> (axis)
        ^                  ^                                       ^
     logstart             xmin                                    xmax
    """
    log = np.geomspace(logstart, xmin, num_log-1, endpoint=False)
    lin = np.linspace(xmin, xmax, num_lin)
    return np.concatenate((log, lin))


def get_pk_spline_a(cosmo=None, spline_params=spline_params):
    """Get a sampling a-array. Used for P(k) splines."""
    if cosmo is not None:
        spline_params = cosmo._spline_params
    s = spline_params
    return loglin_spacing(s.A_SPLINE_MINLOG_PK, s.A_SPLINE_MIN_PK,
                          s.A_SPLINE_MAX, s.A_SPLINE_NLOG_PK, s.A_SPLINE_NA_PK)


def get_pk_spline_lk(cosmo=None, spline_params=spline_params):
    """Get a sampling log(k)-array. Used for P(k) splines."""
    if cosmo is not None:
        spline_params = cosmo._spline_params
    s = spline_params
    nk = int(np.ceil(np.log10(s.K_MAX/s.K_MIN)*s.N_K))
    return np.linspace(np.log(s.K_MIN), np.log(s.K_MAX), nk)


def resample_array(x_in, y_in, x_out,
                   extrap_lo='none', extrap_hi='none',
                   fill_value_lo=0, fill_value_hi=0):
    """ Interpolates an input y array onto a set of x values.

    Args:
        x_in (array_like): input x-values.
        y_in (array_like): input y-values.
        x_out (array_like): x-values for output array.
        extrap_lo (string): type of extrapolation for x-values below the
            range of `x_in`. 'none' (for no interpolation), 'constant',
            'linx_liny' (linear in x and y), 'linx_logy', 'logx_liny' and
            'logx_logy'.
        extrap_hi (string): type of extrapolation for x-values above the
            range of `x_in`.
        fill_value_lo (float): constant value if `extrap_lo` is
            'constant'.
        fill_value_hi (float): constant value if `extrap_hi` is
            'constant'.
    Returns:
        array_like: output array.
    """
    # TODO: point to the enum in CCLv3 docs.
    status = 0
    y_out, status = lib.array_1d_resample(x_in, y_in, x_out,
                                          fill_value_lo, fill_value_hi,
                                          extrap_types[extrap_lo],
                                          extrap_types[extrap_hi],
                                          x_out.size, status)
    check(status)
    return y_out


def _fftlog_transform(rs, frs,
                      dim, mu, power_law_index):
    if np.ndim(rs) != 1:
        raise ValueError("rs should be a 1D array")
    if np.ndim(frs) < 1 or np.ndim(frs) > 2:
        raise ValueError("frs should be a 1D or 2D array")
    if np.ndim(frs) == 1:
        n_transforms = 1
        n_r = len(frs)
    else:
        n_transforms, n_r = frs.shape

    if len(rs) != n_r:
        raise ValueError(f"rs should have {n_r} elements")

    status = 0
    result, status = lib.fftlog_transform(n_transforms,
                                          rs, frs.flatten(),
                                          dim, mu, power_law_index,
                                          (n_transforms + 1) * n_r,
                                          status)
    check(status)
    result = result.reshape([n_transforms + 1, n_r])
    ks = result[0]
    fks = result[1:]
    if np.ndim(frs) == 1:
        fks = fks.squeeze()

    return ks, fks


def _spline_integrate(x, ys, a, b):
    if np.ndim(x) != 1:
        raise ValueError("x should be a 1D array")
    if np.ndim(ys) < 1 or np.ndim(ys) > 2:
        raise ValueError("ys should be 1D or a 2D array")
    if np.ndim(ys) == 1:
        n_integ = 1
        n_x = len(ys)
    else:
        n_integ, n_x = ys.shape

    if len(x) != n_x:
        raise ValueError(f"x should have {n_x} elements")

    if np.ndim(a) > 0 or np.ndim(b) > 0:
        raise TypeError("Integration limits should be scalar")

    status = 0
    result, status = lib.spline_integrate(n_integ,
                                          x, ys.flatten(),
                                          a, b, n_integ,
                                          status)
    check(status)

    if np.ndim(ys) == 1:
        result = result[0]

    return result


def _check_array_params(f_arg, name=None, arr3=False):
    """Check whether an argument `f_arg` passed into the constructor of
    Tracer() is valid.

    If the argument is set to `None`, it will be replaced with a special array
    that signals to the CCL wrapper that this argument is NULL.
    """
    if f_arg is None:
        # Return empty array if argument is None
        f1 = NoneArr
        f2 = NoneArr
        f3 = NoneArr
    else:
        if ((not isinstance(f_arg, Iterable))
            or (len(f_arg) != (3 if arr3 else 2))
            or (not (isinstance(f_arg[0], Iterable)
                     and isinstance(f_arg[1], Iterable)))):
            raise ValueError(f"{name} must be a tuple of two arrays.")

        f1 = np.atleast_1d(np.array(f_arg[0], dtype=float))
        f2 = np.atleast_1d(np.array(f_arg[1], dtype=float))
        if arr3:
            f3 = np.atleast_1d(np.array(f_arg[2], dtype=float))
    if arr3:
        return f1, f2, f3
    else:
        return f1, f2


def _get_spline1d_arrays(gsl_spline):
    """Get array data from a 1D GSL spline.

    Args:
        gsl_spline: `SWIGObject` of gsl_spline
            The SWIG object of the GSL spline.

    Returns:
        xarr: array_like
            The x array of the spline.
        yarr: array_like
            The y array of the spline.
    """
    status = 0
    size, status = lib.get_spline1d_array_size(gsl_spline, status)
    check(status)

    xarr, yarr, status = lib.get_spline1d_arrays(gsl_spline, size, size,
                                                 status)
    check(status)

    return xarr, yarr


def _get_spline2d_arrays(gsl_spline):
    """Get array data from a 2D GSL spline.

    Args:
        gsl_spline: `SWIGObject` of gsl_spline2d *
            The SWIG object of the 2D GSL spline.

    Returns:
        yarr: array_like
            The y array of the spline.
        xarr: array_like
            The x array of the spline.
        zarr: array_like
            The z array of the spline. The shape is (yarr.size, xarr.size).
    """
    status = 0
    x_size, y_size, status = lib.get_spline2d_array_sizes(gsl_spline, status)
    check(status)

    z_size = x_size*y_size
    xarr, yarr, zarr, status = lib.get_spline2d_arrays(gsl_spline,
                                                       x_size, y_size, z_size,
                                                       status)
    check(status)

    return yarr, xarr, zarr.reshape(y_size, x_size)


def _get_spline3d_arrays(gsl_spline, length):
    """Get array data from an array of 2D GSL splines.

    Args:
        gsl_spline (`SWIGObject` of gsl_spline2d **):
            The SWIG object of the 2D GSL spline.
        length (int):
            The length of the 3rd dimension.

    Returns:
        xarr: array_like
            The x array of the spline.
        yarr: array_like
            The y array of the spline.
        zarr: array_like
            The z array of the spline. The shape is (yarr.size, xarr.size).
    """
    status = 0
    x_size, y_size, status = lib.get_spline3d_array_sizes(gsl_spline, status)
    check(status)

    z_size = x_size*y_size*length
    xarr, yarr, zarr, status = lib.get_spline3d_arrays(gsl_spline,
                                                       x_size, y_size, z_size,
                                                       length, status)
    check(status)

    return xarr, yarr, zarr.reshape((length, x_size, y_size))


def check_openmp_version():
    """Return the OpenMP specification release date.
    Return 0 if OpenMP is not working.
    """

    return lib.openmp_version()


def check_openmp_threads():
    """Returns the number of processors available to the device.
    Return 0 if OpenMP is not working.
    """

    return lib.openmp_threads()
