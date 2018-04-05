#!/usr/bin/env python
'''
Do the Single Photoelectron anaylsis

Usage:
  spe.py [options] [FILE] [INPUT ...]

Options:
  -h --help               Show this screen.
  --max_events=N          Maximum number of events to analyse
  -o FILE --output=FILE.  Output file.
  -i INPUT --input=INPUT. Input files.
  -c --compute            Compute the data.
  -f --fit                Fit.
  -d --display            Display.
  -v --debug              Enter the debug mode.
  -p --pixel=<PIXEL>      Give a list of pixel IDs.
'''
import os
from docopt import docopt
from tqdm import tqdm

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks_cwt
from scipy import ndimage
import scipy
import pandas as pd

import peakutils
from iminuit import Minuit, describe
from probfit import Chi2Regression

from ctapipe.io import HDF5TableWriter, HDF5TableReader
from digicampipe.io.event_stream import calibration_event_stream
from digicampipe.utils.pdf import gaussian, single_photoelectron_pdf
from digicampipe.utils.exception import PeakNotFound
from digicampipe.io.containers_calib import SPEResultContainer, CalibrationHistogramContainer
from histogram.histogram import Histogram1D


def compute_gaussian_parameters_highest_peak(bins, count, snr=4, debug=False):

    temp = count.copy()
    mask = ((count / np.sqrt(count)) > snr) * (count > 0)
    temp[~mask] = 0
    peak_indices = scipy.signal.argrelmax(temp, order=4)[0]

    if not len(peak_indices) > 0:

        raise PeakNotFound('Could not detect enough peaks in the histogram\n'
                           'N_peaks found : {} \n '
                           'SNR : {} \n'.format(len(peak_indices), snr))

    if len(peak_indices) == 1:

        mask = (count > 0) * (bins < bins[peak_indices[0]])
        val = np.min(count[mask])
        peak_indices = np.insert(peak_indices, 0, val)

    x_peaks = np.array(bins[peak_indices])
    # y_peaks = np.array(count[peak_indices])

    peak_distance = np.diff(x_peaks)
    peak_distance = np.mean(peak_distance) // 2
    peak_distance = peak_distance.astype(np.int)

    highest_peak_index = np.argmax(count)

    highest_peak_range = [
        highest_peak_index + i
        for i in range(-peak_distance, peak_distance)
    ]

    bins = bins[highest_peak_range]
    count = count[highest_peak_range]

    mask = count > 0
    bins = bins[mask]
    count = count[mask]

    parameter_names = describe(gaussian)
    del parameter_names[0]

    mean = np.average(bins, weights=count)
    std = np.average((bins - mean)**2, weights=count)
    std = np.sqrt(std)
    amplitude = np.sum(count)
    parameter_init = [mean, std, amplitude]
    parameter_init = dict(zip(parameter_names, parameter_init))

    bound_names = []

    for name in parameter_names:

        bound_names.append('limit_' + name)

    bounds = [(0, np.max(bins)),
              (0.5 * std, 1.5 * std),
              (0.5 * amplitude, 1.5 * amplitude)]

    bounds = dict(zip(bound_names, bounds))

    gaussian_minimizer = Chi2Regression(gaussian, bins, count,
                                        error=np.sqrt(count))

    minuit = Minuit(gaussian_minimizer, **parameter_init, **bounds,
                    print_level=0, pedantic=False)
    minuit.migrad()

    if debug:

        plt.figure()
        plt.plot(bins, count)
        plt.plot(bins, gaussian(bins, **minuit.values))
        plt.show()

    return minuit.values, minuit.errors


def build_raw_data_histogram(events):

    for count, event in tqdm(enumerate(events)):

        if count == 0:

            n_pixels = len(event.pixel_id)
            adc_histo = Histogram1D(
                data_shape=(n_pixels, ),
                bin_edges=np.arange(0, 4095, 1),
                axis_name='[LSB]'
            )

        adc_histo.fill(event.data.adc_samples)

    return CalibrationHistogramContainer().from_histogram(adc_histo)


