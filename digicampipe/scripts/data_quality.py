"""
Make a quick data quality check
Usage:
  digicam-data-quality [options] [--] <INPUT>...

Options:
  --help            Show this
  --time_step=N     Time window in nanoseconds within which values are computed
                    [Default: 5000000000]
  --output=PATH     Output path
                    [Default: .]
  --compute
  --display
"""
from docopt import docopt
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numpy import ndarray
from ctapipe.io.containers import Container
from ctapipe.io.serializer import Serializer
from ctapipe.core import Field
from astropy.table import Table

from digicampipe.io.event_stream import calibration_event_stream


class DataQualityContainer(Container):

    time = Field(ndarray, 'time')
    baseline = Field(ndarray, 'baseline average over the camera')
    trigger_rate = Field(ndarray, 'Digicam trigger rate')


def entry():

    args = docopt(__doc__)
    files = args['<INPUT>']

    time_step = float(args['--time_step'])
    output_path = args['--output']
    filename = os.path.join(output_path, 'data_quality.fits')

    if not os.path.exists(output_path):
        raise IOError('Path {} for output '
                      'does not exists \n'.format(output_path))

    if args['--compute']:

        events = calibration_event_stream(files, baseline_new=True)

        time = 0
        baseline = 0
        count = 0

        container = DataQualityContainer()
        file = Serializer(filename, mode='w', format='fits')

        for i, event in enumerate(events):

            new_time = event.data.local_time
            count += 1
            baseline += np.mean(event.data.digicam_baseline)
            time_diff = new_time - time
            time = new_time

            if time_diff > time_step and i > 0:

                trigger_rate = count / time_diff
                baseline = baseline / count

                container.trigger_rate = trigger_rate
                container.baseline = baseline
                container.time = time

                baseline = 0
                count = 0

                file.add_container(container)

        file.close()

    if args['--display']:

        data = Table.read(filename, format='fits')
        data = data.to_pandas()

        data['time'] = pd.to_datetime(data['time'])
        data = data.set_index('time')

        plt.figure()
        plt.plot(data['trigger_rate']*1E9)
        plt.ylabel('Trigger rate [Hz]')

        plt.figure()
        plt.plot(data['baseline'])
        plt.ylabel('Baseline [LSB]')

        plt.show()

    return


if __name__ == '__main__':

    entry()