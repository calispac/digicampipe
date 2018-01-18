from ctapipe.image import hillas
import numpy as np
import astropy.units as u

def hillas_parameters(geom, image):
    unit = geom.pix_x.unit
    try:
       return hillas.hillas_parameters(geom, image)
    except hillas.HillasParameterizationError:
        return hillas.MomentParameters(
            size=None,
            cen_x=np.nan * unit,
            cen_y=np.nan * unit,
            length=np.nan * unit,
            width=np.nan * unit,
            r=np.nan * unit,
            phi=Angle(np.nan * u.rad),
            psi=Angle(np.nan * u.rad),
            miss=np.nan * unit,
            skewness=None,
            kurtosis=None,
        )



def calibrate_to_dl2(event_stream, reclean=False, shower_distance=80*u.mm):

    for i, event in enumerate(event_stream):

        for telescope_id in event.r0.tels_with_data:

            if i == 0:

                geom = event.inst.geom[telescope_id]

            dl1_camera = event.dl1.tel[telescope_id]

            image = dl1_camera.pe_samples

            mask = dl1_camera.cleaning_mask
            image[~mask] = 0.
            moments_first = hillas_parameters(geom, image)
            if reclean:
                mask_near_center = find_mask_near_center(
                    geom=geom,
                    cen_x=moments_first.cen_x,
                    cen_y=moments_first.cen_y,
                    distance=shower_distance)
                dl1_camera.cleaning_mask = dl1_camera.cleaning_mask & mask_near_center
                image[~dl1_camera.cleaning_mask] = 0
                moments = hillas_parameters(geom, image)
            else:
                moments = moments_first
        event.dl2.shower = moments
        event.dl2.energy = None
        event.dl2.classification = None

        yield event


def find_mask_near_center(geom, cen_x, cen_y, distance):

    d = np.sqrt((geom.pix_x - cen_x)**2 + (geom.pix_y - cen_y)**2)

    return d < distance


def find_mask_near_max(geom, distance, index_max):

    cen_x, cen_y = geom.pix_x[index_max], geom.pix_y[index_max]

    return find_mask_near_center(geom=geom, cen_x=cen_x, cen_y=cen_y, distance=distance)
