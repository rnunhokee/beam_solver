import numpy as np
import linsolve
import aipy
import time
from collections import OrderedDict

class BeamFunc():
    def __init__(self, cat=None, bm_pix=60):
        """
        Object that stores the flux catalog containing the flux values which will be used
        to solve for the primary beam
        """
        self.cat = cat
        self.bm_pix = bm_pix
        self.eqs = OrderedDict()
        self.consts = OrderedDict()
        self.sol_dict = OrderedDict()
        self.ls = None

    def _mk_key(self, pixel, srcid, timeid):
        """
        Generates key to represent the beam pixel which include the source id,
        timestamp and pixel.

        Parameters
        ----------
        pixel : int
            Pixel from the 2D grid beam.

        srcid : int
            Source identity.

        timeid : int
            Time identity or timestamps.

        Returns
        -------
            String corresponding the given parameters.
        """
        return 'w%d_s%d_t%d' % (pixel, srcid, timeid)

    def _mk_eq(self, ps, ws, obs_flux, catalog_flux, srcid, timeid, **kwargs):
        """
        Constructs equations that will form the linear system of equations.

        Parameters
        ---------
        ps : nd array
            Numpy array containing the four closest pixel numbers corresponding to the
            alt-az position of the source
h
        ws : ns array
            Numpy array contining the weights corresponding to the pixel numbers

        obs_flux : float
            Measured or observed flux value

        catalog_flux : float
            Catalog or corrected flux value obtained using the flux values from the catalog.
            Refer to catdata.calc_catalog_flux.    

        srcid : int
            Source identity.

        timeid : int
            Time identity or timestamps.
        """
        i = srcid; j = timeid
        c = {self._mk_key(self.unravel_pix(self.bm_pix, (ps[p][0,j], ps[p][1,j])), i, j): ws[p][j] for p in xrange(4)}
        eq = ' + '.join([self._mk_key(self.unravel_pix(self.bm_pix, (ps[p][0, j], ps[p][1, j])), i, j)
            + '*b%d'%(self.unravel_pix(self.bm_pix, (ps[p][0, j], ps[p][1, j])))  for p in xrange(4)])
        self.eqs[eq] = obs_flux / catalog_flux
        self.consts.update(c)

    def build_solver(self, **kwargs):
        """
        Builds linsolve solver
        """
        self.ls = linsolve.LinearSolver(self.eqs, **self.consts)

    def unravel_pix(self, ndim, coord):
        """
        Returns the unraveled/flattened pixel of any (m, n) position
        or coordinates on any square 2D-grid

        Parameters
        ----------
        coord : tuple of int
            Coordinates (m, n) for which to calculate the  flattened index.

        Returns
        -------
        index of the flattened array corresponding to the coordinates (m, n).
        """
        return (coord[0] * ndim) + coord[1]

    def rotate_mat(self, theta):
        """
        Rotate coordinates or pixels by theta degrees

        Parameters
        ----------
        theta : float
            Angle by which the coordinates or pixels will be rotated.
        """
        return np.array([[np.cos(theta), -1*np.sin(theta)], [np.sin(theta), np.cos(theta)]])

    def get_weights(self, azalts, theta, flip):
        """
        Returns the four closest pixels to the azimuth-altitude values on the 2D
        grid.

        Parameters
        ----------
        azalts : ndarray
            2D array consisting of the azimuth and alitutes values in degrees.
        """

        # selecting the four closest pixels
        tx, ty, tz = aipy.coord.azalt2top([azalts[0, :] * np.pi/180., azalts[1, :] * np.pi/180.])
        tx_px = tx * 0.5 * self.bm_pix + 0.5 * self.bm_pix
        ty_px = ty * 0.5 * self.bm_pix + 0.5 * self.bm_pix
        tx_px0 = np.floor(tx_px).astype(np.int)
        tx_px1 = np.clip(tx_px0 + 1, 0, self.bm_pix - 1)
        ty_px0 = np.floor(ty_px).astype(np.int)
        ty_px1 = np.clip(ty_px0 + 1, 0, self.bm_pix - 1)

	x0y0 = np.dot(self.rotate_mat(theta), np.array([tx_px0, ty_px0], dtype=np.int))
        x0y1 = np.dot(self.rotate_mat(theta), np.array([tx_px0, ty_px1], dtype=np.int))
        x1y0 = np.dot(self.rotate_mat(theta), np.array([tx_px1, ty_px0], dtype=np.int))
        x1y1 = np.dot(self.rotate_mat(theta), np.array([tx_px1, ty_px1], dtype=np.int))

	x0y0[0] = flip * x0y0[0]
        x0y1[0] = flip * x0y1[0]
        x1y0[0] = flip * x1y0[0]
        x1y1[0] = flip * x1y1[0]

        # defining the weights
        fx = tx_px - tx_px0
        fy = ty_px - ty_px0
        
        w0 = (1 - fx) * (1 - fy)
        w1 = fx * (1 - fy)
        w2 = (1 - fx) * fy
        w3 = fx * fy
        
        ps = [x0y0, x0y1, x1y0, x1y1]
        ws = [w0, w1, w2, w3]
	
        return ps, ws

    def rotate_coord(self, theta, coord):
        """
        Rotates a point about the origin/center of the beam grid

        Parameters
        ----------
        theta :  float
            Angle in radians by the which the coordinates will be rotated

        coord : numpy.nd array
            2D numpy array with the first axis representing the x-coordinates and
            the second axis representing the y-axis.
        """
        # here we are assuming a square grid, therefore center of the beam is (x0, y0) = (x0, x0).
        x0 = int(0.5 * self.bm_pix)
        y0 = x0
        x, y = coord[0], coord[1]
        xr = np.cos(theta) * (x - x0) - np.sin(theta) * (y - y0) + x0
        yr = np.sin(theta) * (x - x0) + np.cos(theta) * (y - y0) + y0
        return np.array([xr, yr])

    def get_A(self, ls):
        """
        Returns the A matrix used to solve the system of linear equations

            y = A.x.

        Parameters
        ----------
        ls : linsolve instance
            instance of linsolve solver containing the linear system of equations.
        """
        return ls.get_A()

    def svd(self, ls, A):
        """
        Decomposes m x n matrix through single value decomposition

        Parameters
        ----------
		ls : linsolve instance
            instance of linsolve solver containing the linear system of equations.

        A : numpy array/ matrix of floats.
        """
        A.shape = (A.shape[0], A.shape[1])
        AtA = np.dot(A.T.conj(), A)
        # decomposes A matrix
        U, S, V = np.linalg.svd(AtA)

        return U, S, V

    def remove_degen(self, ls, obsbeam, threshold=5e-4):
        """
        Remove degeneracies using single value decomposition. It removes all eigenvalue modes
        above the specified threshold.

		ls : instance of linsolve
			instance of linsolve solver containing the linear system of equations.

        obsbeam : 2D numpy array
            2-dimensional array containing the beam values.

        threshold : float
            Threshold value after which all the eigenvalue modes will be discarded.
        """
        A = self.get_A(ls)
        U, S, V = self.svd(ls, A)

        # determining the cutoff threshold for bad eigen modes
        total = sum(S)
        var_exp = np.array([(i / total) * 100 for i in sorted(S, reverse=True)])
        # selecting the cutoff eigen-mode
        cutoff_mode = np.where(var_exp < threshold)[0][0]
        print ('Removing all eigen modes above {}'.format(cutoff_mode))

        for i in xrange(cutoff_mode, len(S)):
            emode = np.array([U[ls.prm_order['b%d' % px], i] if ls.prm_order.has_key('b%d'%px) else 0 for px in xrange(self.bm_pix**2)])
            emode.shape = (self.bm_pix, self.bm_pix)
            obsbeam -= np.sum(obsbeam * emode) * emode.conj()

        return obsbeam

