
"""
Methods for getting the photon energy
from a psana event, and comparting it
to the Se K-edge
"""

# global sources -- up here so they only get initialized once
cspad_ds2_src  = psana.Source('DetInfo(CxiDs2.0:Cspad.0)')
spc_src        = psana.Source('BldInfo(FEE-SPEC0)')
evr_src        = psana.Source('DetInfo(NoDetector.0:Evr.0)')



class Event(object):

    def __init__(self, psana_event):
        self._psana_event = psana_event
        return


    @property
    def corrected_ds2(self):
        cspad = evt.get(psana.ndarray_float32_3,
                        cspad_ds2_src,
                        'calibrated_ndarr')
        return cspad


    @property
    def mcc_photon_energy(self):
        """
        output in eV
        """
        ebeamPhotonEnergy()


    @property
    def fee_photon_energy(self, ev_per_pixel):
        """
        output in eV
        """

        try:
            spc = evt.get(psana.Bld.BldDataSpectrometerV1, spc_src)
            trace = np.copy(spc.hproj())
        except:
            print 'No spectral data for shot: %d' % shot_index

        trace = trace - np.median(trace)
        trace[trace < 0.0] = 0.0

        avg = np.average(np.arange(len(trace), weights=trace)) * ev_per_pixel
        return avg



