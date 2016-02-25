#ifndef SENDER_DATA_POINT_HH
#define SENDER_DATA_POINT_HH

#include "simulationresults.pb.h"

/**
 * Represents the data that is logged relating to a single sender at a single
 * point in time.
 */
class SenderDataPoint
{

public:

  SimulationResultBuffers::SenderDataPoint DNA( void ) const
  {
    SimulationResultBuffers::SenderDataPoint ret;
    ret.set_average_throughput( average_throughput );
    ret.set_average_delay( average_delay );
    ret.set_sending_duration( sending_duration );
    ret.set_packets_received( packets_received );
    ret.set_total_delay( total_delay );
    ret.set_window_size( window_size );
    ret.set_intersend_time( intersend_time );
    return ret;
  }

  SenderDataPoint( double average_throughput, double average_delay, double sending_duration,
      unsigned int packets_received, double total_delay, unsigned int window_size,
      double intersend_time ) :
    average_throughput( average_throughput ),
    average_delay( average_delay ),
    sending_duration( sending_duration ),
    packets_received( packets_received ),
    total_delay( total_delay ),
    window_size( window_size ),
    intersend_time( intersend_time ) {};

private:
  double average_throughput = 0;
  double average_delay = 0;
  double sending_duration = 0;
  unsigned int packets_received = 0;
  double total_delay = 0;
  unsigned int window_size = 0;
  double intersend_time = 0;
};

#endif // SENDER_DATA_POINT_HH
