# streamlit_helper.py

import streamlit as st  
import matplotlib.pyplot as plt  
import numpy as np  
from scipy.interpolate import interp1d  
from curve_helper import CurveHelper
from enums import InterpMode

def plot_curves(curve_data, thumbnail=None):  
    fig, ax = plt.subplots(figsize=(4, 4))  # Adjust the figure size  
  
    if thumbnail:  
        # Resize the thumbnail to fit the plot  
        thumbnail = thumbnail.resize((int(fig.bbox.bounds[2]), int(fig.bbox.bounds[3])))  
        ax.imshow(thumbnail, aspect='auto', extent=[0, 1, 0, 1], alpha=0.5, zorder=-1)  
  
    # Define custom colors  
    colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFFFF']  # Red, Green, Blue, White  
    channels = ['R', 'G', 'B', 'A']  
  
    for channel, color in zip(channels, colors):  
        if channel in curve_data:  
            times, values = CurveHelper.extract_curve_data(curve_data[channel]['keys'])  
  
            # Ensure times and values cover the full range from 0 to 1  
            if times[0] > 0:  
                times.insert(0, 0)  
                values.insert(0, values[0])  
            if times[-1] < 1:  
                times.append(1)  
                values.append(1)  # Assuming the last value should be extended to 1  
  
            # Clamp values to the range [0, 1]  
            values = np.clip(values, 0, 1)  
  
            # Read interpolation mode from the JSON data
            interp_mode_str = curve_data[channel]['keys'][0].get('interpMode', 'RCIM_Linear')
            interp_mode = InterpMode(interp_mode_str)
            interp_kind = interp_mode.to_plotting_kind()
  
            if interp_kind == "constant":
                # Handle constant interpolation separately
                ax.step(times, values, where='post', label=channel, color=color, linewidth=0.4, alpha=1, zorder=2)
            else:
                # Interpolate values for a smoother curve  
                interp_func = interp1d(times, values, kind=interp_kind)  
                smooth_times = np.linspace(0, 1, 500)  
                smooth_values = interp_func(smooth_times)  
  
                # Plot the glow effect by plotting the same line multiple times with increasing linewidth and decreasing alpha  
                for glow_width, alpha in zip([1, 3], [0.1, 0.1]):  
                    ax.plot(smooth_times, smooth_values, color=color, linewidth=glow_width, alpha=alpha, zorder=1)  
  
                # Plot the main line  
                ax.plot(smooth_times, smooth_values, label=channel, color=color, linewidth=0.4, alpha=1, zorder=2)  
  
    # Configure the plot aesthetics  
    ax.set_xlim([0, 1])  
    ax.set_ylim([0, 1])  
    ax.set_facecolor('#1A1A1A')  # Almost black background  
    fig.patch.set_facecolor('#2E2E2E')  
    ax.grid(color='white', linestyle='-', linewidth=0.2)  
    ax.tick_params(axis='x', colors='white')  
    ax.tick_params(axis='y', colors='white')  
    ax.spines['left'].set_color('white')  
    ax.spines['bottom'].set_color('white')  
    ax.spines['top'].set_color('white')  
    ax.spines['right'].set_color('white')  
    ax.title.set_color('white')  
    ax.xaxis.label.set_color('white')  
    ax.yaxis.label.set_color('white')  
  
    st.pyplot(fig)