# enums.py

from enum import Enum

class ObjectType(Enum):
    COLORCURVE = "colorcurve"
    FLOATCURVE = "floatcurve"
    SDFKV = "sdfkv"

class FloatCurveType(Enum):
    PARABOLIC = "parabolic"
    SINUSOIDAL = "sinusoidal"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    BELL = "bell"
    CUBIC = "cubic"
    STEP = "step"
    RANDOM = "random"
    QUADRATIC = "quadratic"
    HYPERBOLIC = "hyperbolic"
    LERP = "lerp"
    DRAGON = "dragon"
    CYCLE = "cycle"
    RAINBOW = "rainbow"
    EULER_SPIRAL = "euler_spiral" 
    FIBONACCI_WEIGHTED = "fibonacci_weighted" 


class InterpMode(Enum):
    RCIM_LINEAR = "RCIM_Linear"  
    RCIM_CUBIC = "RCIM_Cubic"  
    RCIM_QUADRATIC = "RCIM_Quadratic"
    RCIM_CONSTANT = "RCIM_Constant"
    RCIM_NEAREST = "RCIM_Nearest"
    RCIM_SLINEAR = "RCIM_Slinear"
    RCIM_POLYNOMIAL = "RCIM_Polynomial"
    RCIM_BARYCENTRIC = "RCIM_Barycentric"
    RCIM_KROGH = "RCIM_Krogh"
    RCIM_PCHIP = "RCIM_Pchip"
    RCIM_AKIMA = "RCIM_Akima"

    # Method to get the corresponding plotting kind  
    def to_plotting_kind(self):  
        return {  
            InterpMode.RCIM_LINEAR: "linear",  
            InterpMode.RCIM_CUBIC: "cubic",  
            InterpMode.RCIM_QUADRATIC: "quadratic",  
            InterpMode.RCIM_CONSTANT: "constant",
            InterpMode.RCIM_NEAREST: "nearest",
            InterpMode.RCIM_SLINEAR: "slinear",
            InterpMode.RCIM_POLYNOMIAL: "polynomial",
            InterpMode.RCIM_BARYCENTRIC: "barycentric",
            InterpMode.RCIM_KROGH: "krogh",
            InterpMode.RCIM_PCHIP: "pchip",
            InterpMode.RCIM_AKIMA: "akima",
        }.get(self, "linear")  # Default to linear if not found

    # Method to get a list of all available plotting kinds
    @classmethod
    def available_plotting_kinds(cls):
        return [mode.to_plotting_kind() for mode in cls]