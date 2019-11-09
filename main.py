import kivy
kivy.require( '1.9.1' )

# add the following 2 lines to solve OpenGL 2.0 bug
#from kivy import Config
#Config.set( 'graphics', 'multisamples', '0' )

from kivy.garden.graph import Graph, SmoothLinePlot

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.clock import Clock

from kivy.storage.jsonstore import JsonStore

import math
import json

from definitions import *
import ipclient

from kivy.uix.label import Label
from kivy.properties import ListProperty
class LED( Label ):
  color = ListProperty( [ 1, 0, 0, 1 ] )


class RobRehabGUI( Widget ):
  connection = None
  currentServerAddress = None

  UPDATE_INTERVAL = 2 * MESSAGE_TIMEOUT

  setpointsUpdated = True

  isCalibrating = False
  isSampling = False
  isOperating = False
  samplingEvent = None
  operationEvent = None

  robotIDs = []
  axisIDs = []
  currentAxisIndex = None
  NULL_ID = '<Select>'

  axisMeasures = [ 0.0 for var in range( DOF_VARS_NUMBER ) ]
  setpoints = [ 0.0 for var in range( DOF_VARS_NUMBER ) ]
  jointMeasures = [ 0.0 for var in range( DOF_VARS_NUMBER ) ]

  class DataPlot:
    def __init__( self, handle, values, source, offset ):
      self.handle = handle
      self.values = values
      self.source = source
      self.offset = offset
  dataPlots = []
  INITIAL_VALUES = [ 0.0 for value in range( 101 ) ]

  def __init__( self, **kwargs ):
    super( RobRehabGUI, self ).__init__( **kwargs )

    self.configStorage = JsonStore( 'config.json' )
    if self.configStorage.exists( 'server' ): self.ids[ 'address_input' ].text = self.configStorage.get( 'server' )[ 'address' ]
    if self.configStorage.exists( 'user' ): self.ids[ 'user_name_input' ].text = self.configStorage.get( 'user' )[ 'name' ]

    self.robotSelector = self.ids[ 'robot_selector' ]
    self.robotEntries = DropDown()
    self.robotEntries.bind( on_select=lambda instance, name: self.SetRobot( name ) )
    self.robotSelector.bind( on_release=self.robotEntries.open )
    self.axisSelector = self.ids[ 'axis_selector' ]
    self.axisEntries = DropDown()
    self.axisEntries.bind( on_select=lambda instance, name: self.SetAxis( name ) )
    self.axisSelector.bind( on_release=self.axisEntries.open )
    
    self.enableToggle = self.ids[ 'enable_button' ]
    self.offsetToggle = self.ids[ 'offset_button' ]
    self.calibrationToggle = self.ids[ 'calibration_button' ]
    self.samplingToggle = self.ids[ 'sampling_button' ]
    self.operationToggle = self.ids[ 'operation_button' ]
    
    self.measureSlider = self.ids[ 'measure_slider' ]
    self.setpointSlider = self.ids[ 'setpoint_slider' ]
    self.stiffnessSlider = self.ids[ 'stiffness_slider' ]
    self.dampingSlider = self.ids[ 'damping_slider' ]
    
    self.indicationLED = self.ids[ 'indication_led' ]
    
    dataGraph = self.ids[ 'data_graph' ]

    measure_range = self.measureSlider.range
    GRAPH_PROPERTIES = { 'xlabel':'Last Samples', 'x_ticks_minor':5, 'x_ticks_major':25, 'y_ticks_minor':0.25, 'y_ticks_major':0.5, 'y_grid_label':True, 'x_grid_label':True,
                         'padding':5, 'x_grid':True, 'y_grid':True, 'xmin':0, 'xmax':len(self.INITIAL_VALUES) - 1, 'ymin':measure_range[ 0 ], 'ymax':measure_range[ 1 ],
                         'background_color':[ 1, 1, 1, 1 ], 'tick_color':[ 0, 0, 0, 1 ], 'border_color':[ 0, 0, 0, 1 ], 'label_options':{ 'color': [ 0, 0, 0, 1 ], 'bold':True } }

    axisPositionGraph = Graph( ylabel='Position', **GRAPH_PROPERTIES )
    axisPositionPlot = SmoothLinePlot( color=[ 0, 0, 1, 1 ] )
    axisPositionGraph.add_plot( axisPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisPositionPlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_POSITION ) )
    axisVelocityPlot = SmoothLinePlot( color=[ 0, 1, 0, 1 ] )
    axisPositionGraph.add_plot( axisVelocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisVelocityPlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_VELOCITY ) )
    refPositionPlot = SmoothLinePlot( color=[ 0, 0, 0.5, 1 ] )
    axisPositionGraph.add_plot( refPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refPositionPlot, self.INITIAL_VALUES[:], self.setpoints, DOF_POSITION ) )
    refVelocityPlot = SmoothLinePlot( color=[ 0, 0.5, 0, 1 ] )
    axisPositionGraph.add_plot( refVelocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refVelocityPlot, self.INITIAL_VALUES[:], self.setpoints, DOF_VELOCITY ) )
    axisAccelerationPlot = SmoothLinePlot( color=[ 1, 0, 0, 1 ] )
    axisPositionGraph.add_plot( axisAccelerationPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisAccelerationPlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_ACCELERATION ) )
    dataGraph.add_widget( axisPositionGraph )

    dataGraph.add_widget( Label( size_hint_y=0.05 ) )

    axisForceGraph = Graph( ylabel='Torque', **GRAPH_PROPERTIES )
    axisForcePlot = SmoothLinePlot( color=[ 1, 0, 0, 1 ] )
    axisForceGraph.add_plot( axisForcePlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisForcePlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_FORCE ) )
    dataGraph.add_widget( axisForceGraph )

    Clock.schedule_interval( self.DataUpdate, self.UPDATE_INTERVAL / 2 )
    Clock.schedule_interval( self.GraphUpdate, self.UPDATE_INTERVAL * 2 )
    Clock.schedule_interval( self.SliderUpdate, self.UPDATE_INTERVAL )

  def ConnectClient( self, serverAddress ):
    self.connection = None
    self.robotIDs = []
    serverType, serverHost = serverAddress.split( '://' )
    print( 'acquired %s server host: %s' % ( serverType, serverHost ) )
    if serverType == 'ip': self.connection = ipclient.Connection()
    if self.connection is not None:
      self.configStorage.put( 'server', address=serverAddress )
      self.connection.Connect( serverHost )
      replyCode, replyString = self.connection.SendRequest( LIST_CONFIGS )
      if replyCode == LIST_CONFIGS: 
        self.robotIDs = json.loads( replyString )[ 'robots' ]
        self._UpdateSelectorEntries( self.robotSelector, self.robotEntries, self.robotIDs )

  def GraphUpdate( self, dt ):
    for plot in self.dataPlots:
      if len(plot.values) >= len(self.INITIAL_VALUES):
        plot.handle.points = [ ( sample, plot.values[ sample ] ) for sample in range( len(self.INITIAL_VALUES) ) ]
        plot.values = []
      plot.values.append( plot.source[ plot.offset ] )

  def SliderUpdate( self, dt ):
    self.measureSlider.value = self.axisMeasures[ DOF_POSITION ]

  def DataUpdate( self, dt ):
    if self.connection is not None and self.currentAxisIndex is not None:
      if self.setpointsUpdated:
        self.connection.SendAxisSetpoints( self.currentAxisIndex, self.setpoints )
        self.setpointsUpdated = False
      self.connection.ReceiveAxisMeasures( self.currentAxisIndex, self.axisMeasures )
      #print( 'DataUpdate: received axis measures: ' + str( self.axisMeasures ) )
  
  def EventUpdate( self, dt ):
    if self.connection is not None:
      replyCode, replyString = self.connection.ReceiveReply()
  
  def SetUserName( self, name ):
    if self.connection is not None: self.connection.SendRequest( SET_USER, name )
    self.configStorage.put( 'user', name=name )
    
  def _UpdateSelectorEntries( self, selector, entriesList, entryNames ):
          entriesList.clear_widgets()
          for name in entryNames:
            entryButton = Button( text=name, size_hint_y=None )
            entryButton.height = entryButton.font_size * 2
            entryButton.bind( on_release=lambda button: entriesList.select( button.text ) )
            entriesList.add_widget( entryButton )
    
  def SetRobot( self, name ):
    self.enableToggle = 'normal'
    replyCode, replyString = self.connection.SendRequest( SET_CONFIG, name )
    if replyCode == SET_CONFIG: 
      replyCode, replyString = self.connection.SendRequest( GET_CONFIG )
      if replyCode == GET_CONFIG: 
        robotInfo = json.loads( replyString )
        robotID = robotInfo.get( 'id', '' )
        self.axisIDs = robotInfo.get( 'axes', [] )
        jointIDs = robotInfo.get( 'joints', [] )
        self.robotSelector.text = robotID
        self._UpdateSelectorEntries( self.axisSelector, self.axisEntries, self.axisIDs )
        self.SetAxis( self.axisIDs[ 0 ] if len(self.axisIDs) > 0 else self.NULL_ID )
    
  def SetAxis( self, name ):
    self.axisSelector.text = name
    self.currentAxisIndex = self.axisIDs.index( name ) if ( name in self.axisIDs ) else None

  def SetSetpoints( self ):
    if not self.isSampling:
      self.setpoints[ DOF_POSITION ] = self.setpointSlider.value
      self.setpoints[ DOF_STIFFNESS ] = self.stiffnessSlider.value
      self.setpoints[ DOF_DAMPING ] = self.dampingSlider.value
    self.setpointsUpdated = True

  def _SendCommand( self, commandKey ):
    self.connection.SendRequest( commandKey )

  def SetEnable( self, enabled ):
    if enabled:
      self._SendCommand( ENABLE )
      self.offsetToggle.state = 'down'
    else:
      self._SendCommand( DISABLE )
      self.offsetToggle.state = 'normal'
      self.calibrationToggle.state = 'normal'
      self.samplingToggle.state = 'normal'
      self.operationToggle.state = 'normal'

  def SetOffset( self, enabled ):
    if enabled: self._SendCommand( OFFSET )
    else:
      self._SendCommand( OPERATE if self.isOperating else PASSIVATE )
      self.setpointSlider.value = 0
      self.SetSetpoints()

  def SetCalibration( self, enabled ):
    self.isCalibrating = enabled

    def TurnLedOn( *args ):
      self.indicationLED.color = [ 0, 1, 0, 1 ]
      Clock.schedule_once( TurnLedOff, 5.0 )
    def TurnLedOff( *args ):
      self.indicationLED.color = [ 1, 0, 0, 1 ]
      if self.isCalibrating: Clock.schedule_once( TurnLedOn, 3.0 )

    if enabled:
      self._SendCommand( CALIBRATE )
      TurnLedOn()
    else:
      self._SendCommand( OPERATE if self.isOperating else PASSIVATE )
      TurnLedOff()

  def SetOptimization( self, enabled ):
    PHASE_CYCLES_NUMBER = 5
    PHASE_CYCLE_INTERVAL = 8.0
    SETPOINT_AMPLITUDE = math.pi / 4
    #SETPOINT_AMPLITUDE_ANGLE = SETPOINT_AMPLITUDE * 180 / math.pi
    PHASE_INTERVAL = PHASE_CYCLES_NUMBER * PHASE_CYCLE_INTERVAL
    PHASES_STIFFNESS_LIST = [     0,    30,    60,   60,   30,    0,    0,   10 ]
    PHASES_DIRECTION_LIST = [     1,     1,     1,    1,    1,    1,   -1,   -1 ]
    PHASES_ACTIVE_LIST =    [ False, False, False, True, True, True, True, True ]
    TOTAL_SAMPLING_INTERVAL = len(PHASES_STIFFNESS_LIST) * PHASE_INTERVAL

    self.isSampling = enabled
    self.samplingTime = 0.0

    def UpdateSetpoint( delta ):
      phaseIndex = int( self.samplingTime / PHASE_INTERVAL )
      if phaseIndex >= len(PHASES_STIFFNESS_LIST):
        self.samplingToggle.state = 'normal'
        return False
      self.samplingTime += delta
      setpointDirection = PHASES_DIRECTION_LIST[ phaseIndex ]
      self.indicationLED.color = [ 0, 1, 0, 1 ] if PHASES_ACTIVE_LIST[ phaseIndex ] else [ 1, 0, 0, 1 ]
      setpoint = math.sin( 2 * math.pi * self.samplingTime / PHASE_CYCLE_INTERVAL )
      self.setpointSlider.value = setpoint * SETPOINT_AMPLITUDE #SETPOINT_AMPLITUDE_ANGLE #- SETPOINT_AMPLITUDE_ANGLE
      self.setpoints[ DOF_POSITION ] = setpoint * SETPOINT_AMPLITUDE * setpointDirection - SETPOINT_AMPLITUDE
      targetStiffness = PHASES_STIFFNESS_LIST[ phaseIndex ]
      self.stiffnessSlider.value = self.stiffnessSlider.value * 0.9 + targetStiffness * 0.1
      self.setpoints[ DOF_STIFFNESS ] = self.stiffnessSlider.value
      self.dampingSlider.value = 0.0

    if enabled:
      self._SendCommand( PREPROCESS )
      self.samplingEvent = Clock.schedule_interval( UpdateSetpoint, self.UPDATE_INTERVAL * 2 )
    else:
      self.samplingTime = TOTAL_SAMPLING_INTERVAL
      self.setpointSlider.value = 0.0
      self.stiffnessSlider.value = 0.0
      self.dampingSlider.value = 0.0
      self.indicationLED.color = [ 1, 0, 0, 1 ]
      self._SendCommand( OPERATE if self.isOperating else PASSIVATE )
      self.samplingEvent.cancel()

  def SetOperation( self, enabled ):
    PHASE_CYCLE_INTERVAL = 8.0
    SETPOINT_AMPLITUDE = math.pi / 4
    #SETPOINT_AMPLITUDE_ANGLE = SETPOINT_AMPLITUDE * 180 / math.pi

    self.isOperating = enabled
    self.operationTime = 0.0

    import numpy
    from scipy import signal
    self.trajectory = numpy.loadtxt( 'positionknee.txt' )
    self.trajectory = numpy.reshape( self.trajectory, numpy.size( self.trajectory ) )
    self.trajectory = signal.resample( self.trajectory, int(len(self.trajectory) / 2) )
    print( self.trajectory )
    self.curveStep = 0
    self.setpoints[ DOF_STIFFNESS ] = 0
    #self.hasStarted = False

    def UpdateSetpoint( delta ):
      #cyclesCount = int( self.operationTime / PHASE_CYCLE_INTERVAL )
      #self.operationTime += delta
      #setpoint = math.sin( 2 * math.pi * self.operationTime / PHASE_CYCLE_INTERVAL )
      #if self.hasStarted:
      setpoint = - float( self.trajectory[ self.curveStep % len(self.trajectory) ] )
      self.curveStep += 1
      self.setpointSlider.value = setpoint * SETPOINT_AMPLITUDE #SETPOINT_AMPLITUDE_ANGLE #- SETPOINT_AMPLITUDE_ANGLE
      #elif self.setpoints[ DOF_STIFFNESS ] > 0:
      #  if( abs( self.setpoints[ DOF_POSITION ] - self.axisMeasures[ DOF_POSITION ] ) ) < 0.0001:
      #    self.hasStarted = True
      #self.stiffnessSlider.value = self.axisMeasures[ DOF_STIFFNESS ]
      #if cyclesCount < 20: self.setpoints[ DOF_STIFFNESS ] = 60
      #else: self.setpoints[ DOF_STIFFNESS ] = 0
      #self.setpoints[ DOF_STIFFNESS ] = 60

    if enabled:
      self._SendCommand( OPERATE )
      self.indicationLED.color = [ 0, 1, 0, 1 ]
      self.operationEvent = Clock.schedule_interval( UpdateSetpoint, self.UPDATE_INTERVAL * 2 )
    else:
      self.setpointSlider.value = 0.0
      self.stiffnessSlider.value = 0.0
      self.dampingSlider.value = 0.0
      self.indicationLED.color = [ 1, 0, 0, 1 ]
      self._SendCommand( PASSIVATE )
      self.operationEvent.cancel()

class RobRehabApp( App ):
  def build( self ):
    self.title = 'RobRehab GUI'
    self.icon = 'rerob_icon.png'
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
