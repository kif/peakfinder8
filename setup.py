
from distutils.core import setup, Extension
from Cython.Build import cythonize
from glob import glob

peakfinder8_ext = Extension( "ssc.peakfinder8_extension",
                             sources=["ext/peakfinder8/peakfinder8_extension.pyx",
                                      "ext/peakfinder8/peakfinders.cpp"] ,
                             include_dirs = ['/reg/g/psdm/sw/releases/ana-current/arch/x86_64-rhel6-gcc44-opt/geninc/'],
                             library_dirs = ['/reg/g/psdm/sw/releases/ana-current/arch/x86_64-rhel6-gcc44-opt/lib'],
                             language = "c++" )


setup(name="ssc", 
      packages    = ['ssc'],
      package_dir = {'ssc' : 'ssc'},
      ext_modules=cythonize(peakfinder8_ext),
      scripts=[s for s in glob('scripts/*') if not s.endswith('__.py')]
     )

