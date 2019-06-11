import numpy
import pylab
import os, sys
from beam_solver import casawrapper
from beam_solver import coord_utils as cd

def uvfits2ms(uvfits, outfile=None, script='uvfits2ms', delete=True):
    """
    Converts uvfits to measurement sets 
    Parameters
    ----------
    uvfits: string
        Uvfits files containing visibilities and the corresponding metadata
    outfile: string
        Name of output measurement set (MS) file. Default id <uvfits>.ms
    script: string
        Name of the casapy script will be created on-the-fly. Default is uvfits2ms
    overwrite : boolean
        Overwrites any existing file. Default is False.
    delete: boolean 
        Deletes the casapy script that was created on-the-fly after execution.
        Default is True.
    """
    if outfile is None:
        outfile = uvfits.replace('.uvfits', '.ms')
    print ('Converting {} to {}'.format(uvfits, outfile))
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = casawrapper.create_casa_options(vis="'{}'".format(outfile), fitsfile="'{}'".format(uvfits))
    casawrapper.call_casa_task(task='importuvfits', script=script, task_options=task_opt, casa_options=casa_opt, delete=delete)

def ms2uvfits(dset, outfile=None, script='ms2uvfits', overwrite=False, delete=True):
    """
    Converts measurement sets to uvfits files
    Parameters
    ----------
    dset: string
        Measurement sets (MS) containing visibilities and the corresponding metadata.
    outfile: string
        Name of the output uvfits file. Default is <dset>.uvfits.
    script: string
        Name of casapy script that will be create on-the-fly. Default is ms2uvfits.        
    overwrite : boolean
        Overwrites any existing file. Default is False.    
    delete: boolean
        Deletes the casapy script that was created on-the-fly after execution.
    """
    if outfile is None:
        outfile = dset.replace('.ms', '.uvfits')
    print ('Converting {} to {}'.format(dset, outfile))
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = casawrapper.create_casa_options(vis="'{}'".format(dset), fitsfile="'{}'".format(outfile), overwrite="{}".format(overwrite))
    print ('task_opt:', task_opt)
    casawrapper.call_casa_task(task='exportuvfits', script=script, task_options=task_opt, casa_options=casa_opt, delete=delete)
    
def flag_antenna(dset, antenna, script='flag_a', delete=True):
    """
    Flags all the visibilities corresponding to one/more antennas
    Parameters
    ----------
    dset: string
        Name of input measurement set (MS) file containing visibilities for all baselines
        and the corresponding metadata
    antenna: string
        Antenna number to be flagged, e.g '0' or list of antennas e.g '0, 1, 5, 6'
    script: string
        Name of casapy script that will be create on-the-fly. Default is flag_a
    delete: boolean
        Deletes the casapy script that was created on-the-fly after execution
    """
    print ('Flagging antenna(s) {}'.format(antenna))
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = casawrapper.create_casa_options(vis="'{}'".format(dset), antenna="'{}'".format(antenna))
    casawrapper.call_casa_task(task='flagdata', script=script, task_options=task_opt, casa_options=casa_opt, delete=delete)

def imaging(dset, imagename, antenna='', cellsize='8arcmin', npix=512, niter=0, threshold='0Jy', weighting='uniform', start=200, stop=900, uvlength=0, script='clean', delete=True):
    """
    Generates images using all antenna or specific antennas using visibilities from the measurement set (MS)

    Parameters
    ----------
    dset: string
        Name of input measurement set (MS) file containing visibilities for all baselines
        and the corresponding metadata
    imagename: string
        Name of output casa image
    antenna: string
        Antenna(s) or baseline(s) to used for imaging.
        e.g antenna='0' uses data from antenna 0 only
            antenna='0,4,5' uses data from antennas 0,4 and 5
            antenna='0&3' uses data from baseline 0-3
            antenna='0&3; 4&3' uses data from baselines 0-3 and 4-3
        Default is ''(all) which uses all the baselines
    cellsize: string
        Degrees to be contained in one pixel of the image.
        Default is 3 arcmins.
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
        Uv length in metres equal to or smaller to exclude while generating the image. Default is 0.
    script: string
        Name of casapy script that will be create on-the-fly. Default is clean
    delete: boolean
        Deletes the casapy script that was created on-the-fly after execution
    """ 
    antenna_out = 'all' if antenna == '' else antenna
    print ('Imaging using antenna(s) {}'.format(antenna_out))
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = casawrapper.create_casa_options(vis="'{}'".format(dset), imagename="'{}'".format(imagename), antenna="'{}'".format(antenna), cell="'{}'".format(cellsize), imsize=[npix,npix], threshold="'{}'".format(threshold), niter="{}".format(niter), spw="'0:{}~{}'".format(start, stop), uvrange="'>{}'".format(uvlength), weighting="'{}'".format(weighting), usescratch=True)
    casawrapper.call_casa_task(task='clean', script=script, task_options=task_opt, casa_options=casa_opt, delete=delete)    

def exportfits(imagename, fitsname=None, overwrite=False, script='exportfits', delete=True):
    """
    Converts CASA images to FITS files
    Parameters
    ----------
    imagename: string
        Name of the input casa image
    fitsname: string
        Name of output fits file. Default is <imagename>.fits
    overwrite : boolean
        If True, overwrites the existing image with the new one.
        Default is False.
    script: string 
        Name of casapy script that will be create on-the-fly. Default is exportfits
    delete: boolean
        Deletes the casapy script that was created on-the-fly after execution
    """
    if fitsname is None:
        fitsname = imagename.replace('.image', '.fits')
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = casawrapper.create_casa_options(imagename="'{}'".format(imagename), fitsimage="'{}'".format(fitsname), overwrite=overwrite)
    casawrapper.call_casa_task(task='exportfits', script=script, task_options=task_opt, casa_options=casa_opt, delete=delete)

