#ifndef SIMULATIONRESULTS_HH
#define SIMULATIONRESULTS_HH

#include "network.hh"
#include "whiskertree.hh"
#include "simulationresults.pb.h"
#include <vector>

class SimulationResults;
struct SimulationRunData;
struct SimulationRunDataPoint;
struct SenderDataPoint;

// top level results class
class SimulationResults
{
public:
  SimulationResults() : whiskers(), run_data() {};
  SimulationResults( WhiskerTree whiskers ) : whiskers( whiskers ), run_data() {};

  SimulationResultBuffers::SimulationsData DNA( void ) const;

  // Adds a run and returns a reference to it
  SimulationRunData & add_run_data( const NetConfig & config );

private:
  WhiskerTree whiskers;
  std::vector< struct SimulationRunData > run_data;

  // problem settings
  const unsigned int prng_seed = 0;
  const unsigned int tick_count = 0;
};

class SimulationRunData
{
  friend class SimulationResults;

public:
  SimulationRunData( NetConfig config ) : config( config ), data() {};

  // Adds a data point and returns a reference to it
  struct SimulationRunDataPoint & add_datum( double seconds );

private:
  NetConfig config;
  std::vector< struct SimulationRunDataPoint > data;
};

class SimulationRunDataPoint
{
  friend SimulationResultBuffers::SimulationsData SimulationResults::DNA ( void ) const;

public:
  SimulationRunDataPoint( double seconds ) : seconds( seconds ), sender_data() {};

  // expects pairs of < throughput, delay >
  void add_sender_data( std::vector< std::pair< double, double> > );

private:
  double seconds;
  std::vector< struct SenderDataPoint > sender_data;
};

class SenderDataPoint
{
  friend SimulationResultBuffers::SimulationsData SimulationResults::DNA ( void ) const;

public:
  SenderDataPoint( double average_throughput_since_start, double average_delay_since_start ) :
    average_throughput_since_start( average_throughput_since_start ),
    average_delay_since_start( average_delay_since_start ) {};

private:
  double average_throughput_since_start = 0;
  double average_delay_since_start = 0;
};

#endif // SIMULATIONRESULTS_HH