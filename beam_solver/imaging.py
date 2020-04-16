from beam_solver import casa_utils as ct
from beam_solver import fits_utils as ft
from beam_solver import extract as et
from beam_solver import coord_utils as crd
from astropy.io import fits
from astropy import wcs
import numpy as np
import pylab
import os

class Imaging(object):
    def __init__(self, ms):
        """
        Object to store measurement sets of meausrement files containing visibilities and performs
        operations such as imaging.
        Parameters
        ----------
        ms : str
            Input Measurement set file containing visibilities are required metadata.        
        imagename : str
            Name of output casa image.
        """
        self.ms = ms

    def flag_antenna(self, antenna, script='flag_a', del_script=True):
        """
        Flags antennas
        """
        ct.flag_antenna(self.ms, antenna)

    def generate_image(self, imagename, antenna='', cellsize='8arcmin', npix=512, niter=0, threshold='0Jy', weighting='uniform', start=200, stop=900, uvlength=0, phasecenter='', gridmode='', wprojplanes=1024, script='clean', del_script=True):
        """
        Generates multi-frequency synthesized images using all baselines within the specified cutoff threshold

        Parameters
        ---------
        antenna: string
            Antenna(s) or baseline(s) to used for imaging.
            e.g antenna='0' uses data from antenna 0 only
            antenna='0,4,5' uses data from antennas 0,4 and 5
            antenna='0&3' uses data from baseline 0-3
            antenna='0&3; 4&3' uses data from baselines 0-3 and 4-3
            Default is ''(all) which uses all the baselines
        imagename : str
            Name of output casa image.
        cellsize: string
            Degrees to be contained in one pixel of the image.
            Default is 8 arcmins.
        npix: int
            Number of pixel the output image is along x(l) and y(m) axis.
            Default is 512.
        niter: integer
            Number of iterations to use for deconvolution. Default is 0.
            Hence, dirty images are generated by default.
        threshold: string
            Cleaning threshold in Jy or mJy. Default is 0 Jy.
        weighting: string
            Weighting to be using for gridding of uv points. Default is uniform.
        start: int
            Starting frequency channel. Default is 200.
        stop: int
            Stopping/endign frequency channel. Default is 900.
        uvlength: float
            UV length in metres equal to or smaller to exclude while generating the image. Default is 0.        
        phasecenter: str
            Pointing center of the image
        gridmode: string
            Gridding kernel for FFT-based transforms
    wprojplanes : int
        Number of w-projection planes for convolution; -1 => automatic determination
        del_script : boolean
            If True, deletes the casa script used to execute the CASA clean task.
            Default is True.
        """
        ct.imaging(self.ms, imagename, antenna=antenna, cellsize=cellsize, npix=npix, niter=niter, threshold=threshold, weighting=weighting, start=start, stop=stop, uvlength=uvlength, phasecenter=phasecenter, gridmode=gridmode, wprojplanes=wprojplanes, script=script, delete=del_script)
            
    def remove_image(self, imagename, del_img=False):
        """
        Removes unecesssary images spit by CASA
        Parameters
        ----------
        imagename : str
            Name of output casa image.
        del_img : boolean
            If True, removes the casa image file as well.
            Default is False.
        """
        os.system('rm -r {}.model'.format(imagename))
        os.system('rm -r {}.flux'.format(imagename))
        os.system('rm -r {}.psf'.format(imagename))
        os.system('rm -r {}.residual'.format(imagename))
        if del_img:
            os.system('rm -r {}.image'.format(imagename))

    def to_fits(self, imagename, fitsname=None, script='to_fits', del_script=True, overwrite=False):
        """
        Convert CASA image file to FITS format    
        Parameters
        ----------
        imagename : str
            Name of output casa image.
        fitsname : str
            Name of output fitsfile
        overwrite : boolean
            If True, overwrites the existing image with the new one.
            Default is False.
        """
        input_image = imagename
        ct.exportfits(input_image, fitsname=fitsname, script=script, overwrite=overwrite)

    def plot_image(self, fitsfile, cmap='gray', vmin=None, vmax=None, title=''):
        """
        Read in and plot the fisfile into a 2D waterfall plot.
        Parameters
        ----------
        fitsfile : str
            Name of input fitsfile to read.
        cmap : str
            Color map of the 2D plot. Default is gray.
        vmin : float
            Minimum colorbar value for the plot. Default is
            minimum of the data.
        vmax : float
            Minimum colorbar value for the plot. Default is
            maximum of the data.
        """
        fitsinfo = ft.get_fitsinfo(fitsfile)
        data, header = fitsinfo['data'], fitsinfo['hdr']
        my_wcs = wcs.WCS(header, naxis=[wcs.WCSSUB_CELESTIAL])
        if vmin is None:
            vmin = np.min(data)
        if vmax is None:
            vmax = np.max(data)
        fig = pylab.figure(figsize=(6, 5))
        ax = fig.add_subplot(111, projection=my_wcs)
        im= ax.imshow(data, origin='lower', interpolation='nearest', cmap=cmap, vmin=vmin, vmax=vmax)
        cbar = pylab.colorbar(im, ax=ax)
        cbar.set_label(header['BUNIT'])
        ax.coords[0].set_axislabel('R.A. [deg]')
        ax.coords[1].set_axislabel('Dec [deg]')
        pylab.grid(lw=1, color='black')
        pylab.title(title, size=12)
        pylab.show()

    def subtract_model(self, outfile, del_script=True):
        """
        Subtracts CLEAN model from data
        outfile : str
              Name of the output residual file
        """
        os.system('cp -r {} {}'.format(self.ms, outfile))        
        ct.subtract_model(outfile, delete=del_script)
        
    def delete_log(self):
        """
        Delete unecessary files created during execution
        """
        os.system('rm -rf *.log')
        os.system('rm -rf *.log~')
        os.system('rm -rf *.last')
        os.system('rm -rf *.last~')

