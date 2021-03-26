from typing import Any, Optional

class Function:
    test_types: Any = ...
    len_test_types: Any = ...
    kindToNumber: Any = ...
    boolFunctions: Any = ...
    function: Any = ...
    is_bool: Any = ...
    is_abs: Any = ...
    __doc__: Any = ...
    nin: Any = ...
    nout: Any = ...
    def __init__(self, function: Any) -> None: ...
    def __getattr__(self, name: Any): ...
    def priorities(self, *args: Any): ...
    def common_type_numpy(self, *args: Any): ...
    def common_type(self, *args: Any): ...

class UnaryFunction(Function):
    def __call__(self, arg: Any, out: Optional[Any] = ...): ...

class UnaryFunctionOut2(Function):
    def __call__(self, arg: Any, out1: Optional[Any] = ..., out2: Optional[Any] = ...): ...

class BinaryFunction(Function):
    def __call__(self, arg1: Any, arg2: Any, out: Optional[Any] = ...): ...

# Names in __all__ with no definition:
#   _arg
#   absolute
#   absolute
#   add
#   arccos
#   arccosh
#   arcsin
#   arcsinh
#   arctan
#   arctan2
#   arctanh
#   bitwise_and
#   bitwise_or
#   bitwise_xor
#   cbrt
#   ceil
#   conjugate
#   conjugate
#   copysign
#   cos
#   cosh
#   deg2rad
#   degrees
#   divmod
#   equal
#   exp
#   exp2
#   expm1
#   fabs
#   float_power
#   floor
#   floor_divide
#   fmax
#   fmin
#   fmod
#   frexp
#   gcd
#   greater
#   greater_equal
#   heaviside
#   hypot
#   invert
#   invert
#   isfinite
#   isinf
#   isnan
#   isnat
#   lcm
#   ldexp
#   left_shift
#   less
#   less_equal
#   log
#   log10
#   log1p
#   log2
#   logaddexp
#   logaddexp2
#   logical_and
#   logical_not
#   logical_or
#   logical_xor
#   matmul
#   maximum
#   minimum
#   modf
#   multiply
#   negative
#   nextafter
#   not_equal
#   positive
#   power
#   rad2deg
#   radians
#   reciprocal
#   remainder
#   remainder
#   right_shift
#   rint
#   sign
#   signbit
#   sin
#   sinh
#   spacing
#   sqrt
#   square
#   subtract
#   tan
#   tanh
#   true_divide
#   true_divide
#   trunc
