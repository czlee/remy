#include <unistd.h>

#include <system_error>
#include <iostream>
#include <cmath>

#include "fader.hh"

using namespace std;

template <class NetworkType>
void Fader::update( NetworkType & network )
{
  /* data ready to read? */
  while ( true ) {
    array< uint8_t, 4096 > read_buffer;
    ssize_t bytes_read = read( fd_, &read_buffer, read_buffer.size() );

    if ( bytes_read > 0 ) {
      buffer_.insert( buffer_.end(), read_buffer.begin(), read_buffer.begin() + bytes_read );
    } else if ( bytes_read == 0 ) {
      throw runtime_error( "EOF from fader" );
    } else if ( errno == EAGAIN or errno == EWOULDBLOCK ) {
      break;
    } else {
      throw system_error( errno, system_category() );
    }
  }

  auto new_physical_values = physical_values_;

  /* process what we have */
  while ( buffer_.size() >= 3 ) {
    /* check channel */
    const uint8_t channel = buffer_.front();
    buffer_.pop_front();
    if ( channel != 176 ) {
      throw runtime_error( "unknown MIDI channel" );
    }

    /* get control */
    const uint8_t control = buffer_.front();
    buffer_.pop_front();

    /* get value */
    const uint8_t value = buffer_.front();
    buffer_.pop_front();

    if ( control >= physical_values_.size() ) {
      throw runtime_error( "unexpected MIDI control number" );
    }

    if ( value >= 128 ) {
      throw runtime_error( "unexpected MIDI control value" );
    }

    new_physical_values.at( control ) = value;
  }

  auto output_physical_values = new_physical_values;

  /* process the changes */
  for ( unsigned int i = 0; i < physical_values_.size(); i++ ) {
    if ( physical_values_.at( i ) != new_physical_values.at( i ) ) {
      if ( i >= 65 and i <= 80 ) { /* switch a sender */
	if ( i <= 72 ) {
	  const unsigned int sender_num = i - 65;
	  if ( sender_num < network.mutable_senders().mutable_gang1().count_senders() ) {
	    if ( new_physical_values.at( i ) ) {
	      network.mutable_senders().mutable_gang1().mutable_sender( sender_num ).switch_on( network.tickno() );
	    } else {
	      network.mutable_senders().mutable_gang1().mutable_sender( sender_num ).switch_off( network.tickno(), 1 );
	    }
	  } else {
	    output_physical_values.at( i ) = 0;
	  }
	} else {
	  const unsigned int sender_num = i - 73;
	  if ( sender_num < network.mutable_senders().mutable_gang2().count_senders() ) {
	    if ( new_physical_values.at( i ) ) {
	      network.mutable_senders().mutable_gang2().mutable_sender( sender_num ).switch_on( network.tickno() );
	    } else {
	      network.mutable_senders().mutable_gang2().mutable_sender( sender_num ).switch_off( network.tickno(), 1 );
	    }
	  } else {
	    output_physical_values.at( i ) = 0;
	  }
	}
      }

      /* switch link speed */
      if ( i == 81 ) {
	const double new_speed = 0.316227766016838 * pow( 100.0, new_physical_values.at( i ) / 127.0 );
	network.mutable_link().set_rate( new_speed );
      } else if ( i == 88 ) {
	time_increment_ = (pow( 1.05, new_physical_values.at( i ) ) - 1) / 500;
      } else if ( i == 87 ) {
	horizontal_size_ = pow( 1.05, new_physical_values.at( i ) / 2.0 );
      }
    }
  }

  /* write the output physical values */
  for ( unsigned int i = 0; i < physical_values_.size(); i++ ) {
    if ( output_physical_values.at( i ) != new_physical_values.at( i ) ) {
      array< uint8_t, 3 > write_buffer = { 176, uint8_t( i ), output_physical_values.at( i ) };
      ssize_t bytes_written = write( fd_, &write_buffer, write_buffer.size() );      
      if ( bytes_written != 3 ) {
	throw runtime_error( "could not write to MIDI device" );
      }
    }
  }

  physical_values_ = output_physical_values;
}