import numpy as np
from digicampipe.utils import utils,calib


def calibrate_to_r1(event_stream, calib_container, time_integration_options):
    cleaning_threshold = 3.


    pixel_list = list(range(1296))

    for i_evt,event in enumerate(event_stream):
        if i_evt%100 == 0 : print('Evt_number %d'%i_evt)
        # Check that the event is physics trigger
        if event.trig.trigger_flag != 0:
            yield event
            continue
        # Check that there were enough random trigger to compute the baseline
        if not calib_container.baseline_ready :
            yield event
            continue

        for telescope_id in event.r0.tels_with_data:
            # Get the R0 and R1 containers
            r0_camera = event.r0.tel[telescope_id]
            r1_camera = event.r1.tel[telescope_id]
            # Get the ADCs
            adc_samples = np.array(list(r0_camera.adc_samples.values()))
            # Get the mean and standard deviation
            r1_camera.pedestal_mean = calib_container.baseline
            r1_camera.pedestal_std = calib_container.std_dev
            # Subtract baseline to the data
            adc_samples = adc_samples.astype(dtype = float) - r1_camera.pedestal_mean.reshape(-1,1)
            r1_camera.adc_samples = adc_samples
            # Compute the gain drop and NSB
            if calib_container.dark_baseline is None :
                # compute NSB and Gain drop from STD
                r1_camera.gain_drop = calib.compute_gain_drop(r1_camera.pedestal_std ,'std')
                r1_camera.nsb  = calib.compute_nsb_rate(r1_camera.pedestal_std ,'std')
            else:
                # compute NSB and Gain drop from baseline shift
                r1_camera.gain_drop = calib.compute_gain_drop(r1_camera.pedestal_mean,'mean')
                r1_camera.nsb  = calib.compute_nsb_rate(r1_camera.pedestal_mean,'mean')

            gain_init = calib.get_gains()
            gain = gain_init * r1_camera.gain_drop

            # mask pixels which goes above N sigma
            mask_for_cleaning = adc_samples > cleaning_threshold  * r1_camera.pedestal_std.reshape(-1,1)
            r1_camera.cleaning_mask = np.any(mask_for_cleaning,axis=-1)

            # Integrate the data
            adc_samples = utils.integrate(adc_samples, time_integration_options['window_width'])

            # Compute the charge
            r1_camera.pe_samples, r1_camera.time_bin = utils.extract_charge(adc_samples, time_integration_options['mask'],
                                    time_integration_options['mask_edges'],
                                    time_integration_options['peak'],
                                    time_integration_options['window_start'],
                                    time_integration_options['threshold_saturation'])

            r1_camera.pe_samples = r1_camera.pe_samples / gain

            r1_camera.time_bin = np.array([r1_camera.time_bin])*4 + event.r0.tel[telescope_id].local_camera_clock
            event.level = 1

            yield event

