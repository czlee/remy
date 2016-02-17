#include "fish.hh"

Fish::Fish( WhiskerTree & whiskers, const unsigned int prng_seed, const bool track )
  :  _whiskers( whiskers ),
     _memory(),
     _packets_sent( 0 ),
     _packets_received( 0 ),
     _track( track ),
     _flow_id( 0 ),
     _last_send_time( 0 ),
     _next_send_time( 0 ),
     _prng( prng_seed ),
     _distribution( 1, _prng )
{
  _generate_next_send_time();
}

void Fish::packets_received( const std::vector< Packet > & packets ) {
  _packets_received += packets.size();
  _memory.packets_received( packets, _flow_id );
  const FishWhisker & current_whisker( _whiskers.use_whisker( _memory, _track ) );
  _update_lambda( current_whisker.lambda() );
}

void Fish::reset( const double & )
{
  _memory.reset();
  _next_send_time = 0;
  _generate_next_send_time();
  _update_lambda( 1 );
  _flow_id++;
  assert( _flow_id != 0 );
}

double Fish::next_event_time( const double & tickno ) const
{
  if ( tickno <= _next_send_time ) {
    return tickno;
  } else {
    return _next_send_time;
  }
}

template <class NextHop>
void Fish::send( const unsigned int id, NextHop & next, const double & tickno,
    const int packets_sent_cap )
{
  if ( _next_send_time <= tickno ) {
    Packet p( id, _flow_id, tickno, _packets_sent );
    _packets_sent++;
    _memory.packet_sent( p );
    next.accept( p, tickno );
    _generate_next_send_time();
  }
}

/**
 * Increases _next_send_time by an intersend time drawn from an exponential
 * distribution. Called on construction, reset and whenever a packet is sent.
 * The result is stored in _next_send_time so this value does not change every
 * time next_event_time() is called.
 */
void Fish::_generate_next_send_time( void )
{
  _last_send_time = _next_send_time;
  _next_send_time += _distribution.sample();
}

/**
 * Updates lambda.
 * Lambda isn't stored in Fish itself; this just updates the distribution.
 * It also converts the current next_send_time accordingly, so that the change
 * can take effect immediately, rather than waiting until the next packet.
 */
void Fish::_update_lambda( double lambda )
{
  double old_lambda = _distribution.lambda();
  _next_send_time *= old_lambda / lambda;
  _distribution.set_lambda( lambda );
}