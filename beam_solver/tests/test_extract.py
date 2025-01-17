import os
from beam_solver.data import DATA_PATH
import beam_solver.extract as et
import nose.tools as nt
import numpy as np

fitsfile = os.path.join(DATA_PATH, '2458115.23736.test.xx.fits')

def test_get_peakflux():
    stats = et.get_flux(fitsfile, 74.26237654, -52.0209015)
    nt.assert_almost_equal(stats['pflux'], 0.75)
    stats = et.get_flux(fitsfile, 41.91116875, -43.2292595)
    nt.assert_almost_equal(stats['pflux'], 0.5)
    stats = et.get_flux(fitsfile, 356.26, -0.37)
    nt.assert_almost_equal(stats['pflux'], 0.6)
    nt.assert_almost_equal(stats['gauss_pflux'], 0.6, 1)

def test_boundaries():
    stats = et.get_flux(fitsfile, 74.26237654, -9.0)
    nt.assert_true(np.isnan(stats['pflux']))