def fill_histogram(events, id, histogram):

    for event in events:

        event.histo[id] = histogram

        yield event


def fill_electronic_baseline(events):

    for event in events:

        event.data.baseline = event.histo[0].mode

        yield event


def subtract_baseline(events):

    for event in events:

        baseline = event.data.baseline

        event.data.adc_samples = event.data.adc_samples.astype(baseline.dtype)
        event.data.adc_samples -= baseline[..., np.newaxis]

        yield event


def find_pulse_1(events, threshold, min_distance):

    for count, event in enumerate(events):

        pulse_mask = np.zeros(event.adc_samples.shape, dtype=np.bool)

        for pixel_id, adc_sample in enumerate(event.data.adc_samples):

            peak_index = peakutils.indexes(adc_sample, threshold, min_distance)
            pulse_mask[pixel_id, peak_index] = True

        event.data.pulse_mask = pulse_mask

        yield event


def plot_adc_samples(events, pixel_id):

    plt.figure()

    for i, event in enumerate(events):

        if i == 0:
            pixel_id = event.pixel_id[pixel_id]
        plt.plot(event.data.adc_samples[pixel_id])
        plt.show()

        yield event


def find_pulse_2(events, threshold_sigma, widths, **kwargs):

    for count, event in enumerate(events):

        if count == 0:

            threshold = threshold_sigma * event.histo[0].std

        adc_samples = event.data.adc_samples
        pulse_mask = np.zeros(adc_samples.shape, dtype=np.bool)

        for pixel_id, adc_sample in enumerate(adc_samples):

            peak_index = find_peaks_cwt(adc_sample, widths, **kwargs)
            peak_index = peak_index[
                adc_sample[peak_index] > threshold[pixel_id]
            ]
            pulse_mask[pixel_id, peak_index] = True

        event.data.pulse_mask = pulse_mask

        yield event


def compute_charge(events, integral_width, maximum_width=2):
    """

    :param events: a stream of events
    :param integral_width: width of the integration window
    :param maximum_width: width of the region (bin size) to compute charge,
    maximum value is retained. (not implemented yet)
    :return:
    """

    # bins = np.arange(-maximum_width, maximum_width + 1, 1)

    for count, event in enumerate(events):

        adc_samples = event.data.adc_samples
        pulse_mask = event.data.pulse_mask

        convolved_signal = ndimage.convolve1d(
            adc_samples,
            np.ones(integral_width),
            axis=-1
        )

        charges = np.zeros(convolved_signal.shape) * np.nan
        charges[pulse_mask] = convolved_signal[pulse_mask]
        event.data.reconstructed_charge = charges


        # charges = np.zeros(convolved_signal.shape + bins.shape) * np.nan
        # pulse_mask_indices = np.where(pulse_mask)

        # for i, bin in enumerate(bins):

#            indices = pulse_mask_indices[-1] + bin
#            indices[indices >= convolved_signal.shape[-1]] = convolved_signal.shape[-1] - 1
#            indices[indices < 0] = 0
#            indices = pulse_mask_indices[:-1] + (indices, )
#            charges[indices + (i, )] = convolved_signal[indices]

#        charges = np.nanmax(charges, axis=-1)
#       charges_max = np.zeros(charges.shape) * np.nan
#        charges_max[pulse_mask] = np.nanmax(charges, axis=-1)
        # event.data.reconstructed_charge = charges_max

        yield event


def compute_amplitude(events, maximum_width=2):

    for count, event in enumerate(events):

        adc_samples = event.data.adc_samples
        pulse_indices = event.data.pulse_mask

        charges = np.ones(adc_samples.shape) * np.nan
        charges[pulse_indices] = adc_samples[pulse_indices]
        event.data.reconstructed_amplitude = charges

        yield event


