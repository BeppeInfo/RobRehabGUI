#-*-coding:cp1252-*-

from socket import *

import sys
import json
import struct

from definitions import *

DEFAULT_ADDRESS = 'localhost'

class Connection:

  def __init__( self ):
    self.eventSocket = socket( AF_INET, SOCK_STREAM )
    self.axisSocket = socket( AF_INET, SOCK_DGRAM )
    self.jointSocket = socket( AF_INET, SOCK_DGRAM )

    self.eventSocket.setblocking( 0 )
    self.axisSocket.setblocking( 0 )
    self.jointSocket.setblocking( 0 )

    self.isConnected = False

  def __del__( self ):
    if self.isConnected:
      self.eventSocket.close()
      self.axisSocket.close()
      self.jointSocket.close()

  def Connect( self, host ):
    try:
      self.eventSocket.connect( ( host, 50000 ) )
      self.axisSocket.connect( ( host, 50001 ) )
      self.jointSocket.connect( ( host, 50002 ) )
      self.isConnected = True
      print( 'client connected' )
    except:
      print( sys.exc_info()[ 0 ] )
      self.isConnected = False

  def RefreshInfo( self ):
    robotsInfo = {}
    if self.isConnected:
      messageBuffer = bytearray( 1 )
      messageBuffer[ 0 ] = 0
      self.eventSocket.send( messageBuffer )
      try:
        robotsInfoString = self.eventSocket.recv( BUFFER_SIZE )
        robotsInfo = json.loads( robotsInfoString.decode() )
      except:
        exception = sys.exc_info()[ 0 ]
        print( exception )
        robotsInfo = {}

    robotsInfo = json.loads( '{"robots":["robot_0"],"joints":["joint_0","joint_1"],"axes":["axis_0","axis_1"]}' )
    robotsList = robotsInfo.get( 'robots', [] )
    jointsList = robotsInfo.get( 'joints', [] )
    axesList = robotsInfo.get( 'axes', [] )

    return ( robotsList, jointsList, axesList )

  def SendCommand( self, robotIndex, commandKey ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, robotIndex, commandKey ] )
      try:
        self.eventSocket.send( messageBuffer )
      except:
        print( sys.exc_info()[ 0 ] )

  def CheckState( self, eventNumber ):
    return false
    #return self.eventSocket.recv( BUFFER_SIZE )

  def _SendSetpoints( self, dataSocket, deviceIndex, mask, setpoints ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, deviceIndex, mask ] )
      for setpoint in setpoints:
        messageBuffer += struct.pack( 'f', setpoint )
      try:
        dataSocket.send( messageBuffer )
      except:
        print( sys.exc_info()[ 0 ] )

  def SendAxisSetpoints( self, axisIndex, mask, setpoints ):
    self._SendSetpoints( self.axisSocket, axisIndex, mask, setpoints )

  def SendJointSetpoints( self, jointIndex, mask, setpoints ):
    self._SendSetpoints( self.jointSocket, jointIndex, mask, setpoints )

  def _ReceiveMeasures( self, dataSocket, deviceIndex, varsNumber ):
    measures = [ 0.0 for varIndex in range( varsNumber ) ]
    if self.isConnected:
      try:
        messageBuffer = dataSocket.recv( BUFFER_SIZE )
        devicesNumber = messageBuffer[ 0 ]
        for deviceCount in range( devicesNumber ):
          dataOffset = deviceCount * varsNumber * FLOAT_SIZE + 1
          if messageBuffer[ dataOffset ] == deviceIndex:
            for measureIndex in range( varsNumber ):
              measureOffset = dataOffset + measureIndex * FLOAT_SIZE
              measures[ measureIndex ] = struct.unpack_from( 'f', messageBuffer, measureOffset )[ 0 ]
      except:
        print( sys.exc_info()[ 0 ] )

    return measures

  def ReceiveAxisMeasures( self, axisIndex ):
    self._ReceiveMeasures( self.axisSocket, axisIndex, AXIS_VARS_NUMBER )

  def ReceiveJointMeasures( self, jointIndex ):
    self._ReceiveMeasures( self.jointSocket, jointIndex, JOINT_VARS_NUMBER )
