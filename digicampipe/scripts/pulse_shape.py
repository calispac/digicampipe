#!/usr/bin/env python
"""
Create an histogram of the pulse template for each pixel.
Usage:
  digicam-template [options] <input_files>...

Options:
  -h --help                 Show this screen.
  --output_hist=PATH        Output histogram file, if not given, we just append
                            ".npz" to the path of the 1st input file.
  --time_range_ns=LIST      Minimum and maximum time in ns w.r.t. half maximum
                            of the pulse during rise time [default: -10,40].
  --amplitude_range=LIST    Minimum and maximum amplitude of the template
                            normalised in integrated charge [default: -.1,0.4].
  --integration_range=LIST  Minimum and maximum indexes of samples used in the
                            integration for normalization of the pulse charge
                            [default: 10,30].
  --charge_range=LIST       Minimum and maximum integrated charge in LSB used
                            to build the histogram [default: 200,10000].
  --n_bin=INT               Number of bins for the 2d histograms
                            [default: 100].

"""
import numpy as np
from docopt import docopt

from digicampipe.calib.time import estimate_time_from_leading_edge
from digicampipe.io.event_stream import calibration_event_stream
from digicampipe.utils.hist2d import Histogram2dChunked
from digicampipe.calib.baseline import fill_digicam_baseline, \
    subtract_baseline, correct_wrong_baseline
from digicampipe.utils.docopt import convert_list_float, convert_list_int, \
    convert_int


def main(
        output_hist,
        input_files,
        time_range_ns=(-10., 40.),
        amplitude_range=(-0.1, 0.4),
        integration_range=(10, 30),
        charge_range=(200., 10000.),
        n_bin=100,
):
    charge_min = np.min(charge_range)
    charge_max = np.max(charge_range)
    integration_min = np.min(integration_range)
    integration_max = np.max(integration_range)
    events = calibration_event_stream(input_files)
    events = fill_digicam_baseline(events)
    if "SST1M_01_201805" in input_files[0]:  # fix data in May
        print("WARNING: correction of the baselines applied.")
        events = correct_wrong_baseline(events)
    events = subtract_baseline(events)
    histo = None
    n_sample = 0
    n_pixel = 0
    for e in events:
        adc = e.data.adc_samples
        integral = adc[:, slice(integration_min, integration_max)].sum(axis=1)
        adc_norm = adc / integral[:, None]
        arrival_time_in_ns = estimate_time_from_leading_edge(adc) * 4
        if histo is None:
            n_pixel, n_sample = adc_norm.shape
            histo = Histogram2dChunked(
                shape=(n_pixel, n_bin, n_bin),
                range=[time_range_ns, amplitude_range]
            )
        else:
            assert adc_norm.shape[0] == n_pixel
            assert adc_norm.shape[1] == n_sample
        time_in_ns = np.arange(n_sample) * 4
        # charge < 10 pe (noisy) or > 500 pe (saturation) => bad_charge
        # 1 pe <=> 20 integral
        bad_charge = np.logical_or(
            integral < charge_min,
            integral > charge_max
        )
        arrival_time_in_ns[bad_charge] = -np.inf  # ignored by histo
        histo.fill(
            x=time_in_ns[None, :] - arrival_time_in_ns[:, None],
            y=adc_norm
        )
    histo.save(output_hist)
    print('2D histogram of pulse shape for all pixel saved as', output_hist)


def entry():
    args = docopt(__doc__)
    output_hist = args['--output_hist']
    inputs = args['<input_files>']
    time_range_ns = convert_list_float(args['--time_range_ns'])
    amplitude_range = convert_list_float(args['--amplitude_range'])
    integration_range = convert_list_int(args['--integration_range'])
    charge_range = convert_list_float(args['--charge_range'])
    n_bin = convert_int(args['--n_bin'])
    if output_hist is None:
        output_hist = inputs[0] + '.npz'
    main(
        output_hist=output_hist,
        input_files=inputs,
        time_range_ns=time_range_ns,
        amplitude_range=amplitude_range,
        integration_range=integration_range,
        charge_range=charge_range,
        n_bin=n_bin
    )


if __name__ == '__main__':
    entry()
