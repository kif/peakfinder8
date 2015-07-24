
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



def peakfind_cheetah8(image):

    return


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


if __name__ == '__main__':
    

    from scipy import ndimage as ndi
    import matplotlib.pyplot as plt
    from skimage.feature import peak_local_max
    from skimage import data, img_as_float

    im = img_as_float(data.coins())
    im = np.expand_dims(im, axis=0)
    print im.shape


    output = peakfind_blob(im, sigma_threshold=1.0)

    fig = plt.figure()
    ax = plt.subplot(111)

    ax.imshow(im[0,:,:], cmap=plt.cm.gray)
    ax.autoscale(False)
    ax.plot(output[:, 2], output[:, 1], 'r.')

    plt.show()


