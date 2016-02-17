#ifndef EXPONENTIAL_HH
#define EXPONENTIAL_HH

#include <boost/random/exponential_distribution.hpp>

#include "random.hh"

class Exponential
{
private:
  boost::random::exponential_distribution<> distribution;

  PRNG & prng;

public:
  Exponential( const double & rate, PRNG & s_prng ) : distribution( rate ), prng( s_prng ) {}

  double sample( void ) { return distribution( prng ); }
  double lambda( void ) { return distribution.lambda(); }

  void set_lambda( double lambda ) {
    // replace the distribution
    distribution = boost::random::exponential_distribution<> ( lambda );
  }
};

#endif