class Subtract(Imaging):
    def __init__(self, ms, srcdict=None):
        """
        Object to store measurement sets of meausrement files containing visibilities and performs
        operations such as imaging.
        Parameters
        ----------
        ms : str
            Input Measurement set file containing visibilities are required metadata.
        imagename : str
            Name of output casa image.
         srcdict : dict
            Dictionary with the position of sources in the format below
                srcdict = {srcnum: (ra, dec)}
                e.g srcdict = {1: ('3:52:52.61', '-27:20:2.86')}
        """
        Imaging.__init__(self, ms)
        self.srcdict = srcdict

    def make_image(self, imagename, fitsname, niter=500, antenna='', phasecenter='', start=200, stop=900, del_img=True, overwrite=False):
        """
        Returns fits image generated from the ms for any single antenna, combination of antennas or all antennas.
        Parameters
        ----------
        imagename : str
            Name of the output image
        fitsname : str
            Name of output fits file. By defualt, it return <imagename>.fits
        niter : int
            Number of deconvolution interation. By default it is 500.
        antenna : str
            Antenna number(s). By default it uses all the antennas
        overwrite :  boolean
            If True, overwrite existing image. Default is set to False
        """           
        self.generate_image(imagename, antenna=antenna, niter=niter, phasecenter=phasecenter, start=start, stop=stop)
        self.to_fits(imagename + '.image', fitsname, overwrite=overwrite)
        if del_img:
            self.remove_image(imagename, del_img=True)

    def srcdict_to_list(self):
        ras = [cd.hms2deg(self.srcdict[key][0]) for key in self.srcdict.keys()]
        decs = [cd.dms2deg(self.srcdict[key][1]) for key in self.srcdict.keys()]
        return ras, decs

    def extract_flux(self, fitsname, ras, decs):
        return [et.get_flux(fitsname, ras[i], decs[i])['gauss_pflux'] for i in range(len(ras))]
    
    def get_freq(self, fitsname):
        fitsinfo = ft.get_fitsinfo(fitsname)
        return fitsinfo['freq']        

    def const_phase_center(self, ra, dec):
        ra_str = crd.deg2hms(ra)
        dec_str = crd.deg2dms(dec)
        return 'J2000 {} {}'.format(ra_str, dec_str)

    def subtract_model(self, imagename, fitsname=None, niter=500, antenna='', start=200, stop=900, maxiter=20):
        if fitsname is None:
            fitsname = imagename + '.fits'
        self.make_image(imagename, fitsname, niter=niter, antenna=antenna, start=start, stop=stop, overwrite=True)
        ras, decs = self.srcdict_to_list()
        fluxs = self.extract_flux(fitsname, ras, decs)
        freq = self.get_freq(fitsname)
        # generating visibilities using ft CASA task
        for i in range(len(ras)):
            orig_flux = fluxs[i]
            flux = orig_flux
            flux0 = orig_flux
            operation = 'add' if orig_flux < 0 else 'subtract'
            infile = 'src_component.dat'
            outfile = 'src_component.cl'
            iter_num = 1
            while (np.abs(flux) >= 0.1 * np.abs(orig_flux) and np.abs(flux) <= np.abs(flux0) and iter_num <= maxiter):
                ct.generate_complist_input([ras[i]], [decs[i]], [np.abs(flux)], [0], [freq * 1e-6], output=infile)
                ct.create_complist(infile, outfile)
                ct.ft(self.ms, complist=outfile, start=start, stop=stop)
                ct.subtract_model_ant(self.ms, antenna, operation=operation)
                self.make_image(imagename, fitsname, niter=niter, antenna=antenna, start=start, stop=stop, overwrite=True)
                flux0 = flux # flux obtained at previous iteration
                flux = self.extract_flux(fitsname, [ras[i]], [decs[i]])[0]
                iter_num += 1

    def subtract_sources(self, ra, dec, pflux, imagename, fitsname=None, niter=0, antenna='', start=200, stop=900, npix=30, gain=0.3, maxiter=10, return_val=False):
        if fitsname is None:
            fitsname = imagename + '.fits'
        phasecenter = self.const_phase_center(ra, dec)
        self.generate_image(imagename, antenna=antenna, niter=niter, phasecenter=phasecenter, start=start, stop=stop, npix=npix)
        self.to_fits(imagename + '.image', fitsname, overwrite=True)
        mod_fitsname = imagename + '.mod.fits'
        self.to_fits(imagename + '.model', mod_fitsname, overwrite=True)
        self.remove_image(imagename, del_img=True)
        moddata = ft.get_fitsinfo(mod_fitsname)['data']
        stats = et.get_flux(fitsname, ra, dec)
        resflux = stats['gauss_tflux']
        flux0 = resflux
        resdata = moddata
        iter_num = 1
        print ('Iteration {}: {} Jy -- {}% of observed flux'.format(iter_num, resflux, round(abs(resflux * 100 / np.abs(pflux))), 2))
        while (np.abs(resflux) > 1 / 10. * np.abs(pflux) and np.abs(resflux) <= np.abs(flux0) and iter_num < maxiter):
            pmod_fitsname = imagename + '.pmod.fits'
            ft.write_fits(mod_fitsname, gain * resdata, pmod_fitsname, overwrite=True)
            resdata -= gain * resdata
            mod_imagename = mod_fitsname.replace('.fits', '.image')
            ct.importfits(mod_fitsname, mod_imagename, overwrite=True)  
            ct.ft(self.ms, model = mod_imagename)
            ct.subtract_model_ant(self.ms, antenna)
            self.generate_image(imagename, antenna=antenna, niter=0, start=start, stop=stop, npix=npix, phasecenter=phasecenter)
            self.to_fits(imagename + '.image', fitsname, overwrite=True)
            self.remove_image(imagename, del_img=True)
            stats = et.get_flux(fitsname, ra, dec)
            flux0 = resflux
            resflux = stats['gauss_tflux']
            niter += 1
            print ('Iteration {}: {} Jy -- {}% of observed flux'.format(iter_num, resflux, round(abs(resflux * 100 / np.abs(pflux))), 2))
        if return_val:
            return np.abs(flux0) * 100 / np.abs(pflux)
