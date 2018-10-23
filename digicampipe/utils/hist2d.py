import numpy as np
from astropy.io import fits


class Histogram2d:
    def __init__(self, shape, range):
        self.histo = np.zeros(shape, dtype='u2')
        self.range = range
        self.xedges = None
        self.yedges = None

    def fill(self, x, y):
        for pixel_id in range(len(x)):
            H, xedges, yedges = np.histogram2d(
                x[pixel_id],
                y[pixel_id],
                bins=self.histo.shape[1:],
                range=self.range
            )
            self.histo[pixel_id] += H.astype('u2')
        self.xedges, self.yedges = xedges, yedges

    def contents(self):
        return self.histo

    def fit_y(self):
        h = self.contents()
        n = h.sum(axis=-1)
        x_bin_center = 0.5 * (self.xedges[1:] + self.xedges[:-1])
        y_bin_center = 0.5 * (self.yedges[1:] + self.yedges[:-1])
        x_bin_centers = []
        means_y = []
        stds_y = []
        for pixel in range(h.shape[0]):
            x_bin_non_empty = n[pixel, :] > 10
            h_pix = h[pixel, x_bin_non_empty, :]
            n_pix = n[pixel, x_bin_non_empty]
            x_bin_centers.append(x_bin_center[x_bin_non_empty])
            mean_y = (h_pix * y_bin_center[None, :]).sum(axis=-1) / n_pix
            means_y.append(mean_y)
            squared_sum_y = (y_bin_center[None, :] - mean_y[:, None]) ** 2
            std_y = np.sqrt((h_pix * squared_sum_y).sum(axis=-1) / (n_pix - 1))
            stds_y.append(std_y)
        return x_bin_centers, means_y, stds_y

    def save(self, path, **kwargs):
        hdu_histo = fits.PrimaryHDU(data=self.contents())
        hdu_range = fits.ImageHDU(data=self.range)
        hdu_xedges = fits.ImageHDU(data=self.xedges)
        hdu_yedges = fits.ImageHDU(data=self.yedges)
        hdul = fits.HDUList([hdu_histo, hdu_range, hdu_xedges, hdu_yedges])
        hdul.writeto(path)

    @classmethod
    def load(cls, path):
        with fits.open(path) as hdul:
            histo = hdul[0].data
            range = hdul[1].data
            obj = Histogram2d(histo.shape, range)
            obj.histo = histo
            obj.xedges = hdul[2].data
            obj.yedges = hdul[3].data
        return obj


class Histogram2dChunked(Histogram2d):
    def __init__(self, shape, range, buffer_size=1000):
        super().__init__(shape=shape, range=range)

        self.buffer_size = buffer_size
        self.buffer_x = None
        self.buffer_y = None
        self.buffer_counter = 0

    def fill(self, x, y):
        if self.buffer_counter == self.buffer_size:
            self.__fill_histo_from_buffer()

        if self.buffer_x is None:
            self.__reset_buffer(x, y)

        self.buffer_x[self.buffer_counter] = x
        self.buffer_y[self.buffer_counter] = y
        self.buffer_counter += 1

    def __reset_buffer(self, x, y):
        self.buffer_x = np.zeros(
            (self.buffer_size, *x.shape),
            dtype=x.dtype
        )
        self.buffer_y = np.zeros(
            (self.buffer_size, *y.shape),
            dtype=y.dtype
        )
        self.buffer_counter = 0

    def __fill_histo_from_buffer(self):
        if self.buffer_x is None:
            return

        self.buffer_x = self.buffer_x[:self.buffer_counter]
        self.buffer_y = self.buffer_y[:self.buffer_counter]
        for pixel_id in range(self.buffer_x.shape[1]):
            H, xedges, yedges = np.histogram2d(
                self.buffer_x[:, pixel_id].flatten(),
                self.buffer_y[:, pixel_id].flatten(),
                bins=self.histo.shape[1:],
                range=self.range
            )
            self.histo[pixel_id] += H.astype('u2')
        self.xedges, self.yedges = xedges, yedges
        self.buffer_x = None
        self.buffer_y = None
        self.buffer_counter = 0

    def contents(self):
        self.__fill_histo_from_buffer()
        return self.histo
