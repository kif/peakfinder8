
from ssc import evt


ds = evt.data_source(24)

for evt in ds:
    print evt.fee_photon_energy