class BeamOnly(BeamFunc):
    def __init__(self, cat=None, bm_pix=60):
        """
        Object that stores the flux catalog containing the flux values for one
        polarization and solves for the primary beam only.
        """
        BeamFunc.__init__(self, cat, bm_pix)
	
    def construct_sys(self, catalog_flux=[], theta=[0], flip=[1], polnum=0, **kwargs):
        """
        Construct a linear system of equations of the form

            I_mod * A  = I_obs.

        where I_mod is model flux value, A is primary beam value and I_obs is our measurement.
        We decompose A such that
 
            A = a1 * w1 + a2 * w2 + a3 * w3 + a4 * w4

        where (a1, a2, a3, a4) are the four closest pixel values of the beam to the azimuth-altitude
        value of the source at a given time and (w1, w2, w3, w4) are the corrsponding weights.

        Parameters
        ----------
        catalog_flux : list or np.ndarray
            List or array containing the model/catalog flux values to be used as I_mod.
 
    	theta : float
       	"""
        nfits = self.cat.Nfits
        nsrcs = self.cat.Nsrcs

        obs_vals = self.cat.data_array[polnum]
        for i in xrange(nsrcs):
            for th in theta:
                for fl in flip:
                    ps, ws = self.get_weights(self.cat.azalt_array[:, i, :], th, fl)
                    for j in xrange(nfits):
                        I_s = obs_vals[i, j]
                        if np.isnan(I_s): continue
                        self._mk_eq(ps, ws, I_s, catalog_flux[i], i, j, **kwargs)

    def solve(self, **kwargs):
        """
        Solves for the linear system of equations
        """
        self.build_solver(**kwargs)
        sol = self.ls.solve(verbose=True)
        return sol        

    def eval_sol(self, sol):
        """
        Evaluates the solutions to output the beam values into a
        2D grid.

        sol : dict
            Dictionary containing the solutions, returned by the solver.
        """
        obs_beam = np.zeros((self.bm_pix**2), dtype=float)
        for key in sol.keys():
            if key[0] == 'b':
                px = int(key.strip('b'))
                obs_beam[px] = sol.get(key)

        obs_beam.shape = (self.bm_pix, self.bm_pix)
        return obs_beam
    
