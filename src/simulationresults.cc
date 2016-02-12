#include "simulationresults.hh"

SimulationRunData & SimulationResults::add_run_data( const NetConfig & config )
{

  run_data.emplace_back( config );
  return run_data.back();
}

SimulationRunDataPoint & SimulationRunData::add_datum( double seconds )
{
  data.emplace_back( seconds );
  return data.back();
}

void SimulationRunDataPoint::add_sender_data( std::vector< SenderDataPoint > new_data )
{
  sender_data.insert( sender_data.end(), new_data.begin(), new_data.end() );
}

SimulationResultBuffers::SimulationsData SimulationResults::DNA( void ) const
{
  SimulationResultBuffers::SimulationsData ret;

  ret.mutable_whiskers()->CopyFrom( whiskers.DNA() );

  ProblemBuffers::ProblemSettings settings;
  settings.set_prng_seed( prng_seed );
  settings.set_tick_count( tick_count );
  ret.mutable_settings()->CopyFrom( settings );

  for ( const auto &run : run_data ) {
    SimulationResultBuffers::SimulationRunData * run_data_pb = ret.add_run_data();
    run_data_pb->mutable_config()->CopyFrom( run.config.DNA() );

    for ( const auto &datum : run.data ) {
      SimulationResultBuffers::SimulationRunDataPoint * data_pb = run_data_pb->add_point();
      data_pb->set_seconds( datum.seconds );

      for (const auto &sender_datum : datum.sender_data ) {
        SimulationResultBuffers::SenderDataPoint * sender_data_pb = data_pb->add_sender_data();
        sender_data_pb->CopyFrom( sender_datum.DNA() );
      }
    }
  }

  return ret;
}
