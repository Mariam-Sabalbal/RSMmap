
import vip_hci as vip
import os
from hciplot import plot_frames
#import sys
#sys.path.append('/.../')   # append the path to PyRSM if necessary
from PyRSM import PyRSM 

#Directory of dataset

os.chdir('/...')

psf = './SPHERE_51ERI_psf.fits'
cube = './SPHERE_51ERI_cube.fits'
angle = './SPHERE_51ERI_pa.fits'

angs = vip.fits.open_fits(angle)
cube = vip.fits.open_fits(cube)
psf = vip.fits.open_fits(psf)
pxscale_irdis = vip.config.VLT_SPHERE_IRDIS['plsc']

# Measure the FWHM by fitting a 2d Gaussian to the core of the PSF

fit = vip.var.fit_2dgaussian(psf, crop=True, cropsize=9, debug=True)
fwhm = float((fit.fwhm_y+fit.fwhm_x)/2)

# Normalize the PSF flux to one in the FWHM aperture

psfn = vip.fm.normalize_psf(psf, fwhm, size=19)
psf=  vip.preproc.frame_crop(psfn,11)
scaling_factor=0.84e6
psf_oa = psf*scaling_factor

"""
PyRSM framework (no automated parametrization): Approach 1
"""

# Create PyRSM class object

d=PyRSM.PyRSM(fwhm,minradius=10,maxradius=65,pxscale=pxscale_irdis,ncore=4)

# Add a cube

d.add_cube(psf,cube, angs)

# Add several methods

d.add_method('APCA',interval=[5], intensity='Annulus', distri='G', ncomp=20, var='FR', delta_rot=0.5, asize=5)
d.add_method('NMF',interval=[5], intensity='Annulus', distri='G', ncomp=20, var='FR', asize=5)
d.add_method('LLSG',interval=[5], intensity='Annulus', distri='G', rank=5, var='FR', delta_rot=0.5, asize=5)

# Estimate the cube of likelihoods

d.lik_esti(verbose=True)     

# Estimate final RSM map
     
d.probmap_esti(estimator='Forward',colmode='median')

# Plot final probability map

plot_frames(d.probmap)



"""
# PyRSM framework (no automated parametrization): Approach 2
"""

# Create PyRSM class object

d=PyRSM.PyRSM(fwhm,minradius=10,maxradius=65,pxscale=pxscale_irdis,ncore=4)

# Add a cube

d.add_cube(psf,cube, angs)

# Add several methods

d.add_method('APCA',interval=[5], intensity='Annulus', distri='A', ncomp=20, var='FR', delta_rot=0.5, asize=5)
d.add_method('NMF',interval=[5], intensity='Annulus', distri='A', ncomp=20, var='FR', asize=5)
d.add_method('LLSG',interval=[5], intensity='Annulus', distri='A', rank=5, var='FR', delta_rot=0.5, asize=5)

# Estimate the probability map

d.opti_map(estimator='Forward',colmode='median',threshold=False,Full=True)

# Plot final probability map

plot_frames(d.final_map)


"""
# auto-RSM framework
"""

# Create PyRSM class object

d=PyRSM.PyRSM(fwhm,minradius=10,maxradius=65,pxscale=pxscale_irdis,ncore=4, opti_mode='full-frame',inv_ang=True,opti_type='Contrast',trunc=10)

# Add a cube

d.add_cube(psf,cube, angs)

# Add several methods

d.add_method('APCA', asize=5,crop_size=3,crop_range=2,opti_bound=[[10,30],[1,4],[0.25,1]])
d.add_method('NMF', asize=5,crop_size=3,crop_range=2,opti_bound=[[10,25]])
d.add_method('LLSG', asize=5,crop_size=3,crop_range=2,opti_bound=[[1,8],[1,4]])

# Parameter optimization for the PSF-subtraction techniques

d.opti_model(optimisation_model='Bayesian', param_optimisation={'c1': 1, 'c2': 1, 'w':0.5,'n_particles':10,'opti_iter':40,'ini_esti':60, 'random_search':100}) 

# Parameter optimization for the RSM algorithm

d.opti_RSM(estimator='Forward',colmode='median')

# Optimal selection of the likelihood cubes generated by the RSM algorithm first step
# and estimation of the radial threshold that will be subtracted from the final detection map

d.opti_combination(estimator='Forward',colmode='median',threshold=True,contrast_sel='Max',combination='Bottom-Up') 