class BeamCat(BeamOnly):
    def __init__(self, cat, bm_pix=60):
        """
        Object that stores the flux catalog containing the flux values for one
        polarization and solves for both the true flux values of the sources and
        the primary beam.
        """
        BeamOnly.__init__(self, cat, bm_pix)

    def _mk_eq(self, ps, ws, obs_flux, catalog_flux, srcid, timeid, **kwargs):
        """
        Constructs equations that will form the linear system of equations.

        Parameters
        ---------
        ps : numpy.nd array
            Numpy array containing the four closest pixel numbers corresponding to the
            alt-az position of the source

        ws : ns array
            Numpy array contining the weights corresponding to the pixel numbers

        obs_flux : float
            Measured or observed flux value

        catalog_flux : float
            Catalog or corrected flux value obtained using the flux values from the catalog.
            Refer to catdata.calc_catalog_flux.

        srcid : int
            Source identity.

        timeid : int
            Time identity or timestamps.
        """
        i = srcid ; j = timeid
        bvals = kwargs['bvals'].flatten()
        self.sol_dict['I%d'%i] = catalog_flux
        c = {self._mk_key(self.unravel_pix(self.bm_pix, (ps[p][0,j], ps[p][1,j])), i, j): ws[p][j]
                    for p in xrange(4)}
        eq = ' + '.join([self._mk_key(self.unravel_pix(self.bm_pix, (ps[p][0, j], ps[p][1, j])), i, j)
            + '*b%d'% (self.unravel_pix(self.bm_pix, (ps[p][0, j], ps[p][1, j]))) + '*I%d'%i for p in xrange(4)])
        self.eqs[eq] = obs_flux
        self.consts.update(c)
        for p in xrange(4):
            bpix = int(self.unravel_pix(self.bm_pix, (ps[p][0, j], ps[p][1, j])))
            self.sol_dict['b%d'%bpix] = bvals[bpix]

    def construct_sys(self, catalog_flux=[], theta=[0], flip=[1], polnum=0, **kwargs):
        """
        Construct a non linear system of equations of the form

            I_mod * A  = I_obs.

        where I_mod is model flux value, A is primary beam value and I_obs is our measurement.
        We decompose A such that

            A = a1 * w1 + a2 * w2 + a3 * w3 + a4 * w4

        where (a1, a2, a3, a4) are the four closest pixel values of the beam to the azimuth-altitude
        value of the source at a given time and (w1, w2, w3, w4) are the corrsponding weights.

        In the non-linear case, we solve for both I_mod and A, however initial guesses are required
        to start the iteration.

        Parameters
        ----------
        catalog_flux : list or np.ndarray
            List or array containing the model/catalog flux values to be used as I_mod.
        """
        nfits = self.cat.Nfits
        nsrcs = self.cat.Nsrcs

        obs_vals = self.cat.data_array[polnum]
 
        for i in xrange(nsrcs):
            for th in theta:
                for fl in flip:
                    ps, ws = self.get_weights(self.cat.azalt_array[:, i, :], th, fl)
                    for j in xrange(nfits):
                        I_s = obs_vals[i, j]
                        if np.isnan(I_s): continue
                        self._mk_eq(ps, ws, I_s, catalog_flux[i], i, j, **kwargs)

    def build_solver(self, multiply=100, **kwargs):
        """
        Builds linsolve solver

		Parameters
		----------
		multiply: float
			Value specified to force the desired constrained. Default is 100.
        """
        constrain = kwargs.pop('constrain', False)
        # constraining the center pixel to be one
        if constrain:	
            self.eqs['%d*b%d'%(multiply, self.unravel_pix(self.bm_pix, (int(self.bm_pix/2.), int(self.bm_pix/2.))))] = multiply
        self.ls = linsolve.LinProductSolver(self.eqs, sol0=self.sol_dict, **self.consts)

    def solve(self, maxiter=50, conv_crit=1e-11, **kwargs):
        self.build_solver(**kwargs)
        sol = self.ls.solve_iteratively(maxiter=maxiter, conv_crit=conv_crit, verbose=True)
        return sol

    def eval_sol(self, sol):
        """
        Evaluates the solutions to output the beam values into a
        2D grid and the model flux values.

        sol : dict
            Dictionary containing the solutions, returned by the solver.
        """

        obs_beam = BeamOnly(cat=self.cat, bm_pix=self.bm_pix).eval_sol(sol[1])
	fluxvals = np.zeros((2, self.cat.Nsrcs))
        k = 0
        for key in sol[1].keys():
            if key[0] == 'I':
                fluxvals[0, k] = int(key[1::]) + 1
                fluxvals[1, k] = sol[1].get(key)
                k += 1
        return fluxvals, obs_beam

