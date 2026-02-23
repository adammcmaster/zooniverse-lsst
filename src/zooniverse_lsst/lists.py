"""
BSD 3-Clause License

Copyright (c) 2008-2011, AQR Capital Management, LLC, Lambda Foundry, Inc. and PyData Development Team
All rights reserved.

Copyright (c) 2011-2025, Open source contributors.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Based on Pandas
# https://github.com/pandas-dev/pandas/blob/fcffde9d7c1914cacc3f6708dbff4a1856d339d9/pandas/_libs/lib.pyx#L1252


from collections import abc


def _is_list_like(obj: object, allow_sets: bool = True) -> bool:
    """
    Check if the object is list-like.

    Objects that are considered list-like are for example Python
    lists, tuples, sets, NumPy arrays, and Pandas Series.

    Strings and datetime objects, however, are not considered list-like.

    Parameters
    ----------
    obj : object
        Object to check.
    allow_sets : bool, default True
        If this parameter is False, sets will not be considered list-like.

    Returns
    -------
    bool
        Whether `obj` has list-like properties.

    See Also
    --------
    Series : One-dimensional ndarray with axis labels (including time series).
    Index : Immutable sequence used for indexing and alignment.
    numpy.ndarray : Array object from NumPy, which is considered list-like.

    Examples
    --------
    >>> import datetime
    >>> from pandas.api.types import is_list_like
    >>> is_list_like([1, 2, 3])
    True
    >>> is_list_like({1, 2, 3})
    True
    >>> is_list_like(datetime.datetime(2017, 1, 1))
    False
    >>> is_list_like("foo")
    False
    >>> is_list_like(1)
    False
    >>> is_list_like(np.array([2]))
    True
    >>> is_list_like(np.array(2))
    False
    """
    # return c_is_list_like(obj, allow_sets)

    # cdef bint c_is_list_like(object obj, bint allow_sets) except -1:
    # first, performance short-cuts for the most common cases
    # if util.is_array(obj):
    # exclude zero-dimensional numpy arrays, effectively scalars
    # return not cnp.PyArray_IsZeroDim(obj)
    if isinstance(obj, list):
        return True
    # then the generic implementation
    return (
        # equiv: `isinstance(obj, abc.Iterable)`
        getattr(obj, "__iter__", None) is not None
        and not isinstance(obj, type)
        # we do not count strings/unicode/bytes as list-like
        # exclude Generic types that have __iter__
        and not isinstance(obj, (str, bytes))  # , _GenericAlias, GenericAlias))
        # exclude zero-dimensional duck-arrays, effectively scalars
        and not (hasattr(obj, "ndim") and obj.ndim == 0)
        # exclude sets if allow_sets is False
        and not (allow_sets is False and isinstance(obj, abc.Set))
    )


try:
    # Import the pandas version if it's there since that will work on pandas' types
    from pandas.api.types import is_list_like
except ImportError:
    is_list_like = _is_list_like