def spe_fit_function(x, baseline, gain, sigma_e, sigma_s, a_1, a_2, a_3, a_4):

    amplitudes = np.array([a_1, a_2, a_3, a_4])
    N = np.arange(1, amplitudes.shape[0] + 1, 1)
    sigma = sigma_e**2 + N * sigma_s**2

    value = x - (N * gain + baseline)[..., np.newaxis]
    value = value**2
    value /= 2 * sigma[..., np.newaxis]
    temp = np.exp(-value) * (amplitudes / np.sqrt(sigma))[..., np.newaxis]
    temp = np.sum(temp, axis=0)
    temp /= np.sqrt(2 * np.pi)

    return temp


def compute_fit_init_param(x, y, snr=4, sigma_e=None, debug=False):

    init_params = compute_gaussian_parameters_highest_peak(x, y, snr=snr,
                                                           debug=debug)[0]
    del init_params['mean'], init_params['amplitude']
    init_params['baseline'] = 0

    if sigma_e is None:

        init_params['sigma_s'] = init_params['sigma'] / 2
        init_params['sigma_e'] = init_params['sigma_s']

    else:

        init_params['sigma_s'] = init_params['sigma'] ** 2 - sigma_e ** 2
        init_params['sigma_s'] = np.sqrt(init_params['sigma_s'])
        init_params['sigma_e'] = sigma_e

    del init_params['sigma']

    temp = y.copy()
    mask = ((temp / np.sqrt(temp)) > snr) * (temp > 0)
    temp[~mask] = 0
    peak_indices = scipy.signal.argrelmax(temp, order=4)[0]

    if not len(peak_indices) > 1:

        raise PeakNotFound('Could not detect enough peak in the histogram \n'
                           'N_peaks : {} \n'
                           'SNR : {} \n'.format(len(peak_indices), snr))

    peaks_y = np.array(y[peak_indices])
    gain = np.array(x[peak_indices])
    gain = np.diff(gain)
    gain = np.mean(gain)

    init_params['gain'] = gain

    for i in range(1, max(min(peaks_y.shape[0], 4), 4)):

        val = 0

        if i < peaks_y.shape[0]:

            val = peaks_y[i]

        init_params['a_{}'.format(i)] = val

    return init_params


def fit_spe(x, y, y_err, snr=4, debug=False):

    params_init = compute_fit_init_param(x, y, snr=snr, debug=debug)

    # print(params_init)

    mask = x > (params_init['baseline'] + params_init['gain'] / 2)
    mask *= y > 0

    x = x[mask]
    y = y[mask]
    y_err = y_err[mask]

    n_entries = np.sum(y)

    keys = [
        'limit_baseline', 'limit_gain', 'limit_sigma_e', 'limit_sigma_s',
        'limit_a_1', 'limit_a_2', 'limit_a_3', 'limit_a_4'
    ]

    values = [
        (0, params_init['gain']/2),
        (0, 2 * params_init['gain']),
        (0, 2 * params_init['sigma_e']),
        (0, 2 * params_init['sigma_s']),
        (0, n_entries),
        (0, n_entries),
        (0, n_entries),
        (0, n_entries),
        ]

    param_bounds = dict(zip(keys, values))

    # def f(baseline, gain, sigma_e, sigma_s, a_1, a_2, a_3, a_4):
    #     return minimiser(
    #         x,
    #         y,
    #         y_err,
    #         spe_fit_function,
    #         baseline,
    #         gain,
    #         sigma_e,
    #         sigma_s,
    #         a_1,
    #         a_2,
    #         a_3,
    #         a_4
    #     )

    chi2 = Chi2Regression(single_photoelectron_pdf, x, y, y_err)
    m = Minuit(
        chi2,
        **params_init,
        **param_bounds,
        print_level=0,
        pedantic=False
    )
    m.migrad()

    '''
    try:
        m.minos()
    except RuntimeError:
        pass

    '''

    if debug:
        plt.figure()
        plt.plot(x, y)
        plt.plot(x, single_photoelectron_pdf(x, **m.values))
        print(m.values, m.errors)
        plt.show()

    return m.values, m.errors, params_init, param_bounds


