"""
For further reference on Hillas parameters refer to :
http://adsabs.harvard.edu/abs/1993ApJ...404..206R
and
https://github.com/cta-observatory/ctapipe
"""

import numpy as np


def correct_hillas(x, y, source_x=0, source_y=0):

    x = x - source_x
    y = y - source_y
    r = np.sqrt(x ** 2.0 + y ** 2.0)
    phi = np.arctan2(y, x)

    return x, y, r, phi


def compute_alpha(phi, psi):
    """
    :param phi: Polar angle of shower centroid
    :param psi: Orientation of shower major axis
    :return:
    """

    # phi and psi range [-np.pi, +np.pi]
    alpha = np.mod(phi - psi, np.pi)  # alpha in [0, np.pi]
    alpha = np.minimum(np.pi - alpha, alpha)  # put alpha in [0, np.pi/2]

    return alpha


def compute_miss(r, alpha):
    """
    :param r: Shower centroid distance to center of coordinates
    :param alpha: Shower orientation to center of coordinates
    :return:
    """
    miss = r * np.sin(alpha)

    return miss


def arrival_lessard(data, xis, mm_per_deg = 100):
    disp_ang = xis[None, :] * (1 - data['width']/data['length'])[:, None]
    disp_mm =  - np.sign(data['skewness'])[:, None] * mm_per_deg * disp_ang
    arrival_x = disp_mm * np.cos(data['psi'])[:, None] + data['x'][:, None]
    arrival_y = disp_mm * np.sin(data['psi'])[:, None] + data['y'][:, None]
    return arrival_x, arrival_y
