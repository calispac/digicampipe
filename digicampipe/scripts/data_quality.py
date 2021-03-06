"""
Make a quick data quality check
Usage:
  digicam-data-quality [options] [--] <INPUT>...

Options:
  --help                        Show this
  <INPUT>                       List of zfits input files. Typically a single
                                night observing a single source.
  --dark_filename=FILE          path to histogram of the dark files
  --parameters=FILE             Calibration parameters file path
  --time_step=N                 Time window in nanoseconds within which values
                                are computed
                                [Default: 5000000000]
  --output-fits=FILE            path to output fits file
                                [Default: ./data_quality.fits]
  --output-hist=FILE            path to output histo file
                                [Default: ./baseline_histo.pk]
  --aux_basepath=DIR            Base directory for the auxilary data.
                                If set to "search", It will try to determine it
                                from the input files.
                                [Default: search]
  --load                        If not present, the INPUT zfits files will be
                                analyzed and output fits and histo files will
                                be created. If present, that analysis is
                                skipped and the fits and histo files will serve
                                as input for plotting.
                                [Default: False]
  --rate_plot=FILE              path to the output plot history of rate.
                                Use "none" to not create the plot and "show" to
                                open an interactive plot instead of creating a
                                file.
                                [Default: none]
  --baseline_plot=FILE          path to the output plot history of the mean
                                baseline. Use "none" to not create the plot and
                                "show" to open an interactive plot instead of
                                creating a file.
                                [Default: none]
  --nsb_plot=FILE               path to the output plot history of the mean
                                Night Sky Background rate. Use "none" to not
                                create the plot and "show" to open an
                                interactive plot instead of creating a file.
                                [Default: none]
  --template=FILE               Pulse template file path
  --threshold_sample_pe=INT     threshold used in the shower rate estimation.
                                [Default: 20.]
  --disable_bar                 If used, the progress bar is not show while
                                reading files.
"""
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from astropy.table import Table
from ctapipe.core import Field
from ctapipe.io.containers import Container
from ctapipe.io.serializer import Serializer
from docopt import docopt
from histogram.histogram import Histogram1D
from numpy import ndarray
import os

from digicampipe.calib.baseline import fill_digicam_baseline, \
    subtract_baseline, compute_gain_drop, compute_nsb_rate,\
    compute_baseline_shift, fill_dark_baseline
from digicampipe.calib.tagging import tag_burst_from_moving_average_baseline
from digicampipe.calib.charge import compute_sample_photo_electron
from digicampipe.calib.cleaning import compute_3d_cleaning
from digicampipe.instrument.camera import DigiCam
from digicampipe.io.event_stream import calibration_event_stream, \
    add_slow_data_calibration
from digicampipe.utils.pulse_template import NormalizedPulseTemplate
from digicampipe.utils.docopt import convert_text


class DataQualityContainer(Container):
    time = Field(ndarray, 'Time')
    baseline = Field(ndarray, 'Baseline average over the camera')
    trigger_rate = Field(ndarray, 'Digicam trigger rate')
    shower_rate = Field(ndarray, 'Shower rate')
    nsb_rate = Field(ndarray, 'Averaged over the camera NSB rate')
    burst = Field(bool, 'Is there a burst')
    current_position_az = Field(ndarray, 'az info from DriveSystem')
    current_position_el = Field(ndarray, 'el info from DriveSystem')