def minimiser(x, y, y_err, f, *args):

    return np.sum(((y - f(x, *args)) / y_err)**2)


def build_spe(events, max_events):

    for i, event in tqdm(zip(range(max_events), events), total=max_events):

        if i == 0:

            n_pixels = len(event.pixel_id)

            spe_charge = Histogram1D(
                data_shape=(n_pixels,),
                bin_edges=np.arange(-20, 500, 1)
            )
            spe_amplitude = Histogram1D(data_shape=(n_pixels,),
                                        bin_edges=np.arange(-20, 200, 1))

        spe_charge.fill(event.data.reconstructed_charge)
        spe_amplitude.fill(event.data.reconstructed_amplitude)

    spe_charge = CalibrationHistogramContainer().from_histogram(spe_charge)
    spe_amplitude = CalibrationHistogramContainer().from_histogram(
        spe_amplitude)

    return spe_charge, spe_amplitude


def save_container(container, filename, group_name, table_name):

    with HDF5TableWriter(filename, mode='a', group_name=group_name) as h5:
        h5.write(table_name, container)


def save_event_data(events, filename, group_name):

    with HDF5TableWriter(filename, mode='a', group_name=group_name) as h5:

        for event in events:

            h5.write('waveforms', event.data)

            yield event


def plot_event(events, pixel_id):

    for event in events:

        event.data.plot(pixel_id=pixel_id)
        plt.show()

        yield event


def _convert_pixel_args(text):

    if text is not None:

        text = text.split(',')
        pixel_id = list(map(int, text))
        pixel_id = np.array(pixel_id)

    else:

        pixel_id = [...]

    return pixel_id


