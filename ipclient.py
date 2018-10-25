#-*-coding:cp1252-*-

from socket import *

import sys
import json
import struct

from definitions import *

DEFAULT_ADDRESS = '127.0.0.1'

MESSAGE_TIMEOUT = 0.02

class Connection:

  setpointBuffer = bytearray( BUFFER_SIZE )

  def __init__( self ):
    self.eventSocket = socket( AF_INET, SOCK_STREAM )
    self.axisSocket = socket( AF_INET, SOCK_DGRAM )
    self.jointSocket = socket( AF_INET, SOCK_DGRAM )

    self.isConnected = False

  def __del__( self ):
    self.Disconnect()

  def Connect( self, host ):
    try:
      self.Disconnect()
      self.eventSocket.connect( ( host, 50000 ) )
      self.eventSocket.settimeout( 5.0 )
      self.axisSocket.connect( ( host, 50001 ) )
      self.axisSocket.sendall( bytearray( BUFFER_SIZE ) )
      self.axisSocket.settimeout( MESSAGE_TIMEOUT )
      self.jointSocket.connect( ( host, 50002 ) )
      self.jointSocket.sendall( bytearray( BUFFER_SIZE ) )
      self.jointSocket.settimeout( MESSAGE_TIMEOUT )
      self.isConnected = True
      print( 'client connected' )
    except:
      print( sys.exc_info() )
      self.isConnected = False

  def Disconnect( self ):
    if self.isConnected:
      self.eventSocket.close()
      self.axisSocket.close()
      self.jointSocket.close()
      self.isConnected = False

  def RefreshInfo( self ):
    robotsInfo = {}
    if self.isConnected:
      messageBuffer = bytearray( [ REQUEST_INFO ] )
      try:
        self.eventSocket.sendall( messageBuffer )
        robotsInfoString = self.eventSocket.recv( BUFFER_SIZE )
        print( 'RefreshInfo: received JSON string: ' + str(robotsInfoString[1:], 'utf-8').strip( '\0' ) )
        if robotsInfoString[ 0 ] == REQUEST_INFO: robotsInfo = json.loads( str(robotsInfoString[1:], 'utf-8').strip( '\0' ) )
      except:
        print( sys.exc_info() )
        robotsInfo = {}

    robotID = robotsInfo.get( 'id', '' )
    jointsList = robotsInfo.get( 'joints', [] )
    axesList = robotsInfo.get( 'axes', [] )

    return ( robotID, ( jointsList, axesList ) )

  def SendCommand( self, commandKey ):
    if self.isConnected:
      messageBuffer = bytearray( [ commandKey ] )
      print( 'SendCommand: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.sendall( messageBuffer )
      except:
        print( sys.exc_info() )

  def SetUser( self, userName ):
    if self.isConnected:
      messageBuffer = bytearray( [ SET_USER ] ) + userName.encode()
      print( 'SetUser: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.sendall( messageBuffer )
      except:
        print( sys.exc_info() )

  def CheckState( self, eventNumber ):
    return false
    #return self.eventSocket.recv( BUFFER_SIZE )

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

  def ReceiveJointMeasures( self, jointIndex, measures ):
    return self._ReceiveMeasures( self.jointSocket, jointIndex, measures )