class BeamOnlyCross(BeamOnly):
    def __init__(self, cat=None, bm_pix=60):
        """
        Object that stores the flux catalog containing the flux values for xx and yy
        polarization and solves for the primary beam only using both polarizations.
        """
        BeamOnly.__init__(self, cat, bm_pix)
        
    def construct_sys(self, catalog_flux_xx=[], catalog_flux_yy=[], theta_xx=[0], theta_yy=[np.pi/2], flip_xx=[1], flip_yy=[1], **kwargs):
        """
        Construct a linear system of equations of the form

            I_mod * A  = I_obs.

        where I_mod is model flux value, A is primary beam value and I_obs is our measurement.
        We decompose A such that

            A = a1 * w1 + a2 * w2 + a3 * w3 + a4 * w4

        where (a1, a2, a3, a4) are the four closest pixel values of the beam to the azimuth-altitude
        value of the source at a given time and (w1, w2, w3, w4) are the corrsponding weights.

        Parameters
        ----------
        catalog_flux : list or np.ndarray
            List or array containing the model/catalog flux values to be used as I_mod.
        """
        BeamOnly.construct_sys(self, catalog_flux=catalog_flux_xx, theta=theta_xx, flip=flip_xx, polnum=0)
	BeamOnly.construct_sys(self, catalog_flux=catalog_flux_yy, theta=theta_yy, flip=flip_yy, polnum=1)

    def solve(self, **kwargs):
        """
        Solves for the linear system of equations
        """
        self.build_solver(**kwargs)
        sol = self.ls.solve(verbose=True)
        return sol
        
class BeamCatCross(BeamCat):
    def __init__(self, cat=None, bm_pix=60):
        """
        Object that stores the flux catalog containing the flux values for xx and yy
        polarization and solves for both the flux values of the sources and the primary 
        beam using both polarizations.
        """
        BeamCat.__init__(self, cat, bm_pix)

    def construct_sys(self, catalog_flux_xx, catalog_flux_yy, theta_xx=[0], theta_yy=[np.pi/2], flip_xx=[1], flip_yy=[1], polnum=0, **kwargs):
        """
        Construct a non linear system of equations of the form

            I_mod * A  = I_obs.

        where I_mod is model flux value, A is primary beam value and I_obs is our measurement.
        We decompose A such that

            A = a1 * w1 + a2 * w2 + a3 * w3 + a4 * w4

        where (a1, a2, a3, a4) are the four closest pixel values of the beam to the azimuth-altitude
        value of the source at a given time and (w1, w2, w3, w4) are the corrsponding weights.

        In the non-linear case, we solve for both I_mod and A, however initial guesses are required
        to start the iteration.

        Parameters
        ----------
        mflux : list or np.ndarray
            List or array containing the model flux values to be used as initial guesses for I_mod.
            Default is list of ones.

        bvals : 2D numpy array
            Array containing initial guesses for the beam. Default is zeros.

        constrain : boolean
            If True, constrained the center pixel to be one. It will error out if the sources are not
            transiting zenith. Default is False.
        """
        BeamCat.construct_sys(self, catalog_flux=catalog_flux_xx, theta=theta_xx, flip=flip_xx, polnum=0, **kwargs)
        BeamCat.construct_sys(self, catalog_flux=catalog_flux_yy, theta=theta_yy, flip=flip_yy, polnum=1, **kwargs)

    def solve(self, maxiter=50, conv_crit=1e-11, **kwargs):
        self.build_solver(**kwargs)
        sol = self.ls.solve_iteratively(maxiter=maxiter, conv_crit=conv_crit, verbose=True)
        return sol
