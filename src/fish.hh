#ifndef FISH_HH
#define FISH_HH

#include <vector>
#include "whiskertree.hh"
#include "exponential.hh"
#include "packet.hh"
#include "random.hh"

class FishMemory {
public:
  void packet_sent( const Packet & packet __attribute((unused)) ) {};
  void packets_received( const std::vector< Packet > & packets, const unsigned int flow_id );
};

/**
 * A sender that sends packets according to a Poisson point process. It has a
 * single state, called lambda, being the rate parameter of the Poisson point
 * process (i.e., the expected number of packets per unit time). The mean
 * intersend time is then given by 1/lambda.
 *
 * This class implements the SenderType interface for SwitchedSender
 * (in sender.hh).
 */
class Fish
{
private:
  const WhiskerTree & _whiskers;
  FishMemory _memory;

  int _packets_sent, _packets_received;
  bool _track;
  unsigned int _flow_id;

  double _last_send_time;
  double _next_send_time;

  PRNG _prng;
  Exponential _distribution;

  void _update_lambda( double lambda );
  void _generate_next_send_time();

public:
  Fish( WhiskerTree & whiskers, const unsigned int prng_seed, const bool track=false );

  void packets_received( const std::vector< Packet > & packets );

  void reset( const double & tickno ); /* start new flow */

  template <class NextHop>
  void send( const unsigned int id, NextHop & next, const double & tickno,
       const int packets_sent_cap = std::numeric_limits<int>::max() );

  const WhiskerTree & whiskers( void ) const { return _whiskers; }

  Fish & operator=( const Fish & ) { assert( false ); return *this; }

  double next_event_time( const double & tickno ) const;

  const int & packets_sent( void ) const { return _packets_sent; }
};

#endif // FISH_HH