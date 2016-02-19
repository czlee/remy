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

  void set_prng_seed( unsigned int prng_seed ) { this->prng_seed = prng_seed; }
  void set_tick_count( unsigned int tick_count ) { this->tick_count = tick_count; }
  void set_log_interval_ticks( unsigned int log_interval_ticks ) { this->log_interval_ticks = log_interval_ticks; }

private:
  WhiskerTree whiskers;
  std::vector< struct SimulationRunData > run_data;

  // problem settings
  unsigned int prng_seed = 0;
  unsigned int tick_count = 0;
  unsigned int log_interval_ticks = 0;
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