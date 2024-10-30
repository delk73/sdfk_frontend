from datetime import datetime, timezone
import json
import logging
import random
import re
import time
from typing import Any, Dict, Optional
import numpy as np
import os
from PIL import Image, ImageDraw
from enums import FloatCurveType
import uuid
import math
from models import SDFKColorCurve
import scipy.special 

class CurveHelper:
    """Helper class for fetching, generating, and processing color curves."""

    @staticmethod
    def remap(values, old_min, old_max, new_min, new_max):
        """Remap the values from the old range to a new range."""
        return (values - old_min) / (old_max - old_min) * (new_max - new_min) + new_min

    @staticmethod
    def extract_curve_data(curve, epsilon=1e-6):
        """Helper function to extract times and values from curve data."""
        if len(curve) == 1:
            constant_value = curve[0]['value']
            return [0, 1], [constant_value, constant_value]
        else:
            times = [key['time'] for key in curve]
            values = [key['value'] for key in curve]
            values = [0 if abs(v) < epsilon else v for v in values]
            return times, values

    @staticmethod
    def clamp(value, min_value, max_value):
        """Clamp values to be within a given range."""
        return max(min_value, min(value, max_value))

    @staticmethod
    def process_alpha_channel(alpha_normalized):
        """Process alpha values more robustly and remap them."""
        if np.allclose(alpha_normalized, alpha_normalized[0]):
            return np.full_like(alpha_normalized, int(alpha_normalized[0] * 255))

        min_alpha = min(alpha_normalized)
        max_alpha = max(alpha_normalized)

        if min_alpha == max_alpha:
            return np.full_like(alpha_normalized, 255)
        else:
            return CurveHelper.remap(alpha_normalized, min_alpha, max_alpha, 0, 255).astype(np.uint8)

    @staticmethod
    def create_checkered_background(width, height, square_size=8):
        """Creates a checkered background of given size."""
        background = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(background)
        colors = [(200, 200, 200, 255), (255, 255, 255, 255)]  # Light gray and white

        for y in range(0, height, square_size):
            for x in range(0, width, square_size):
                fill_color = colors[((x // square_size) + (y // square_size)) % 2]
                draw.rectangle([x, y, x + square_size, y + square_size], fill=fill_color)

        return background

    @staticmethod
    def generate_random_key(time_range=(0, 1)):
        """Generate a random key for a float curve."""
        return {
            "interpMode": random.choice(["RCIM_Constant", "RCIM_Linear", "RCIM_Cubic"]),
            "tangentMode": random.choice(["RCTM_Auto", "RCTM_Break", "RCTM_User"]),
            "tangentWeightMode": "RCTWM_WeightedNone",
            "time": random.uniform(*time_range),
            "value": random.uniform(0, 1),
            "arriveTangent": 0,
            "arriveTangentWeight": 0,
            "leaveTangent": 0,
            "leaveTangentWeight": random.uniform(0, 1)
        }

    @staticmethod
    def generate_random_float_curve(min_keys=2, max_keys=100, float_curve_type=None):
        """
        Generate a random float curve with a random number of keys between min_keys and max_keys.
        Enhanced to include multiple curve types for increased variance and prevent washed-out curves.
        If float_curve_type is None, a random FloatCurveType will be selected.
        """
        # If no specific type is provided, choose a random FloatCurveType
        if float_curve_type is None:
            float_curve_type = random.choice(list(FloatCurveType))

        num_keys = random.randint(min_keys, max_keys)
        times = sorted(random.uniform(0, 1) for _ in range(num_keys))
        keys = []

        for i in range(num_keys):
            t = times[i]

            # Apply the curve generation logic based on float_curve_type
            if float_curve_type == FloatCurveType.PARABOLIC:
                value = (t - 0.5) ** 2  # Parabolic distribution
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.2, 0.6)
                leave_tangent_weight = random.uniform(0.2, 0.6)
            elif float_curve_type == FloatCurveType.SINUSOIDAL:
                value = (math.sin(t * math.pi - math.pi / 2) + 1) / 2
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedArrive"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.EXPONENTIAL:
                value = t ** 3  # Exponential rise
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedLeave"
                arrive_tangent = random.uniform(0, 0.3)
                leave_tangent = random.uniform(0.5, 1.0)
                arrive_tangent_weight = random.uniform(0.1, 0.4)
                leave_tangent_weight = random.uniform(0.5, 1.0)
            elif float_curve_type == FloatCurveType.LOGARITHMIC:
                value = math.log1p(t * (math.e - 1)) / math.log(math.e)
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedArrive"
                arrive_tangent = random.uniform(0.1, 0.5)
                leave_tangent = random.uniform(0.1, 0.5)
                arrive_tangent_weight = random.uniform(0.1, 0.3)
                leave_tangent_weight = random.uniform(0.1, 0.3)
            elif float_curve_type == FloatCurveType.BELL:
                value = math.exp(-((t - 0.5) ** 2) / (2 * 0.05 ** 2))  # Bell-shaped
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.1, 0.1)
                leave_tangent = random.uniform(-0.1, 0.1)
                arrive_tangent_weight = random.uniform(0.2, 0.5)
                leave_tangent_weight = random.uniform(0.2, 0.5)
            elif float_curve_type == FloatCurveType.CUBIC:
                value = 4 * (t - 0.5) ** 3 + 0.5
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.STEP:
                step_position = random.uniform(0.3, 0.7)
                value = 0.0 if t < step_position else 1.0
                interp_mode = "RCIM_Constant"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = 0
                leave_tangent = 0
                arrive_tangent_weight = 0
                leave_tangent_weight = 0
            elif float_curve_type == FloatCurveType.RANDOM:
                value = random.uniform(0, 1)
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = random.uniform(-0.5, 0.5)
                leave_tangent = random.uniform(-0.5, 0.5)
                arrive_tangent_weight = random.uniform(0, 1)
                leave_tangent_weight = random.uniform(0, 1)
            elif float_curve_type == FloatCurveType.QUADRATIC:
                value = t ** 2  # Quadratic curve
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.3, 0.3)
                leave_tangent = random.uniform(-0.3, 0.3)
                arrive_tangent_weight = random.uniform(0.2, 0.6)
                leave_tangent_weight = random.uniform(0.2, 0.6)
            elif float_curve_type == FloatCurveType.HYPERBOLIC:
                value = 1 / (1 + math.exp(-10 * (t - 0.5)))  # Hyperbolic curve
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.4, 0.4)
                leave_tangent = random.uniform(-0.4, 0.4)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.LERP:
                value = t  # Linear interpolation
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = 0
                leave_tangent = 0
                arrive_tangent_weight = 0
                leave_tangent_weight = 0
            elif float_curve_type == FloatCurveType.DRAGON:
                value = CurveHelper.generate_dragon_step_value(t)  # Dragon curve logic
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.3, 0.3)
                leave_tangent = random.uniform(-0.3, 0.3)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.CYCLE:
                value = (math.sin(2 * math.pi * t) + 1) / 2  # Cyclical, sine-based
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedArrive"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.RAINBOW:
                value = CurveHelper.generate_rainbow_value(t)  # Rainbow-like transitions
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.3, 0.3)
                leave_tangent = random.uniform(-0.3, 0.3)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.EULER_SPIRAL:
                value = CurveHelper.generate_euler_spiral_value(t)  # Euler spiral curve
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.4, 0.4)
                leave_tangent = random.uniform(-0.4, 0.4)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.FIBONACCI_WEIGHTED:
                value = CurveHelper.generate_fibonacci_weighted_value(t)  # Fibonacci weighting
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.5, 0.5)
                leave_tangent = random.uniform(-0.5, 0.5)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            else:
                value = random.uniform(0, 1)  # Fallback to random
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = random.uniform(-0.5, 0.5)
                leave_tangent = random.uniform(-0.5, 0.5)
                arrive_tangent_weight = random.uniform(0, 1)
                leave_tangent_weight = random.uniform(0, 1)

            # Add noise to the value for variability
            noise_range = 0.1 / (math.log(num_keys + 1) + 1)
            noise = random.uniform(-noise_range, noise_range)
            value = CurveHelper.clamp(value + noise, 0, 1)

            keys.append({
                "interpMode": interp_mode,
                "tangentMode": tangent_mode,
                "tangentWeightMode": tangent_weight_mode,
                "time": t,
                "value": value,
                "arriveTangent": arrive_tangent,
                "arriveTangentWeight": arrive_tangent_weight,
                "leaveTangent": leave_tangent,
                "leaveTangentWeight": leave_tangent_weight
            })

        return {
            "keys": keys,
            "defaultValue": 3.4028234663852886e+38,  # FLT_MAX as placeholder
            "preInfinityExtrap": "RCCE_Constant",
            "postInfinityExtrap": "RCCE_Constant"
        }
    
    @staticmethod
    def generate_float_curve(float_curve_type=None, resolution_scale=1.0, noise_scale=0.0):
        """
        Generate a float curve based on the float_curve_type.
        If float_curve_type is None, a random FloatCurveType is selected.
        
        Parameters:
            float_curve_type (FloatCurveType, optional): The type of float curve to generate.
            resolution_scale (float): Scales the number of keys.
            noise_scale (float): Adds variability to the curve values.
            min_keys (int): Minimum number of keys for random key count selection.
            max_keys (int): Maximum number of keys for random key count selection.
        
        Returns:
            dict: A dictionary representing the float curve.
        """
        if float_curve_type is None:
            float_curve_type = random.choice(list(FloatCurveType))
        
        min_keys=2
        max_keys=100

        # Define default key counts based on float curve type
        default_key_counts = {
            FloatCurveType.PARABOLIC: 120,
            FloatCurveType.SINUSOIDAL: 130,
            FloatCurveType.EXPONENTIAL: 115,
            FloatCurveType.LOGARITHMIC: 115,
            FloatCurveType.BELL: 125,
            FloatCurveType.CUBIC: 120,
            FloatCurveType.STEP: 110,
            FloatCurveType.QUADRATIC: 120,
            FloatCurveType.HYPERBOLIC: 115,
            FloatCurveType.LERP: 110,
            FloatCurveType.DRAGON: 140,
            FloatCurveType.CYCLE: 130,
            FloatCurveType.RAINBOW: 150,
            FloatCurveType.EULER_SPIRAL: 135,
            FloatCurveType.FIBONACCI_WEIGHTED: 125,
            FloatCurveType.RANDOM: 150, #This is overridden below
        }
        
        #Use Value Or Random
        default_num_keys = default_key_counts.get(float_curve_type, random.randint(min_keys, max_keys))
        
        # If the type is RANDOM, allow key count to vary between min_keys and max_keys
        if float_curve_type == FloatCurveType.RANDOM:
            num_keys = random.randint(min_keys, max_keys)
        else:
            num_keys = int(default_num_keys * resolution_scale)
            num_keys = max(min_keys, min(num_keys, max_keys))  # Ensure within bounds
        
        # Generate sorted time points between 0 and 1
        times = sorted(random.uniform(0, 1) for _ in range(num_keys))
        keys = []
        
        for t in times:
            # Initialize variables
            value = 0.0
            interp_mode = "RCIM_Cubic"
            tangent_mode = "RCTM_Auto"
            tangent_weight_mode = "RCTWM_WeightedBoth"
            arrive_tangent = 0.0
            leave_tangent = 0.0
            arrive_tangent_weight = 0.0
            leave_tangent_weight = 0.0
            
            # Apply the curve generation logic based on float_curve_type
            if float_curve_type == FloatCurveType.PARABOLIC:
                value = (t - 0.5) ** 2  # Parabolic distribution
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.2, 0.6)
                leave_tangent_weight = random.uniform(0.2, 0.6)
            elif float_curve_type == FloatCurveType.SINUSOIDAL:
                value = (math.sin(t * math.pi - math.pi / 2) + 1) / 2
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedArrive"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.EXPONENTIAL:
                value = t ** 3  # Exponential rise
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedLeave"
                arrive_tangent = random.uniform(0, 0.3)
                leave_tangent = random.uniform(0.5, 1.0)
                arrive_tangent_weight = random.uniform(0.1, 0.4)
                leave_tangent_weight = random.uniform(0.5, 1.0)
            elif float_curve_type == FloatCurveType.LOGARITHMIC:
                value = math.log1p(t * (math.e - 1)) / math.log(math.e)
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedArrive"
                arrive_tangent = random.uniform(0.1, 0.5)
                leave_tangent = random.uniform(0.1, 0.5)
                arrive_tangent_weight = random.uniform(0.1, 0.3)
                leave_tangent_weight = random.uniform(0.1, 0.3)
            elif float_curve_type == FloatCurveType.BELL:
                value = math.exp(-((t - 0.5) ** 2) / (2 * 0.05 ** 2))  # Bell-shaped
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.1, 0.1)
                leave_tangent = random.uniform(-0.1, 0.1)
                arrive_tangent_weight = random.uniform(0.2, 0.5)
                leave_tangent_weight = random.uniform(0.2, 0.5)
            elif float_curve_type == FloatCurveType.CUBIC:
                value = 4 * (t - 0.5) ** 3 + 0.5
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.STEP:
                step_position = random.uniform(0.3, 0.7)
                value = 0.0 if t < step_position else 1.0
                interp_mode = "RCIM_Constant"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = 0
                leave_tangent = 0
                arrive_tangent_weight = 0
                leave_tangent_weight = 0
            elif float_curve_type == FloatCurveType.RANDOM:
                value = random.uniform(0, 1)
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = random.uniform(-0.5, 0.5)
                leave_tangent = random.uniform(-0.5, 0.5)
                arrive_tangent_weight = random.uniform(0, 1)
                leave_tangent_weight = random.uniform(0, 1)
            elif float_curve_type == FloatCurveType.QUADRATIC:
                value = t ** 2  # Quadratic curve
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.3, 0.3)
                leave_tangent = random.uniform(-0.3, 0.3)
                arrive_tangent_weight = random.uniform(0.2, 0.6)
                leave_tangent_weight = random.uniform(0.2, 0.6)
            elif float_curve_type == FloatCurveType.HYPERBOLIC:
                value = 1 / (1 + math.exp(-10 * (t - 0.5)))  # Hyperbolic curve
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.4, 0.4)
                leave_tangent = random.uniform(-0.4, 0.4)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.LERP:
                value = t  # Linear interpolation
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = 0
                leave_tangent = 0
                arrive_tangent_weight = 0
                leave_tangent_weight = 0
            elif float_curve_type == FloatCurveType.DRAGON:
                value = CurveHelper.generate_dragon_step_value(t)  # Dragon curve logic
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.3, 0.3)
                leave_tangent = random.uniform(-0.3, 0.3)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.CYCLE:
                value = (math.sin(2 * math.pi * t) + 1) / 2  # Cyclical, sine-based
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_Auto"
                tangent_weight_mode = "RCTWM_WeightedArrive"
                arrive_tangent = random.uniform(-0.2, 0.2)
                leave_tangent = random.uniform(-0.2, 0.2)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.RAINBOW:
                value = CurveHelper.generate_rainbow_value(t)  # Rainbow-like transitions
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.3, 0.3)
                leave_tangent = random.uniform(-0.3, 0.3)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.EULER_SPIRAL:
                value = CurveHelper.generate_euler_spiral_value(t)  # Euler spiral curve
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.4, 0.4)
                leave_tangent = random.uniform(-0.4, 0.4)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            elif float_curve_type == FloatCurveType.FIBONACCI_WEIGHTED:
                value = CurveHelper.generate_fibonacci_weighted_value(t)  # Fibonacci weighting
                interp_mode = "RCIM_Cubic"
                tangent_mode = "RCTM_User"
                tangent_weight_mode = "RCTWM_WeightedBoth"
                arrive_tangent = random.uniform(-0.5, 0.5)
                leave_tangent = random.uniform(-0.5, 0.5)
                arrive_tangent_weight = random.uniform(0.3, 0.7)
                leave_tangent_weight = random.uniform(0.3, 0.7)
            else:
                value = random.uniform(0, 1)  # Fallback to random
                interp_mode = "RCIM_Linear"
                tangent_mode = "RCTM_Break"
                tangent_weight_mode = "RCTWM_WeightedNone"
                arrive_tangent = random.uniform(-0.5, 0.5)
                leave_tangent = random.uniform(-0.5, 0.5)
                arrive_tangent_weight = random.uniform(0, 1)
                leave_tangent_weight = random.uniform(0, 1)
    
            # Add noise to the value for variability
            if noise_scale != 0:
                noise_range = 0.1 / (math.log(num_keys + 1) + 1)
                noise = random.uniform(-noise_range, noise_range)
                value = CurveHelper.clamp(value + (noise * noise_scale), 0, 1)
    
            # Append the key
            keys.append({
                "interpMode": interp_mode,
                "tangentMode": tangent_mode,
                "tangentWeightMode": tangent_weight_mode,
                "time": t,
                "value": value,
                "arriveTangent": arrive_tangent,
                "arriveTangentWeight": arrive_tangent_weight,
                "leaveTangent": leave_tangent,
                "leaveTangentWeight": leave_tangent_weight
            })
    
        return {
            "keys": keys,
            "defaultValue": 3.4028234663852886e+38,  # FLT_MAX as placeholder
            "preInfinityExtrap": "RCCE_Constant",
            "postInfinityExtrap": "RCCE_Constant"
        }



    @staticmethod
    def generate_dragon_step_value(t):
        """
        Generate a Dragon-like curve value for a given parameter t.
        Combines multiple sine waves to emulate the fractal complexity of the Dragon Curve.

        :param t: A float between 0 and 1 representing the parameter along the curve.
        :return: A float between 0 and 1 representing the Dragon Curve value at t.
        """
        # Normalize t to range [0, 4π] for multiple wave cycles
        theta = t * 4 * math.pi  # Two full sine cycles

        # Combine multiple sine waves with different frequencies and phases
        value = (
            0.3 * math.sin(theta) +
            0.2 * math.sin(3 * theta + math.pi / 4) +
            0.1 * math.sin(5 * theta + math.pi / 2)
        )

        # Normalize the combined value to [0, 1]
        normalized_value = (value + 0.6) / 1.2  # Adjusting based on amplitude

        # Clamp the value to ensure it stays within [0, 1]
        return CurveHelper.clamp(normalized_value, 0, 1)

    @staticmethod
    def generate_rainbow_value(t):
        """
        Generate a Rainbow-like curve value for a given parameter t.
        Uses a sine wave to create a smooth, cyclical oscillation.

        :param t: A float between 0 and 1 representing the parameter along the curve.
        :return: A float between 0 and 1 representing the Rainbow Curve value at t.
        """
        # Single sine wave cycle for smooth oscillation
        value = (math.sin(2 * math.pi * t - math.pi / 2) + 1) / 2  # Shifted sine wave

        return CurveHelper.clamp(value, 0, 1)

    @staticmethod
    def generate_euler_spiral_value(t):
        """
        Generate an Euler Spiral-like curve value for a given parameter t.
        Utilizes Fresnel Integrals to emulate the spiral's curvature properties.

        :param t: A float between 0 and 1 representing the parameter along the curve.
        :return: A float between 0 and 1 representing the Euler Spiral Curve value at t.
        """
        # Compute Fresnel Integrals for the given t
        S, C = scipy.special.fresnel(t)

        # The Fresnel Integrals range from [0, 0.5] for t in [0, 1]
        # Normalize the results to [0, 1]
        # Here, we'll use the C (cosine) component as the float curve value
        normalized_value = 2 * C  # Scale from [0, 0.5] to [0, 1]

        return CurveHelper.clamp(normalized_value, 0, 1)

    @staticmethod
    def generate_fibonacci_weighted_value(t):
        """
        Generate a Fibonacci Weighted curve value for a given parameter t.
        Utilizes the Golden Ratio to create an asymmetrical, balanced curve.

        :param t: A float between 0 and 1 representing the parameter along the curve.
        :return: A float between 0 and 1 representing the Fibonacci Weighted Curve value at t.
        """
        phi = (1 + math.sqrt(5)) / 2  # Golden Ratio ≈ 1.618

        # Apply the Fibonacci weighting formula
        # The formula creates an S-shaped curve with asymmetry based on the Golden Ratio
        value = (t ** phi) / (t ** phi + (1 - t) ** phi)

        return CurveHelper.clamp(value, 0, 1)


    @staticmethod
    def generate_random_color_curve() -> Dict[str, Any]:
        """
        Generate a random color curve using random values.

        :return: Dictionary representing the generated random color curve.
        """
        curve_id = str(uuid.uuid4())

        # Use random choice for each channel's float curve type
        float_curve_types = {
            channel: random.choice(list(FloatCurveType))
            for channel in ["R", "G", "B", "A"]
        }

        # Generate float curves for each channel
        float_curves = {
            channel: CurveHelper.generate_random_float_curve(
                min_keys=2,
                max_keys=100,
                float_curve_type=curve_type
            )
            for channel, curve_type in float_curve_types.items()
        }

        # Generate random adjustments
        randomize_adjustments = 0.1  # Example range for random adjustments
        adjustments = {
            "adjustHue": random.uniform(0, randomize_adjustments),
            "adjustSaturation": random.uniform(0, randomize_adjustments),
            "adjustBrightness": random.uniform(0, randomize_adjustments),
            "adjustBrightnessCurve": random.uniform(0, randomize_adjustments),
            "adjustVibrance": random.uniform(0, randomize_adjustments),
            "adjustMinAlpha": random.uniform(0, randomize_adjustments),
            "adjustMaxAlpha": random.uniform(0, randomize_adjustments)
        }

        # Generate a combined type descriptor
        curve_type_comp = '-'.join([curve_type.name for curve_type in float_curve_types.values()])

        # Get the current UTC timestamp
        utc_time_string = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        # Base curve_json structure
        curve_json = {
            "floatCurves": float_curves,
            **adjustments,
            "assetImportData": {
                "_ClassName": "/Script/Engine.AssetImportData",
                "sourceData": {}
            },
            "created_at": utc_time_string
        }

        # Construct the final JSON for a random curve
        final_json = {
            "curve_id": curve_id,
            "curve_type_comp": curve_type_comp,
            "curve_json": curve_json
        }

        return final_json


    @staticmethod
    def generate_color_curve_from_spec(json_data: Optional[Dict[str, Any]] = None, float_curve_type: Optional[FloatCurveType] = None) -> Dict[str, Any]:
            """
            Generate a color curve either randomly or based on provided JSON data.

            :param json_data: Optional dictionary containing parameters to generate the curve.
            :param float_curve_type: Optional FloatCurveType to use for all channels when generating randomly.
            :return: Dictionary representing the generated color curve.
            """
            curve_id = str(uuid.uuid4())

            # Determine if we are generating randomly or from JSON
            is_random = json_data is None

            # Initialize float_curve_types
            if is_random:
                # Use the float_curve_type provided, or random choice for each channel
                float_curve_types = {
                    channel: float_curve_type or random.choice(list(FloatCurveType))
                    for channel in ["R", "G", "B", "A"]
                }
            else:
                def get_enum(json_key: str, default: str) -> FloatCurveType:
                    try:
                        return FloatCurveType[json_data.get(json_key, default).upper()]
                    except KeyError:
                        return FloatCurveType.PARABOLIC  # Default fallback

                float_curve_types = {
                    "R": get_enum("R_float_curve_type", "PARABOLIC"),
                    "G": get_enum("G_float_curve_type", "PARABOLIC"),
                    "B": get_enum("B_float_curve_type", "PARABOLIC"),
                    "A": get_enum("A_float_curve_type", "PARABOLIC")
                }

            # Generate float curves
            float_curves = {}
            for channel, curve_type in float_curve_types.items():
                if is_random:
                    float_curves[channel] = CurveHelper.generate_random_float_curve(
                        min_keys=2,
                        max_keys=100,
                        float_curve_type=curve_type
                    )
                else:
                    float_curves[channel] = CurveHelper.generate_float_curve(
                        float_curve_type=curve_type,
                        resolution_scale=json_data.get(f"{channel}_resolution_scale", 1.0),
                        noise_scale=json_data.get(f"{channel}_noise_scale", 0.0)
                    )

            # Generate Meta Curves if JSON data is provided
            if not is_random:
                x_offset_curve = CurveHelper.generate_float_curve(
                    float_curve_type=get_enum("meta_x_offset_curve_type", "PARABOLIC"),
                    resolution_scale=json_data.get("meta_x_resolution_scale", 1.0),
                    noise_scale=json_data.get("meta_x_noise_scale", 0.0)
                )
                y_offset_curve = CurveHelper.generate_float_curve(
                    float_curve_type=get_enum("meta_y_offset_curve_type", "PARABOLIC"),
                    resolution_scale=json_data.get("meta_y_resolution_scale", 1.0),
                    noise_scale=json_data.get("meta_y_noise_scale", 0.0)
                )
            else:
                x_offset_curve = None
                y_offset_curve = None

            # Generate adjustments
            randomize_adjustments = json_data.get("randomize_adjustments", 0) if json_data else 0
            adjustments = {
                "adjustHue": random.uniform(0, randomize_adjustments),
                "adjustSaturation": random.uniform(0, randomize_adjustments),
                "adjustBrightness": random.uniform(0, randomize_adjustments),
                "adjustBrightnessCurve": random.uniform(0, randomize_adjustments),
                "adjustVibrance": random.uniform(0, randomize_adjustments),
                "adjustMinAlpha": random.uniform(0, randomize_adjustments),
                "adjustMaxAlpha": random.uniform(0, randomize_adjustments)
            }

            # Determine curve_type_comp
            
            if json_data:
                curve_type_comp = "{}-{}-{}-{}-{}".format(
                    json_data.get("name", "Unnamed Curve"),
                    json_data.get("R_float_curve_type", ""),
                    json_data.get("G_float_curve_type", ""),
                    json_data.get("B_float_curve_type", ""),
                    json_data.get("A_float_curve_type", "")
                ).strip("-")
            elif not is_random:
                curve_type_comp = json_data.get("name", "Unnamed Curve")
            else:
                # Generate curve_type_comp as concatenation of curve types
                curve_type_comp = '-'.join([curve_type.name for curve_type in float_curve_types.values()])

            # Get the current UTC timestamp
            utc_time_string = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

            # Base curve_json
            curve_json = {
                "floatCurves": float_curves,
                **adjustments,
                "assetImportData": {
                    "_ClassName": "/Script/Engine.AssetImportData",
                    "sourceData": {}
                },
                "created_at": utc_time_string
            }

            # Include metaCurves if JSON data is provided
            if not is_random:
                curve_json["metaCurves"] = {
                    "x_offset_curve": x_offset_curve,
                    "y_offset_curve": y_offset_curve,
                    "x_offset_scale": json_data.get("meta_x_offset_scale", 0.0),
                    "y_offset_scale": json_data.get("meta_y_offset_scale", 0.0)
                }

            # Construct the final JSON
            if is_random:
                # Match the structure of generate_random_color_curve when json_data is not provided
                final_json = {
                    "curve_id": curve_id,
                    "curve_type_comp": curve_type_comp,
                    "curve_json": curve_json
                }
            else:
                # Include additional fields when json_data is provided
                final_json = {
                    "curve_id": curve_id,
                    "name": json_data.get("name", "Unnamed Curve"),
                    "description": json_data.get("description", ""),
                    "curve_type_comp": curve_type_comp,
                    "curve_json": curve_json
                }
                # Append metadata about the curve
                CurveHelper.append_metadata(curve_id, json_data.get("name", "Unnamed Curve"))

            return final_json


        ########

    @staticmethod
    def generate_random_SDFKColorCurve() -> Dict[str, Any]:
        """
        Generate a completely random color curve without any input parameters. No adjustments by default.

        :return: Dictionary representing the generated random color curve.
        """
        curve_id = str(uuid.uuid4())

        # Use random choice for each channel's float curve type
        float_curve_types = {
            channel: random.choice(list(FloatCurveType))
            for channel in ["R", "G", "B", "A"]
        }

        # Generate float curves for each channel using the selected type
        float_curves = {
            channel: CurveHelper.generate_random_float_curve(
                min_keys=2,
                max_keys=100,
                float_curve_type=float_curve_types[channel]
            )
            for channel in ["R", "G", "B", "A"]
        }

        # Generate random adjustments
        randomize_adjustments = 0.0  # Example range for random adjustments
        adjustments = {
            "adjustHue": random.uniform(0, randomize_adjustments),
            "adjustSaturation": random.uniform(0, randomize_adjustments),
            "adjustBrightness": random.uniform(0, randomize_adjustments),
            "adjustBrightnessCurve": random.uniform(0, randomize_adjustments),
            "adjustVibrance": random.uniform(0, randomize_adjustments),
            "adjustMinAlpha": random.uniform(0, randomize_adjustments),
            "adjustMaxAlpha": random.uniform(0, randomize_adjustments)
        }

        # Get the current UTC timestamp
        utc_time_string = datetime.now(timezone.utc)

        # Base curve_json structure
        curve_json = {
            "floatCurves": float_curves,
            **adjustments,
            "assetImportData": {
                "_ClassName": "/Script/Engine.AssetImportData",
                "sourceData": {}
            },
            "created_at": utc_time_string
        }

        # Generate random meta offset curve types
        meta_x_offset_curve_type = random.choice(list(FloatCurveType)).name
        meta_y_offset_curve_type = random.choice(list(FloatCurveType)).name

        # Construct the final SDFKColorCurve instance
        sdfk_color_curve = SDFKColorCurve(
            uuid=curve_id,
            name=f"Random Curve {curve_id[:8]}",
            description="Randomly generated color curve",
            human_description=None,  # Initialize to None (or an empty string if preferred)
            machine_description=None,  # Initialize to None (or an empty string if preferred)
            human_tags_with_confidence=None,  # Initialize to None
            computer_vision_tags_with_confidence=None,  # Initialize to None
            nlp_keywords=[],  # Initialize to an empty list
            thumbnail_url=None,
            curve_json_url=None,
            search_json_url=None,
            R_float_curve_type=float_curve_types["R"].name,
            R_resolution_scale=1.0,
            R_noise_scale=0.1,
            G_float_curve_type=float_curve_types["G"].name,
            G_resolution_scale=1.0,
            G_noise_scale=0.1,
            B_float_curve_type=float_curve_types["B"].name,
            B_resolution_scale=1.0,
            B_noise_scale=0.1,
            A_float_curve_type=float_curve_types["A"].name,
            A_resolution_scale=1.0,
            A_noise_scale=0.1,
            meta_x_offset_curve_type=meta_x_offset_curve_type,
            meta_y_offset_curve_type=meta_y_offset_curve_type,
            meta_x_offset_scale=0.1,
            meta_y_offset_scale=0.1,
            meta_x_resolution_scale=1.0,
            meta_y_resolution_scale=1.0,
            meta_x_noise_scale=0.0,
            meta_y_noise_scale=0.0,
            created_at=utc_time_string,
            updated_at=utc_time_string
        )

        # Return the SDFKColorCurve instance and the curve_json
        return {
            "sdfk_color_curve": sdfk_color_curve.model_dump(),
            "curve_json": curve_json
        }


    @staticmethod  
    def generate_thumbnail_from_curve(curve_json, transparent_background=False):  
        """  
        Generate a thumbnail image from the color curve data and return it as a PIL Image.  
        Additionally, returns information about the gradients and spikiness of the channels.  
        """  
        texture_width, texture_height = 128, 128  
        try:  
            float_curves = curve_json['floatCurves']  
        except KeyError:  
            return None, None  
  
        # Validate presence of required channels  
        if not all(channel in float_curves for channel in ["R", "G", "B", "A"]):  
            return None, None  
  
        try:  
            red_times, red_values = CurveHelper.extract_curve_data(float_curves["R"]["keys"])  
            green_times, green_values = CurveHelper.extract_curve_data(float_curves["G"]["keys"])  
            blue_times, blue_values = CurveHelper.extract_curve_data(float_curves["B"]["keys"])  
            alpha_times, alpha_values = CurveHelper.extract_curve_data(float_curves["A"]["keys"])  
  
            # Normalize times to [0, 1]  
            red_normalized = np.interp(np.linspace(0, 1, texture_width), red_times, red_values)  
            green_normalized = np.interp(np.linspace(0, 1, texture_width), green_times, green_values)  
            blue_normalized = np.interp(np.linspace(0, 1, texture_width), blue_times, blue_values)  
            alpha_normalized = np.interp(np.linspace(0, 1, texture_width), alpha_times, alpha_values)  
  
            # Process alpha channel if needed  
            alpha_remapped = CurveHelper.process_alpha_channel(alpha_normalized)  
  
            # Calculate gradient (derivative) of each channel to analyze transitions  
            red_gradient = np.gradient(red_normalized)  
            green_gradient = np.gradient(green_normalized)  
            blue_gradient = np.gradient(blue_normalized)  
  
            # Calculate the spikiness of the alpha channel  
            alpha_gradient = np.gradient(alpha_remapped)  
            alpha_spikiness = np.std(alpha_gradient)  # Standard deviation as a measure of spikiness  
        except (IndexError, KeyError, TypeError):  
            return None, None  
  
        # Create an empty RGBA image with transparency  
        combined_image = np.zeros((texture_height, texture_width, 4), dtype=np.uint8)  
  
        for x in range(texture_width):  
            combined_image[:, x, 0] = int(CurveHelper.clamp(red_normalized[x] * 255, 0, 255))  
            combined_image[:, x, 1] = int(CurveHelper.clamp(green_normalized[x] * 255, 0, 255))  
            combined_image[:, x, 2] = int(CurveHelper.clamp(blue_normalized[x] * 255, 0, 255))  
            combined_image[:, x, 3] = int(CurveHelper.clamp(alpha_remapped[x], 0, 255))  
  
        combined_img = Image.fromarray(combined_image, 'RGBA')  
  
        if not transparent_background:  
            # Create a checkered background  
            checkered_background = CurveHelper.create_checkered_background(texture_width, texture_height)  
            # Composite the curve image onto the checkered background  
            combined_with_background = Image.alpha_composite(checkered_background, combined_img)  
        else:  
            combined_with_background = combined_img  
  
        # Gather gradient info for debugging or further analysis  
        gradient_info = {  
            'red_gradient_mean': np.mean(np.abs(red_gradient)),  
            'green_gradient_mean': np.mean(np.abs(green_gradient)),  
            'blue_gradient_mean': np.mean(np.abs(blue_gradient)),  
            'alpha_spikiness': alpha_spikiness  
        }  
  
        return combined_with_background, gradient_info  

    @staticmethod
    def compute_integral_from_curve_json(curve_json, width=128):
        """
        Computes the integral of a single grayscale row from color curve data in JSON.

        Parameters:
            curve_json (dict): JSON data defining the color curve.
            width (int): Width of the image (default is 128).

        Returns:
            row_integral (ndarray): 1D integral of the reconstructed grayscale row.
        """
        try:
            float_curves = curve_json['floatCurves']
            if not all(channel in float_curves for channel in ["R", "G", "B", "A"]):
                return None

            # Extract color curve data and normalize for the single row
            red_times, red_values = CurveHelper.extract_curve_data(float_curves["R"]["keys"])
            green_times, green_values = CurveHelper.extract_curve_data(float_curves["G"]["keys"])
            blue_times, blue_values = CurveHelper.extract_curve_data(float_curves["B"]["keys"])
            alpha_times, alpha_values = CurveHelper.extract_curve_data(float_curves["A"]["keys"])

            # Interpolate values across the width of the image
            red_normalized = np.interp(np.linspace(0, 1, width), red_times, red_values)
            green_normalized = np.interp(np.linspace(0, 1, width), green_times, green_values)
            blue_normalized = np.interp(np.linspace(0, 1, width), blue_times, blue_values)
            alpha_normalized = np.interp(np.linspace(0, 1, width), alpha_times, alpha_values)
            alpha_remapped = CurveHelper.process_alpha_channel(alpha_normalized)
            
            # Compute grayscale row (averaging RGB channels, modulated by alpha)
            grayscale_row = np.array([
                int((r + g + b) / 3 * (a / 255))  # Apply alpha modulation
                for r, g, b, a in zip(red_normalized * 255, green_normalized * 255, blue_normalized * 255, alpha_remapped)
            ])
            
            # Calculate the integral for the single row
            row_integral = grayscale_row.cumsum()
            
            return row_integral
        
        except KeyError as e:
            logging.error(f"KeyError while parsing curve data: {e}")
            return None
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None


    @staticmethod
    def step_through_curve(float_curve, step_size=0.1):
        """
        Generator that yields interpolated values of the float_curve at each step_size interval.

        :param float_curve: Dictionary containing curve data with 'keys'.
        :param step_size: Incremental step size between 0 and 1.
        """
        times, values = CurveHelper.extract_curve_data(float_curve['keys'])
        for t in np.arange(0, 1 + step_size, step_size):
            t = CurveHelper.clamp(t, 0, 1)
            interpolated_value = np.interp(t, times, values)
            yield t, interpolated_value

    @staticmethod
    def convert_to_UE_output_format(input_json):  
        # Load the input JSON  
        data = json.loads(input_json)  
        
        # Initialize the new format  
        new_data = {  
            "floatCurves": [],  
            "adjustHue": data.get("adjustHue", 0.0),  
            "adjustSaturation": data.get("adjustSaturation", 0.0),  
            "adjustBrightness": data.get("adjustBrightness", 0.0),  
            "adjustBrightnessCurve": data.get("adjustBrightnessCurve", 0.0),  
            "adjustVibrance": data.get("adjustVibrance", 0.0),  
            "adjustMinAlpha": data.get("adjustMinAlpha", 0.0),  
            "adjustMaxAlpha": data.get("adjustMaxAlpha", 0.0),  
            "assetImportData": data.get("assetImportData", {})  
        }  
        
        # Extract the nested structure from floatCurves
        float_curves = data.get("floatCurves", {})
        
        # Channels to include in the conversion (R, G, B, and A for alpha)
        for channel in ["R", "G", "B", "A"]:
            if channel in float_curves:
                float_curve = {  
                    "keys": float_curves[channel].get("keys", []),  
                    "defaultValue": float_curves[channel].get("defaultValue", 3.4028234663852886e+38),  
                    "preInfinityExtrap": float_curves[channel].get("preInfinityExtrap", "RCCE_Constant"),  
                    "postInfinityExtrap": float_curves[channel].get("postInfinityExtrap", "RCCE_Constant")  
                }
                # Append to the new floatCurves list  
                new_data["floatCurves"].append(float_curve)
        
        # Convert the new data back to JSON  
        return json.dumps(new_data, indent=4)
    

    @staticmethod
    def compute_integral_from_curve_data(curve_data, width=128, height=128):
        """
        Computes the integral image directly from curve data without generating a full image array.
        
        Parameters:
            curve_data (dict): Data defining the color curve for red, green, blue, and alpha channels.
            width (int): Width of the target image (typically 128 for color curves).
            height (int): Height of the target image (typically 128 for color curves).
        
        Returns:
            integral_image (ndarray): Integral image as a 2D array of size (height, width).
        """
        
        # Extract color curve data
        r_curve = curve_data.get('r_curve', [0] * width)
        g_curve = curve_data.get('g_curve', [0] * width)
        b_curve = curve_data.get('b_curve', [0] * width)
        a_curve = curve_data.get('a_curve', [1] * width)  # Alpha defaults to fully opaque
        
        # Calculate grayscale intensity for a single row (average RGB, modulated by alpha)
        row_values = np.array([
            int((r + g + b) / 3 * a)  # Applying alpha modulation if available
            for r, g, b, a in zip(r_curve, g_curve, b_curve, a_curve)
        ])
        
        # Calculate cumulative sum for this single row
        row_integral = row_values.cumsum()
        
        # Calculate the full integral image by multiplying row integrals for each row (since rows are identical)
        integral_image = np.outer(np.arange(1, height + 1), row_integral)
        
        return integral_image

