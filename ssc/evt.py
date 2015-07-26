
"""
Methods for getting the photon energy
from a psana event, and comparting it
to the Se K-edge
"""

import numpy as np
import psana


# global sources -- up here so they only get initialized once
cspad_ds2_src  = psana.Source('DetInfo(CxiDs1.0:Cspad.0)')
spc_src        = psana.Source('BldInfo(FEE-SPEC0)')
ebeam_src      = psana.Source('BldInfo(EBeam)')
evr_src        = psana.Source('DetInfo(NoDetector.0:Evr.0)')



class Event(object):

    def __init__(self, psana_event):
        self._psana_event = psana_event
        return


    @property
    def corrected_ds1(self):
        cspad = self._psana_event.get(psana.ndarray_float32_3,
                                      cspad_ds2_src,
                                      'calibrated_ndarr')
        return cspad


    @property
    def mcc_photon_energy(self):
        """
        output in eV
        """
        ebeam = self._psana_event.get(psana.Bld.BldDataEBeamV7, ebeam_src)
        return ebeam.ebeamPhotonEnergy()


    @property
    def fee_photon_energy(self):
        """
        output in eV
        """

        ev_per_pixel = 1.0 # NEEDS CALIBRATION

        try:
            spc = self._psana_event.get(psana.Bld.BldDataSpectrometerV1, spc_src)
            trace = np.copy(spc.hproj())
        except:
            return -1.0

        trace = trace - np.median(trace)
        trace[trace < 0.0] = 0.0

        avg = np.average(np.arange(len(trace)), weights=trace) * ev_per_pixel
        return avg



def data_source(run, expt='cxic0415', times=None):
    """
    Replacement data source (event generator)
    """

    cfg_path = '/reg/neh/home2/tjlane/analysis/ssc-com/ssc/psana.cfg' # hardwired for now :(
    psana.setConfigFile(cfg_path)

    ds = psana.DataSource('exp=CXI/%s:run=%d:idx' % (expt, run))
    
    for r in ds.runs():
        if times == None:
            times = r.times()
        for t in times:
            yield Event(r.event(t))




