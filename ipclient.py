#-*-coding:cp1252-*-

from socket import *

import sys
import json
import struct

from definitions import *

DEFAULT_ADDRESS = '127.0.0.1'

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
      self.axisSocket.settimeout( 0.1 )
      self.jointSocket.connect( ( host, 50002 ) )
      self.jointSocket.sendall( bytearray( BUFFER_SIZE ) )
      self.jointSocket.settimeout( 0.1 )
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
      messageBuffer = bytearray( [ 0 ] )
      try:
        self.eventSocket.sendall( messageBuffer )
        robotsInfoString = self.eventSocket.recv( BUFFER_SIZE )
        stringTerminator = str(robotsInfoString).find( '\0' )
        robotsInfoString = str(robotsInfoString)[ :stringTerminator ]
        print( 'RefreshInfo: received JSON string: ' + robotsInfoString )
        robotsInfo = json.loads( robotsInfoString )
      except:
        print( sys.exc_info() )
        robotsInfo = {}

    robotsList = robotsInfo.get( 'robots', [] )
    jointsList = robotsInfo.get( 'joints', [] )
    axesList = robotsInfo.get( 'axes', [] )

    return ( robotsList, jointsList, axesList )

  def SendCommand( self, robotIndex, commandKey ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, robotIndex, commandKey ] )
      print( 'SendCommand: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.sendall( messageBuffer )
      except:
        print( sys.exc_info() )

  def SetUser( self, userName ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, 0, SET_USER ] ) + userName.encode()
      print( 'SetUser: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.sendall( messageBuffer )
      except:
        print( sys.exc_info() )

  def CheckState( self, eventNumber ):
    return false
    #return self.eventSocket.recv( BUFFER_SIZE )

  def _SendSetpoints( self, dataSocket, deviceIndex, mask, setpoints ):
    if self.isConnected:
      struct.pack_into( 'BBB', self.setpointBuffer, 0, 1, deviceIndex, mask )
      for setpointIndex in range( len(setpoints) ):
        setpointOffset = 3 + setpointIndex * FLOAT_SIZE
        struct.pack_into( 'f', self.setpointBuffer, setpointOffset, setpoints[ setpointIndex ] )
      #print( '_SendSetpoints: sending message buffer: ' + str( list( self.setpointBuffer ) ) )
      try:
        dataSocket.sendall( self.setpointBuffer )
      except:
        print( sys.exc_info() )

  def SendAxisSetpoints( self, axisIndex, mask, setpoints ):
    self._SendSetpoints( self.axisSocket, axisIndex, mask, setpoints )

  def _ReceiveMeasures( self, dataSocket, deviceIndex, measures ):
    if self.isConnected:
      try:
        messageBuffer = dataSocket.recv( BUFFER_SIZE )
        devicesNumber = ord( messageBuffer[ 0 ] )
        #print( '_ReceiveMeasures: received message buffer: ' + str( list( messageBuffer ) ) )
        for deviceCount in range( devicesNumber ):
          dataOffset = deviceCount * len(measures) * FLOAT_SIZE + 1
          if ord( messageBuffer[ dataOffset ] ) == deviceIndex:
            for measureIndex in range( len(measures) ):
              measureOffset = dataOffset + measureIndex * FLOAT_SIZE
              measures[ measureIndex ] = struct.unpack_from( 'f', messageBuffer, measureOffset )[ 0 ]
          return True
      except:
        print( sys.exc_info() )
    return False

  def ReceiveAxisMeasures( self, axisIndex, measures ):
    return self._ReceiveMeasures( self.axisSocket, axisIndex, measures )

  def ReceiveJointMeasures( self, jointIndex, measures ):
    return self._ReceiveMeasures( self.jointSocket, jointIndex, measures )