def generate_complist_input(ras, decs, fluxs, sindex, freqs, flux_unit='Jy', freq_unit='MHz', output='complist.dat'):
    """
    Generates the inputs for complist task
    Parameters
    ----------
    ras : list 
        List of right ascensions in degrees.
    decs : list
        List of declinations in degrees.
    fluxs : list
        List of flux density values in Jy
    sindex : list
        List of spectral indices
    freq : float
        Frequency value in Hz, MHz or GHz
    flux_unit : string
        Unit of input fluxs
    freq_unit : string
        Unit of input frequency
    output : string
        Name of output text file
    Returns
    -------
    textfile containing values for source position [ra(hms) dec(dms)], flux in Jy, spectral index and frequency in MHz
    """
    assert(len(ras) == len(decs))
    assert(len(ras) == len(fluxs))    
    assert(len(ras) == len(sindex))
    if freq_unit == 'Hz':
        freqs = freqs * 1e-6
    if freq_unit == 'GHz':
        freqs = freqs * 1e3
    stdout = open(output, 'wb')
    for ii, ra in enumerate(ras):
        ra_str = cd.deg2hms(ra)
        dec_str = cd.deg2dms(decs[ii])
        text = ('J2000 {} {}: {}: {}: {}\n'.format(ra_str, dec_str, fluxs[ii], sindex[ii], freqs[ii])).encode()
        stdout.write(text)
    stdout.close()    
    return output

def create_complist(infile, outfile='component.cl', script='create_cl', delete=False):
    """
    Creates component list of sources
    Parameters:
    -----------
    infile : Input text file containing the required parameters (see generate_complist_input function for the input format)
    outfile :  Output name of the component list
    Returns
    -------
    CASA Component with all the components
    """
    if os.path.exists(outfile):
        print ('WARNING: overwritting existed file')
        os.system('rm -rf {}'.format(outfile))
    stdout = open(script + '.py', 'wb')
    sources = numpy.loadtxt(infile, dtype='str', delimiter=':')
    if sources.ndim == 1: sources = sources.reshape((1, len(sources)))
    for src in sources:
        task_opt = "dir='{}', flux={}, fluxunit='Jy', shape='point', spectrumtype='spectral index', index={}, freq='{}MHz'".format(src[0], float(src[1]), float(src[2]), float(src[3])) 
        text = ('cl.addcomponent({})\n'.format(task_opt)).encode()
        stdout.write(text)    
    text = ("cl.rename('{}')\ncl.close()".format(outfile)).encode()
    stdout.write(text)
    stdout.close()
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    casawrapper.call_casa_script(script + '.py', casa_opts=casa_opt, delete=delete)

def ft(dset, complist=None, script='ft', delete=False):
    """
    Fourier transforming model (complist) and writing the resulting visibilities into the MODEL column
    Parameters
    ----------
    dset : string
        Name of input measurement set (MS) file containing visibilities for all baselines
        and the corresponding metadata
    complist : string
        Name of the component list containing list of model sources
    scripts : string
        Name of casapy script that will be create on-the-fly. Default is exportfits
    delete: boolean
        Deletes the casapy script that was created on-the-fly after execution
    """
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    if complist is None:
        task_opt = casawrapper.create_casa_options(vis="'{}'".format(dset), usescratch=True)
    else:
        task_opt = casawrapper.create_casa_options(vis="'{}'".format(dset), complist="'{}'".format(complist ), usescratch=True)
    casawrapper.call_casa_task(task='ft', script=script, task_options=task_opt, casa_options=casa_opt, delete=delete) 

def writeto(dset, column_from, column_to, script='writeto', delete=False):
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = "ms = casac.table()\n"
    task_opt += "ms.open('{}', nomodify=False)\n".format(dset)
    task_opt += "if '{}' in ms.colnames():\n".format(column_from)
    task_opt += "   mod_data = ms.getcol('MODEL_DATA')\n"
    task_opt += "   ms.putcol('{}', mod_data)".format(column_to)
    stdout = open(script + ".py", "w")
    stdout.write(task_opt)
    stdout.close()
    casawrapper.call_casa_script(script + ".py", casa_opt, delete=delete)

def subtract_model(dset, script='subtract_mod', delete=False):
    casa_opt = casawrapper.create_casa_options(nologger='0', nogui='0', nologfile='0')
    task_opt = "ms = casac.table()\n"
    task_opt += "ms.open('{}', nomodify=False)\n".format(dset)
    task_opt += "if 'MODEL_DATA' in ms.colnames():\n"
    task_opt += "   data = ms.getcol('CORRECTED_DATA') if 'CORRECTED_DATA' in ms.colnames() else ms.getcol('DATA')\n"
    task_opt += "   ms.putcol('DATA', data - ms.getcol('MODEL_DATA'))\n"
    stdout = open(script + ".py", "w")
    stdout.write(task_opt)
    stdout.close()
    casawrapper.call_casa_script(script + ".py", casa_opt, delete=delete)
