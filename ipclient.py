#-*-coding:cp1252-*-

from socket import *

import sys
import struct

from definitions import *

DEFAULT_ADDRESS = '127.0.0.1:50000'

class Connection:

  setpointBuffer = bytearray( BUFFER_SIZE )

  def __init__( self ):
    self.eventSocket = socket( AF_INET, SOCK_STREAM )
    self.axisSocket = socket( AF_INET, SOCK_DGRAM )

    self.isConnected = False

  def __del__( self ):
    self.Disconnect()

  def Connect( self, address ):
    addressParts = address.split( ':' )
    host = addressParts[ 0 ]
    port = int( addressParts[ 1 ] )
    try:
      self.Disconnect()
      self.eventSocket.connect( ( host, port ) )
      self.eventSocket.settimeout( 5.0 )
      self.axisSocket.connect( ( host, port ) )
      self.axisSocket.sendall( bytearray( BUFFER_SIZE ) )
      self.axisSocket.settimeout( 2 * MESSAGE_TIMEOUT )
      self.isConnected = True
      print( 'client connected' )
    except:
      print( sys.exc_info() )
      self.isConnected = False

  def Disconnect( self ):
    if self.isConnected:
      self.eventSocket.close()
      self.axisSocket.close()
      self.isConnected = False

  def SendRequest( self, opcode, dataString='' ):
    replyCode = 0
    replyString = ''
    if self.isConnected:
      messageBuffer = bytearray( [ opcode ] ) + dataString.encode() + bytearray( [ 0 ] )
      print( 'SendRequest: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.sendall( messageBuffer )
        replyData = self.eventSocket.recv( BUFFER_SIZE )
        replyCode = replyData[ 0 ]
        replyString = str(replyData[ 1: ], 'utf-8').strip( '\0' )
      except:
        print( sys.exc_info() )
    return ( replyCode, replyString )

  def ReceiveReply( self ):
    replyCode = 0
    replyString = ''
    if self.isConnected:
      try:
        replyData = self.eventSocket.recv( BUFFER_SIZE )
        replyCode = replyData[ 0 ]
        replyString = str(replyData[ 1: ], 'utf-8').strip( '\0' )
      except:
        print( sys.exc_info() )
    return ( replyCode, replyString )

  def _SendSetpoints( self, dataSocket, deviceIndex, setpoints ):
    if self.isConnected:
      struct.pack_into( 'BB', self.setpointBuffer, 0, 1, deviceIndex )
      for setpointIndex in range( len(setpoints) ):
        setpointOffset = 2 + setpointIndex * FLOAT_SIZE
        struct.pack_into( 'f', self.setpointBuffer, setpointOffset, setpoints[ setpointIndex ] )
      #print( '_SendSetpoints: sending message buffer: ' + str( list( self.setpointBuffer ) ) )
      try:
        dataSocket.sendall( self.setpointBuffer )
      except:
        #print( sys.exc_info() )
        pass

  def SendAxisSetpoints( self, axisIndex, setpoints ):
    self._SendSetpoints( self.axisSocket, axisIndex, setpoints )

  def _ReceiveMeasures( self, dataSocket, deviceIndex, measures ):
    if self.isConnected:
      try:
        messageBuffer = dataSocket.recv( BUFFER_SIZE )
        devicesNumber = int( messageBuffer[ 0 ] )
        #print( '_ReceiveMeasures: received values for: ' + str( devicesNumber ) + ' axes' )
        for deviceCount in range( devicesNumber ):
          dataOffset = deviceCount * ( 1 + len(measures) * FLOAT_SIZE ) + 1
          #print( '_ReceiveMeasures: comparing indexes: ' + str( int( messageBuffer[ dataOffset ] ) ) + '/' + str( deviceIndex ) )
          if int( messageBuffer[ dataOffset ] ) == deviceIndex:
            for measureIndex in range( len(measures) ):
              measureOffset = dataOffset + 1 + measureIndex * FLOAT_SIZE
              measures[ measureIndex ] = struct.unpack_from( 'f', messageBuffer, measureOffset )[ 0 ]
            return True
      except:
        #print( sys.exc_info() )
        pass
    return False

  def ReceiveAxisMeasures( self, axisIndex, measures ):
    return self._ReceiveMeasures( self.axisSocket, axisIndex, measures )