def main(args):

    files = args['INPUT']
    debug = args['--debug']
    telescope_id = 1
    max_events = int(args['--max_events'])
    output_file = args['FILE']
    pixel_id = _convert_pixel_args(args['--pixel'])

    if args['--compute']:

        if not os.path.exists(output_file):

            events = calibration_event_stream(files,
                                              telescope_id=telescope_id,
                                              pixel_id=pixel_id,
                                              max_events=max_events)
            # events = plot_adc_samples(events, pixel_id=0)
            raw_histo = build_raw_data_histogram(events)
            save_container(raw_histo, output_file, 'histo', 'raw_lsb')

            events = calibration_event_stream(files,
                                              telescope_id=telescope_id,
                                              max_events=max_events,
                                              pixel_id=pixel_id)

            events = fill_histogram(events, 0, raw_histo)
            events = fill_electronic_baseline(events)
            events = subtract_baseline(events)
            # events = normalize_adc_samples(events, std)
            # events = find_pulse_1(events, 0.5, 20)
            events = find_pulse_2(events, widths=[5, 6], threshold_sigma=2)
            # events = normalize_adc_samples(events, 1./std)

            events = compute_charge(events, integral_width=7)
            events = compute_amplitude(events)
            # events = save_event_data(events, output_file, 'data')

            if debug:
                events = plot_event(events, 0)

            spe_charge, spe_amplitude = build_spe(events, max_events)

            save_container(spe_charge, output_file, 'histo', 'spe_charge')
            save_container(
                spe_amplitude,
                output_file,
                'histo',
                'spe_amplitude')

        else:

            raise IOError('File {} already exists'.format(output_file))

    if args['--fit']:

        # with HDF5TableReader('spe_analysis.hdf5') as h5_table:

        #     spe_charge = h5_table.read('/histo/spe_charge',
        #                                CalibrationHistogramContainer())

        #     spe_amplitude = h5_table.read('/histo/spe_amplitude',
        #                                   CalibrationHistogramContainer())

        #     spe_charge = convert_container_to_histogram(next(spe_charge))
        #     spe_amplitude = convert_container_to_histogram(next(spe_amplitude))

        # spe = spe_charge
        spe = Histogram1D.load('temp.pk')
        spe.draw(index=(10, ), log=True)
        plt.show()

        parameters = {
            'a_1': [],
            'a_2': [],
            'a_3': [],
            'a_4': [],
            'sigma_s': [],
            'sigma_e': [],
            'gain': [],
            'baseline': [],
            'pixel_id': [],
        }

        n_pixels = spe.data.shape[0]

        results = SPEResultContainer()

        with HDF5TableWriter(output_file, 'analysis', mode='a') as h5:

            for pixel_id in tqdm(range(n_pixels)):

                try:

                    params, params_err, params_init, params_bound = fit_spe(
                        spe._bin_centers(),
                        spe.data[pixel_id],
                        spe.errors(index=pixel_id), snr=3, debug=debug)

                    for key, val in params.items():
                        parameters[key].append(val)

                    parameters['pixel_id'].append(pixel_id)

                    for key, val in params_init.items():

                        results.init[key] = val
                        results.param[key] = params[key]
                        results.param_errors[key] = params_err[key]
                        results.bound_min[key] = params_bound['limit_' + key][0]
                        results.bound_max[key] = params_bound['limit_' + key][1]

                    for key, val in results.items():

                        results[key]['pixel'] = pixel_id

                    for key, val in results.items():

                        h5.write('spe_' + key, val)

                except PeakNotFound as e:

                    print(e)
                    print('Could not fit for pixel_id : {}'.format(pixel_id))

        for key, val in parameters.items():
            parameters[key] = np.array(val)

        np.savez('spe_fit_params.npz', **parameters)

    if args['--display']:

        with HDF5TableReader(output_file, mode='r') as h5:

            for node in h5._h5file.iter_nodes('/histo'):

                histo_path = node._v_name
                histo_path = '/histo/' + histo_path

                histo = CalibrationHistogramContainer()

                for _, event in zip(range(1), h5.read(histo_path, histo)):

                    histo = event.to_histogram()

                histo.draw(index=(0, ), log=True)

        plt.show()

        parameters = pd.HDFStore(output_file, mode='r')
        parameters = parameters['analysis/spe_param']
        n_entries = 0

        for i in range(1, 3):

            n_entries += parameters['a_{}'.format(i)]

        xt = (n_entries - parameters['a_1']) / n_entries
        dark_count = n_entries / (4 * 92 * 10000)

        for key, val in parameters.items():

            fig = plt.figure()
            axes = fig.add_subplot(111)
            axes.hist(val, bins='auto', log=True)
            axes.set_xlabel(key + ' []')
            axes.set_ylabel('count []')

        plt.figure()
        plt.hist(xt, bins='auto', log=True)
        plt.xlabel('XT []')

        plt.figure()
        plt.hist(dark_count, bins='auto', log=True)
        plt.xlabel('dark count rate [GHz]')

        # with HDF5TableReader('spe_analysis.hdf5') as h5_table:

        #     spe_charge = h5_table.read('/histo/spe_charge',
        #                                       CalibrationHistogramContainer())

        #     spe_amplitude = h5_table.read('/histo/spe_amplitude',
        #                                           CalibrationHistogramContainer())

        #    # raw_histo = h5_table.read('/histo/raw_lsb', CalibrationHistogramContainer())

        #     spe_charge = convert_container_to_histogram(next(spe_charge))
        #    # raw_histo = convert_container_to_histogram(next(raw_histo))
        #     spe_amplitude = convert_container_to_histogram(next(spe_amplitude))

        spe_charge = Histogram1D.load('temp_10000.pk')

        # raw_histo.draw(index=(10, ))
        spe_charge.draw(index=(10, ), log=True)
        # spe_amplitude.draw(index=(10, ))

        plt.show()

    return


def entry():
    args = docopt(__doc__)
    main(args)


if __name__ == '__main__':
    entry()
