
"""
Simple interface to a bunch of peakfinders. These peakfinders
should share a common interface, namely:

   f(image) --> peaks

where:

-- image : 3d array, panels x slow x fast
-- peaks : 4d array of the peak positions: panel index, slow, fast, intensity
"""

import numpy as np

from skimage.feature import peak_local_max
from pypsalg import find_blobs as fb

from ssc.peakfinder8_extension import peakfinder_8 as pf8


def peakfind_skimage(image, min_distance=20):

    panels = []
    assert len(image.shape) == 3

    for i in range(image.shape[0]):

        coords = peak_local_max(image[i,:,:], min_distance=min_distance)
        p_ind  = np.ones(coords.shape[0]) * i
        intens = image[i][coords[:,0],coords[:,1]]

        panels.append( np.hstack([ p_ind[:,np.newaxis], 
                                   coords, 
                                   intens[:,np.newaxis] ]) )

    return np.vstack(panels)



def peakfind_8(image, mask=None, max_num_peaks=5000,
               adc_thresh=150.0, min_snr=5.0, min_pix_count=2, 
               max_pix_count=20, local_bg_radius=3):


    # operate on a single panel,
    # in the future it will be more efficient to pass the entire
    # array through to c++
    asic_nx  = image.shape[2]
    asic_ny  = image.shape[1]
    nasics_x = 1
    nasics_y = 1

    # pix_r is the radius of the pixel from the center
    # used along with local_bg_radius to discard peaks
    # based on geometry
    pix_r = np.ones_like(image) * 1000.

    if mask == None:
        mask = np.ones(image.shape[1:])

    panels = []
    for i in range(image.shape[0]):

        data = image[i,:,:]

        peak_list_x, peak_list_y, peak_list_value = pf8(max_num_peaks,
                                                        data.astype(np.float32),     # 2d, 32 bit float
                                                        mask.astype(np.int8),        # 2d, 8 bit int
                                                        pix_r[i].astype(np.float32), # 2d, 32 bit float
                                                        asic_nx, asic_ny,
                                                        nasics_x, nasics_y,
                                                        adc_thresh, min_snr,
                                                        min_pix_count, max_pix_count,
                                                        local_bg_radius)


        assert len(peak_list_x) == len(peak_list_value)
        assert len(peak_list_y) == len(peak_list_value)

        if len(peak_list_value) > 0:
            p_ind  = np.ones(len(peak_list_value)) * i

            panels.append( np.array([ p_ind,
                                      peak_list_y,
                                      peak_list_x,
                                      peak_list_value ]).T )
 

    if len(panels) > 0:
        result = np.vstack(panels)
    else:
        result = None

    return result



def peakfind_mikhail(image):

    return


def peakfind_blob(image, **kwargs):

    panels = []
    assert len(image.shape) == 3

    for i in range(image.shape[0]):

        coords, widths = fb.find_blobs(image[i,:,:], **kwargs)
        if len(coords) == 0:
            continue
        coords = np.array(coords)

        p_ind  = np.ones(coords.shape[0]) * i
        intens = image[i][coords[:,0].astype(np.int),coords[:,1].astype(np.int)]

        panels.append( np.hstack([ p_ind[:,np.newaxis],
                                   coords,
                                   intens[:,np.newaxis] ]) )

    if len(panels) > 0:
        result = np.vstack(panels)
    else:
        result = None

    return result


def _hugepeak():
    """
    just makes an image with a big blob in the middle
    """

    image = np.abs( np.random.randn(32, 185, 388) )
    image[0,90:100,200:210] = 100.0

    return image


if __name__ == '__main__':
    

    from scipy import ndimage as ndi
    import matplotlib.pyplot as plt
    from skimage.feature import peak_local_max
    from skimage import data, img_as_float

    #im = img_as_float(data.coins())
    #im = np.expand_dims(im, axis=0)

    im = _hugepeak()

    print im.shape


    output = peakfind_8(im, adc_thresh=1.0, min_snr=6.0)

    fig = plt.figure()
    ax = plt.subplot(111)

    ax.imshow(im[0,:,:], cmap=plt.cm.gray)
    ax.autoscale(False)
    ax.plot(output[:, 2], output[:, 1], 'r.')

    plt.show()