# Computation of the final optimal RSM detection map

d.opti_map(estimator='Forward',colmode='median',threshold=True)

# Plot final probability map

plot_frames(d.final_map)

# Save the set of optimal parameters

d.save_parameters('/.../','SPHERE_51ERI_optimal_param')


"""
# auto-S/N framework
"""

# Create PyRSM class object

d=PyRSM.PyRSM(fwhm,minradius=10,maxradius=65,pxscale=pxscale_irdis,ncore=4, opti_mode='full-frame',inv_ang=True,opti_type='Contrast',trunc=10)

# Add a cube
d.add_cube(psf,cube, angs)

# Add several methods

d.add_method('APCA')
d.add_method('NMF')
d.add_method('LLSG')

# Load optimal set of parameters for the PSF-subtraction techniques from previous step

d.load_parameters('/.../SPHERE_51ERI_optimal_param')

# Optimal selection of the S/N map generated by the set of selected PSF-subtraction techniques
# and estimation of the radial threshold that will be subtracted from the final S/N map

d.opti_combination(threshold=True,contrast_sel='Max',combination='Bottom-Up',SNR=True) 

# Computation of the final optimal RSM detection map

d.opti_map(threshold=True,SNR=True)

# Plot final probability map

plot_frames(d.final_map)


"""
# PyRSM planet characterization algorithm
"""
from vip_hci.fm import cube_inject_companions

# Create PyRSM class object

d=PyRSM.PyRSM(fwhm,minradius=10,maxradius=65,pxscale=pxscale_irdis,ncore=4)

# Add a cube
d.add_cube(psf,cube, angs)

# Add several methods

d.add_method('APCA')
d.add_method('NMF')
d.add_method('LLSG')

# Load optimal set of parameters for the PSF-subtraction techniques from previous step

d.load_parameters('/.../SPHERE_51ERI_optimal_param')

# Characterization of the detected signal positionned at [38,68]

result=d.target_charact([38,68],psf_oa=[psf_oa], loss_func='value',optimisation_model='PSO',param_optimisation={'c1': 1, 'c2': 1, 'w':0.5,'n_particles':10,'opti_iter':10,'ini_esti':10,'random_search':100},photo_bound=[1e-5,1e-4,10],ci_esti='hessian',first_guess=False)

cube_empty = cube_inject_companions(cube, psf, angs, flevel=-result[0]*scaling_factor, plsc=pxscale_irdis, 
                                rad_dists=result[9]/(1000*pxscale_irdis), theta=result[10], n_branches=1,verbose=True)
        

"""
# PyRSM contrast curve estimation (require the suppresion of 51 Eridani B from the sequence, see previous step)
"""

# Remove 51 Eridani B from the ADI sequence via the injection of a negative fake companion

result= [3.530749694432493e-05,38.80483808793875,68.00748823329512,9.776823185116977e-07,0.09864687206672194,0.08541139758377976,1.6081443076102904e-06,0.16225966530636546,0.14048924709867436,451.5890627081117,-100.93422053777543]

cube_empty = cube_inject_companions(cube, psf, angs, flevel=-result[0]*scaling_factor, plsc=pxscale_irdis, 
                                rad_dists=result[9]/(1000*pxscale_irdis), theta=result[10], n_branches=1,verbose=True)
        
# Create PyRSM class object

d=PyRSM.PyRSM(fwhm,minradius=10,maxradius=65,pxscale=pxscale_irdis,ncore=4)

# Add a cube
d.add_cube(psf,cube_empty, angs)

# Add several methods

# Add several methods

d.add_method('APCA')
d.add_method('NMF')
d.add_method('LLSG')

# Load optimal set of parameters for the PSF-subtraction techniques from previous step

d.load_parameters('/Users/.../SPHERE_51ERI_optimal_param')

# Computation of the  RSM detection map of empty cube

d.opti_map(estimator='Forward',colmode='median',threshold=False)

# Plot final probability map

plot_frames(d.final_map)

# Computation of the contrast curve for a completeness level of 90% for the angular distances of 10, 20, 30 and 40 pixels from the center.
# The detection map being computed at the previous step no probability map (probmap) has to be provided.

contrast_curve=d.contrast_curve([10,20,30,40,50,60],[2.5e-3,1.5e-4,5e-5,3.5e-5,2.5e-6,2e-6],probmap=None,psf_oa=[psf_oa],n_fc=10,completeness=0.9)

