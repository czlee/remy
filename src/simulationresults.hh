#ifndef SIMULATIONRESULTS_HH
#define SIMULATIONRESULTS_HH

#include "network.hh"
#include "whiskertree.hh"
#include "simulationresults.pb.h"
#include "senderdatapoint.hh"
#include <vector>

class SimulationResults;
class SimulationRunData;
class SimulationRunDataPoint;

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
  void add_sender_data( std::vector< SenderDataPoint > );

private:
  double seconds;
  std::vector< SenderDataPoint > sender_data;
};

#endif // SIMULATIONRESULTS_HH