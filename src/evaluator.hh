#ifndef EVALUATOR_HH
#define EVALUATOR_HH

#include <string>
#include <vector>

#include "random.hh"
#include "whiskertree.hh"
#include "simulationresults.hh"
#include "network.hh"
#include "problem.pb.h"
#include "answer.pb.h"

class Evaluator
{
public:

  class Outcome
  {
  public:
    double score;
    std::vector< std::pair< NetConfig, std::vector< std::pair< double, double > > > > throughputs_delays;
    WhiskerTree used_whiskers;
    SimulationResults simulation_results;

    Outcome( WhiskerTree whiskers ) : score( 0 ), throughputs_delays(),
        used_whiskers( whiskers ), simulation_results( whiskers ) {}

    Outcome( const AnswerBuffers::Outcome & dna );

    AnswerBuffers::Outcome DNA( void ) const; // does not include simulation_results
  };

private:
  const unsigned int _prng_seed;
  unsigned int _tick_count;
  double _log_interval_ticks;

  std::vector< NetConfig > _configs;

public:
  Evaluator( const ConfigRange & range );

  ProblemBuffers::Problem DNA( const WhiskerTree & whiskers ) const;

  Outcome score( WhiskerTree & run_whiskers,
		 const bool trace = false,
		 const double carefulness = 1,
     const bool log_simulation = false ) const;

  static Evaluator::Outcome parse_problem_and_evaluate( const ProblemBuffers::Problem & problem );

  static Outcome score( WhiskerTree & run_whiskers,
			const unsigned int prng_seed,
			const std::vector<NetConfig> & configs,
			const bool trace,
			const unsigned int ticks_to_run,
      const double _log_interval = 1000,
      const bool log_simulation = false );
};

#endif
