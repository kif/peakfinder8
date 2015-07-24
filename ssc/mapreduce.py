#!/usr/bin/env python

"""
Core classes. Based on work from TJ Lane
"""

import sys
import psana
import mpi4py
import mpi4py.MPI
import math
import time
import datetime
from utils.io_utils import dirname_from_source_runs
from data_recovery_backends.psana_data_recovery import *

class MapReducer(object):
    """
    A class to perform flexible map-reduction.
    """

    # Constants for syntatic sugar
    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000

    def __init__(self, map_func, reduce_func, source, monitor_params):
        """
        Initialization of the MapReducer object

        Parameters
        ----------
        map_func : function
            Function that takes a psana 'event' object and returns some value
            of interest.

        reduce_func : function
            Function that takes the output of `map_func`, as well as a
            previously stored result, and generates and updated solution. Note
            that powerful and flexible operations can be performed by
            using a class method here...

        source : str
            This specifies the data source you wish to access. Can either be
            shared memory, specified by the hutch followed by 'shmem'
            (eg. 'cxishmem'), or an experiment identifier (eg. 'cxi4113').

        event_rejection_threshold: float
            Maximum delay between the psana event timestamp and the current time for events to be processed. The goal
            of setting an event_rejection_threshold is to drain the psana event queue and make sure to get fresh events

        """


        # This variable is used not to trigger random access to data when the monitor is running online.
        # Used only for debugging purposes
        debug = False

        self.mpi_rank = mpi4py.MPI.COMM_WORLD.Get_rank()
        self.mpi_size = mpi4py.MPI.COMM_WORLD.Get_size()
        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        self.monitor_params = monitor_params

        # Default values
        self.event_rejection_threshold = 10000000000
        self.offline = False
        self.source = source

        # Set offline mode depending on source
        if 'shmem' not in self.source and debug == False:
            self.offline = True
            if not self.source[-4:] == ':idx':
                self.source = self.source + ':idx'

        # Set event_rejection threshold
        if self.monitor_params['Backend']['event_rejection_threshold'] != None:
            self.event_rejection_threshold = int(self.monitor_params['Backend']['event_rejection_threshold'])

        # Set map,reduce and extract functions
        self.map = map_func
        self.reduce = reduce_func
        self.extract_data = extract

        if self.offline == True:
            try:              
                self.first_event = int(monitor_params['General']['event_range'].split('-')[0])
            except:
                self.first_event = 0
            try: 
                self.last_event = int(monitor_params['General']['event_range'].split('-')[1])
            except:
                self.last_event = 0

        # The following is executed only on the master node
        if self.role == 'master':
            self.num_nomore = 0
            if self.offline == True:
                self.source_runs_dirname = dirname_from_source_runs(source)
               
        return


    def shutdown(self, msg='reason not provided'):
        """
        Shutdown of the MapReduce mechanism
        """
        print "Shutting down, (%s)" % msg


        # Gracefully shut down worker
        if self.role == 'worker':
            self._buffer = mpi4py.MPI.COMM_WORLD.send(dest=0, tag=self.DEADTAG)
            mpi4py.MPI.Finalize()
            sys.exit(0)


        # Tell all workers to die and shut down the monitor when all the workers
        # report as dead
        if self.role == 'master':
            try:
                for nod_num in range(1, self.mpi_size()):
                    mpi4py.MPI.COMM_WORLD.isend(0, dest = nod_num, tag = self.DIETAG)
                num_shutdown_confirm = 0
                while True:
                    if mpi4py.MPI.COMM_WORLD.Iprobe(source=mpi4py.MPI.ANY_SOURCE, tag=0):
                        self._buffer = mpi4py.COMM.recv(source=mpi4py.MPI.ANY_SOURCE, tag=0)
                    if mpi4py.MPI.COMM_WORLD.Iprobe(source=mpi4py.MPI.ANY_SOURCE, tag=self.DEADTAG):
                        num_shutdown_confirm += 1
                    if num_shutdown_confirm == self.mpi_size()-1:
                        break
                mpi4py.MPI.Finalize()
            except:
                mpi4py.MPI.COMM_WORLD.Abort(0)
            sys.exit(0)
        return


    def start(self, verbose = False):
        """
        Starts the monitor
        """

        #  The following is executed on each worker
        if self.role == 'worker':

            req = None

            # Identify which events each worker will process:
            # - when using shared memory, the DAQ/shmem process takes
            #   care of serving up individual events,
            # - when running offline, we use XTC random access to iterate through events
            if self.offline == False:
                psana_events = psana.DataSource(self.source).events()
            else:
                def psana_events_generator():
                    # identify which events this RANK will process
                    for r in psana.DataSource(self.source).runs():
                        times = r.times()
                        if self.last_event == 0:
                            self.last_event = len(times)
                        realtimes = times[self.first_event:self.last_event]                        
                        mylength = int(math.ceil(len(realtimes)/float(self.mpi_size-1)))
                        mytimes = realtimes[(self.mpi_rank-1)*mylength:(self.mpi_rank)*mylength]
                        for mt in mytimes:
                            yield r.event(mt)
                psana_events = psana_events_generator()

            # Loop over events and process
            for evt in psana_events:

                # Reject events above the rejection threshold
                event_id = str(evt.get(psana.EventId))
                timestring = event_id.split('time=')[1].split(',')[0]
                timestamp = time.strptime(timestring[:-6],'%Y-%m-%d %H:%M:%S.%f')
                timestamp = datetime.datetime.fromtimestamp(time.mktime(timestamp))
                timenow = datetime.datetime.now()

                if (timenow-timestamp).seconds > self.event_rejection_threshold:
                    continue

                self.event_timestamp = timestring

                # Check if a shutdown message is coming from the server
                if mpi4py.MPI.COMM_WORLD.Iprobe(source = 0, tag = self.DIETAG):
                    self.shutdown('Shutting down RANK: %i' % self.mpi_rank)

                self.extract_data(evt, self)

                if self.data_as_slab == None:
                   continue

                result = self.map()

                # send the mapped event data to the master process
                if req: req.Wait() # be sure we're not still sending something
                req = mpi4py.MPI.COMM_WORLD.isend(result, dest=0, tag=0)

            # When all events have been processed, send the master a dictionary with an 'end'
            # flag and die
            end_dict = {}
            end_dict['end'] = True
            if req:
                req.Wait() # be sure we're not still sending something
            dump = mpi4py.MPI.COMM_WORLD.isend((end_dict, self.mpi_rank), dest=0, tag=0)
            mpi4py.MPI.Finalize()
            sys.exit(0)


        # The following is executed on the master
        elif self.role == 'master':

            if verbose:
                print 'Starting master'

            self.num_reduced_events = 0

            # Loops continuously waiting for processed data from workers
            while True:

                try:

                    buffer = mpi4py.MPI.COMM_WORLD.recv(source=mpi4py.MPI.ANY_SOURCE, tag=0)
                    if 'end' in buffer[0].keys():
                        print 'Finalizing', buffer[1]
                        self.num_nomore += 1
                        if self.num_nomore == self.mpi_size-1:
                            print 'All workers have run out of events. Shutting down'
                            self.end_processing()
                            mpi4py.MPI.Finalize()
                            sys.exit(0)

                    self.reduce(buffer)
                    self.num_reduced_events += 1

                except KeyboardInterrupt as e:
                    print 'Recieved keyboard sigterm...'
                    print e
                    print 'shutting down MPI.'
                    self.shutdown()
                    print '---> execution finished'
                    sys.exit(0)

        return



    def end_processing(self):
        """
        Executed by the Master node after all events have been processed.
        """

        # OVERRIDE THIS TO PERFORM AN ACTION AT THE END OF THE RUN

        pass
