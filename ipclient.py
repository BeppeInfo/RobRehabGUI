#-*-coding:cp1252-*-

from socket import *

import sys
import json
import struct

from definitions import *

DEFAULT_ADDRESS = '127.0.0.1'

class Connection:
  
  host = DEFAULT_ADDRESS
  
  def __init__( self ):
    self.eventSocket = socket( AF_INET, SOCK_STREAM )
    self.dataSocket = socket( AF_INET, SOCK_DGRAM )

    self.dataSocket.settimeout( 0.01 )

    self.isConnected = False

  def __del__( self ):
    if self.isConnected:
      self.eventSocket.close()
      self.dataSocket.close()

  def Connect( self, host ):
    self.host = host
    try:
      self.eventSocket.connect( ( self.host, 50000 ) )
      self.eventSocket.setblocking( 0 )
      self.isConnected = True
      print( 'client connected' )
    except:
      print( sys.exc_info() )
      self.isConnected = False

  def RefreshInfo( self ):
    robotsInfo = {}
    if self.isConnected:
      messageBuffer = bytearray( [ 0 ] )
      try:
        self.eventSocket.send( messageBuffer )
        robotsInfoString = self.eventSocket.recv( BUFFER_SIZE )
        robotsInfo = json.loads( robotsInfoString.decode() )
      except:
        print( sys.exc_info() )
        robotsInfo = {}

    robotsInfo = json.loads( '{"robots":["robot_0"],"joints":["joint_0","joint_1"],"axes":["axis_0","axis_1"]}' )
    robotsList = robotsInfo.get( 'robots', [] )
    jointsList = robotsInfo.get( 'joints', [] )
    axesList = robotsInfo.get( 'axes', [] )

    return ( robotsList, jointsList, axesList )

  def SendCommand( self, robotIndex, commandKey ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, robotIndex, commandKey ] )
      print( 'SendCommand: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.send( messageBuffer )
      except:
        print( sys.exc_info() )
        
  def SetUser( self, userName ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, 0, SET_USER ] ) + userName.encode()
      print( 'SetUser: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.eventSocket.send( messageBuffer )
      except:
        print( sys.exc_info() )

  def CheckState( self, eventNumber ):
    return false
    #return self.eventSocket.recv( BUFFER_SIZE )

  def _SendSetpoints( self, port, deviceIndex, mask, setpoints ):
    if self.isConnected:
      messageBuffer = bytearray( [ 1, deviceIndex, mask ] )
      for setpoint in setpoints:
        messageBuffer += struct.pack( 'f', setpoint )
      print( '_SendSetpoints: sending message buffer: ' + str(list(messageBuffer)) )
      try:
        self.dataSocket.sendto( messageBuffer, ( self.host, port ) )
      except:
        print( sys.exc_info() )

  def SendAxisSetpoints( self, axisIndex, mask, setpoints ):
    self._SendSetpoints( 50001, axisIndex, mask, setpoints )

  def SendJointSetpoints( self, jointIndex, mask, setpoints ):
    self._SendSetpoints( 50002, jointIndex, mask, setpoints )

  def _ReceiveMeasures( self, port, deviceIndex, varsNumber ):
    measures = [ 0.0 for varIndex in range( varsNumber ) ]
    if self.isConnected:
      try:
        messageBuffer, remoteAddress = self.dataSocket.recvfrom( BUFFER_SIZE, MSG_PEEK )
        if remoteAddress[ 1 ] == port:
          self.dataSocket.recvfrom( BUFFER_SIZE )
          devicesNumber = messageBuffer[ 0 ]
          for deviceCount in range( devicesNumber ):
            dataOffset = deviceCount * varsNumber * FLOAT_SIZE + 1
            if messageBuffer[ dataOffset ] == deviceIndex:
              for measureIndex in range( varsNumber ):
                measureOffset = dataOffset + measureIndex * FLOAT_SIZE
                measures[ measureIndex ] = struct.unpack_from( 'f', messageBuffer, measureOffset )[ 0 ]
      except:
        print( sys.exc_info() )

    return measures

  def ReceiveAxisMeasures( self, axisIndex ):
    self._ReceiveMeasures( 50001, axisIndex, AXIS_VARS_NUMBER )

  def ReceiveJointMeasures( self, jointIndex ):
    self._ReceiveMeasures( 50002, jointIndex, JOINT_VARS_NUMBER )