def data_quality(
        files, dark_filename, time_step, fits_filename, load_files,
        histo_filename, rate_plot_filename, baseline_plot_filename,
        nsb_plot_filename, parameters_filename, template_filename,
        aux_basepath, threshold_sample_pe=20.,
        bias_resistance=1e4 * u.Ohm, cell_capacitance=5e-14 * u.Farad,
        disable_bar=False, aux_services=('DriveSystem',)

):
    input_dir = np.unique([os.path.dirname(file) for file in files])
    if len(input_dir) > 1:
        raise AttributeError("input files must be from the same directories")
    input_dir = input_dir[0]
    if aux_basepath.lower() == "search":
        aux_basepath = input_dir.replace('/raw/', '/aux/')
        print("auxiliary files are expected in", aux_basepath)
    with open(parameters_filename) as file:
        calibration_parameters = yaml.load(file)

    pulse_template = NormalizedPulseTemplate.load(template_filename)
    pulse_area = pulse_template.integral() * u.ns
    gain_integral = np.array(calibration_parameters['gain'])

    charge_to_amplitude = pulse_template.compute_charge_amplitude_ratio(7, 4)
    gain_amplitude = gain_integral * charge_to_amplitude
    crosstalk = np.array(calibration_parameters['mu_xt'])
    pixel_id = np.arange(1296)
    n_pixels = len(pixel_id)
    dark_histo = Histogram1D.load(dark_filename)
    dark_baseline = dark_histo.mean()
    if not load_files:
        events = calibration_event_stream(files, disable_bar=disable_bar)
        events = add_slow_data_calibration(
            events, basepath=aux_basepath, aux_services=aux_services
        )
        events = fill_digicam_baseline(events)
        events = fill_dark_baseline(events, dark_baseline)
        events = subtract_baseline(events)
        events = compute_baseline_shift(events)
        events = compute_nsb_rate(
            events, gain_amplitude, pulse_area, crosstalk, bias_resistance,
            cell_capacitance
        )
        events = compute_gain_drop(events, bias_resistance, cell_capacitance)
        events = compute_sample_photo_electron(events, gain_amplitude)
        events = tag_burst_from_moving_average_baseline(
            events, n_previous_events=100, threshold_lsb=5
        )
        events = compute_3d_cleaning(events, geom=DigiCam.geometry,
                                     threshold_sample_pe=threshold_sample_pe)
        init_time = 0
        baseline = 0
        count = 0
        shower_count = 0
        az = 0
        el = 0
        container = DataQualityContainer()
        file = Serializer(fits_filename, mode='w', format='fits')
        baseline_histo = Histogram1D(
            data_shape=(n_pixels,),
            bin_edges=np.arange(4096)
        )
        for i, event in enumerate(events):
            new_time = event.data.local_time
            if init_time == 0:
                init_time = new_time
            count += 1
            baseline += np.mean(event.data.digicam_baseline)
            az += event.slow_data.DriveSystem.current_position_az
            el += event.slow_data.DriveSystem.current_position_el
            time_diff = new_time - init_time
            if event.data.shower:
                shower_count += 1
            baseline_histo.fill(event.data.digicam_baseline.reshape(-1, 1))
            if time_diff > time_step and i > 0:
                trigger_rate = count / time_diff
                shower_rate = shower_count / time_diff
                baseline = baseline / count
                az = az / count
                el = el / count
                container.trigger_rate = trigger_rate
                container.baseline = baseline
                container.time = (new_time + init_time) / 2
                container.shower_rate = shower_rate
                container.burst = event.data.burst
                nsb_rate = event.data.nsb_rate
                container.nsb_rate = np.nanmean(nsb_rate).value
                container.current_position_az = az
                container.current_position_el = el
                baseline = 0
                count = 0
                init_time = 0
                shower_count = 0
                az = 0
                el = 0
                file.add_container(container)
        output_path = os.path.dirname(histo_filename)
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        baseline_histo.save(histo_filename)
        print(histo_filename, 'created.')
        file.close()
        print(fits_filename, 'created.')

    data = Table.read(fits_filename, format='fits')
    data = data.to_pandas()
    data['time'] = pd.to_datetime(data['time'], utc=True)
    data = data.set_index('time')

    if rate_plot_filename is not None:
        fig1 = plt.figure()
        ax = plt.gca()
        plt.xticks(rotation=70)
        plt.plot(data['trigger_rate']*1E9, '.', label='trigger rate')
        plt.plot(data['shower_rate']*1E9, '.', label='shower_rate')
        plt.ylabel('rate [Hz]')
        plt.legend({'trigger rate', 'shower rate'})
        xlim = plt.xlim()
        plt.xlim(xlim[0] - 1e-3, xlim[1] + 1e-3)  # extra min on the sides
        if rate_plot_filename == "show":
            plt.show()
        else:
            output_path = os.path.dirname(rate_plot_filename)
            if not (output_path == '' or os.path.exists(output_path)):
                os.makedirs(output_path)
            plt.savefig(rate_plot_filename)
        plt.close(fig1)

    if baseline_plot_filename is not None:
        fig2 = plt.figure(figsize=(8, 6))
        ax = plt.gca()
        data_burst = data[data['burst']]
        data_good = data[~data['burst']]
        plt.xticks(rotation=70)
        plt.plot(data_good['baseline'], '.', label='good', ms=2)
        plt.plot(data_burst['baseline'], '.', label='burst', ms=2)
        plt.ylabel('Baseline [LSB]')
        xlim = plt.xlim()
        plt.xlim(xlim[0] - 1e-3, xlim[1] + 1e-3)  # extra min on the sides
        if rate_plot_filename == "show":
            plt.show()
        else:
            output_path = os.path.dirname(baseline_plot_filename)
            if not (output_path == '' or os.path.exists(output_path)):
                os.makedirs(output_path)
            plt.savefig(baseline_plot_filename)
        plt.close(fig2)

    if nsb_plot_filename is not None:
        fig3 = plt.figure()
        ax = fig3.add_subplot(111)
        data.plot(y='nsb_rate', ax=ax)
        ax.set_ylabel('$f_{NSB}$ [GHz]')

        if nsb_plot_filename == "show":
            plt.show()
        else:
            fig3.savefig(nsb_plot_filename)
        plt.close(fig3)

    return


def entry():
    args = docopt(__doc__)
    files = args['<INPUT>']
    dark_filename = args['--dark_filename']
    time_step = float(args['--time_step'])
    fits_filename = args['--output-fits']
    histo_filename = args['--output-hist']
    load_files = args['--load']
    rate_plot_filename = convert_text(args['--rate_plot'])
    baseline_plot_filename = convert_text(args['--baseline_plot'])
    nsb_plot_filename = convert_text(args['--nsb_plot'])
    parameters_filename = args['--parameters']
    template_filename = args['--template']
    threshold_sample_pe = float(args['--threshold_sample_pe'])
    disable_bar = args['--disable_bar']
    aux_basepath = args['--aux_basepath']
    data_quality(
        files, dark_filename, time_step, fits_filename, load_files,
        histo_filename, rate_plot_filename, baseline_plot_filename,
        nsb_plot_filename, parameters_filename, template_filename,
        aux_basepath, threshold_sample_pe, disable_bar=disable_bar
    )


if __name__ == '__main__':
    entry()
