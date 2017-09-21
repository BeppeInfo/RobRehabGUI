import kivy
kivy.require( '1.9.1' )

# add the following 2 lines to solve OpenGL 2.0 bug
from kivy import Config
Config.set( 'graphics', 'multisamples', '0' )

from kivy.garden.graph import Graph, SmoothLinePlot

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.clock import Clock

from kivy.storage.jsonstore import JsonStore

import math

from definitions import *
import ipclient

from kivy.uix.label import Label
from kivy.properties import ListProperty
class LED( Label ):
  color = ListProperty( [ 1, 0, 0, 1 ] )


class RobRehabGUI( Widget ):
  connection = None
  currentServerAddress = None

  UPDATE_INTERVAL = 0.02

  robotEnabled = False
  setpointsUpdated = True
  isCalibrating = False
  isSampling = False
  samplingEvent = None

  JOINT = 0
  AXIS = 1
  deviceIDs = ( [], [] )
  currentDeviceIndexes = [ None for i in range( len(deviceIDs) ) ]
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

    self.deviceSelectors = ( self.ids[ 'joint_selector' ], self.ids[ 'axis_selector' ] )
    self.deviceEntries = [ DropDown() for selector in self.deviceSelectors ]
    for index in range( len(self.deviceEntries) ):
      def SelectEntry( instance, name, index=index ):
        self.SetDevice( index, name )
      self.deviceEntries[ index ].bind( on_select=SelectEntry )
      self.deviceSelectors[ index ].bind( on_release=self.deviceEntries[ index ].open )

    dataGraph = self.ids[ 'data_graph' ]

    axisPositionGraph = Graph( xlabel='Last Samples', ylabel='Position', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25, y_grid_label=True,
                               x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=0, xmax=len(self.INITIAL_VALUES) - 1, ymin=-1.5, ymax=1.5 )
    axisPositionPlot = SmoothLinePlot( color=[ 1, 1, 0, 1 ] )
    axisPositionGraph.add_plot( axisPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisPositionPlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_POSITION ) )
    axisVelocityPlot = SmoothLinePlot( color=[ 0, 1, 0, 1 ] )
    axisPositionGraph.add_plot( axisVelocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisVelocityPlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_VELOCITY ) )
    refPositionPlot = SmoothLinePlot( color=[ 0.5, 0.5, 0, 1 ] )
    axisPositionGraph.add_plot( refPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refPositionPlot, self.INITIAL_VALUES[:], self.setpoints, DOF_POSITION ) )
    refVelocityPlot = SmoothLinePlot( color=[ 0, 0.5, 0, 1 ] )
    axisPositionGraph.add_plot( refVelocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refVelocityPlot, self.INITIAL_VALUES[:], self.setpoints, DOF_VELOCITY ) )
    dataGraph.add_widget( axisPositionGraph )

    axisForceGraph = Graph( xlabel='Last Samples', ylabel='Torque', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25, y_grid_label=True,
                            x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=0, xmax=len(self.INITIAL_VALUES) - 1, ymin=-1.5, ymax=1.5 )
    axisForcePlot = SmoothLinePlot( color=[ 1, 0, 0, 1 ] )
    axisForceGraph.add_plot( axisForcePlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisForcePlot, self.INITIAL_VALUES[:], self.axisMeasures, DOF_FORCE ) )
    dataGraph.add_widget( axisForceGraph )

    Clock.schedule_interval( self.NetworkUpdate, self.UPDATE_INTERVAL )
    Clock.schedule_interval( self.GraphUpdate, self.UPDATE_INTERVAL )

  def ConnectClient( self, serverAddress ):
    self.connection = None
    self.robotID = ''
    self.deviceIDs = ( [], [] )
    serverType, serverHost = serverAddress.split( '://' )
    print( 'acquired %s server host: %s' % ( serverType, serverHost ) )
    if serverType == 'ip': self.connection = ipclient.Connection()
    if self.connection is not None:
      self.configStorage.put( 'server', address=serverAddress )
      self.connection.Connect( serverHost )
      self.robotID, self.deviceIDs = self.connection.RefreshInfo()

    self.ids[ 'robot_id_display' ].text = self.robotID

    def UpdateSelectorEntries( selector, entriesList, entryNames ):
      entriesList.clear_widgets()
      for name in entryNames:
        entryButton = Button( text=name, size_hint_y=None )
        entryButton.height = entryButton.font_size * 2
        entryButton.bind( on_release=lambda button: entriesList.select( button.text ) )
        entriesList.add_widget( entryButton )

    for deviceType in range( len(self.deviceIDs) ):
      UpdateSelectorEntries( self.deviceSelectors[ deviceType ], self.deviceEntries[ deviceType ], self.deviceIDs[ deviceType ] )
      self.SetDevice( deviceType, self.deviceIDs[ deviceType ][ 0 ] if len(self.deviceIDs[ deviceType ]) > 0 else self.NULL_ID )

  def GraphUpdate( self, dt ):
    for plot in self.dataPlots:
      if len(plot.values) >= len(self.INITIAL_VALUES):
        plot.handle.points = [ ( sample, plot.values[ sample ] ) for sample in range( len(self.INITIAL_VALUES) ) ]
        plot.values = []
      plot.values.append( plot.source[ plot.offset ] )
    self.ids[ 'measure_slider' ].value = self.axisMeasures[ DOF_POSITION ] * 180 / math.pi

  def NetworkUpdate( self, dt ):
    currentAxisIndex = self.currentDeviceIndexes[ self.AXIS ]
    currentJointIndex = self.currentDeviceIndexes[ self.JOINT ]
    if self.connection is not None and currentAxisIndex is not None:
      if self.setpointsUpdated:
        self.connection.SendAxisSetpoints( currentAxisIndex, self.setpoints )
        self.setpointsUpdated = False
      self.connection.ReceiveAxisMeasures( currentAxisIndex, self.axisMeasures )
      #print( 'NetworkUpdate: received axis measures: ' + str( self.axisMeasures ) )
      #self.connection.ReceiveJointMeasures( currentJointIndex, self.jointMeasures )

  def SetUserName( self, name ):
    if self.connection is not None: self.connection.SetUser( name )
    self.configStorage.put( 'user', name=name )

  def SetDevice( self, type, name ):
    self.deviceSelectors[ type ].text = name
    deviceIDs = self.deviceIDs[ type ]
    self.currentDeviceIndexes[ type ] = deviceIDs.index( name ) if ( name in deviceIDs ) else None

  def SetSetpoints( self ):
    if not self.isSampling:
      self.setpoints[ DOF_POSITION ] = self.ids[ 'setpoint_slider' ].value * math.pi / 180
      self.setpoints[ DOF_STIFFNESS ] = self.ids[ 'stiffness_slider' ].value
    self.setpointsUpdated = True

  def _SendCommand( self, commandKey ):
    self.connection.SendCommand( commandKey )

  def SetEnable( self, enabled ):
    self.robotEnabled = enabled
    offsetToggle = self.ids[ 'offset_button' ]
    if enabled:
      self._SendCommand( ENABLE )
      offsetToggle.state = 'down'
    else:
      self._SendCommand( DISABLE )
      offsetToggle.state = 'normal'

  def SetOffset( self, enabled ):
    if enabled: self._SendCommand( OFFSET )
    else: self._SendCommand( OPERATE if self.robotEnabled else PASSIVATE )

  def SetCalibration( self, enabled ):
    self.isCalibrating = enabled
    calibrationLED = self.ids[ 'indication_led' ]

    def TurnLedOn( *args ):
      calibrationLED.color = [ 0, 1, 0, 1 ]
      Clock.schedule_once( TurnLedOff, 5.0 )
    def TurnLedOff( *args ):
      calibrationLED.color = [ 1, 0, 0, 1 ]
      if self.isCalibrating: Clock.schedule_once( TurnLedOn, 3.0 )

    if enabled:
      self._SendCommand( CALIBRATE )
      TurnLedOn()
    else:
      self._SendCommand( OPERATE if self.robotEnabled else PASSIVATE )
      TurnLedOff()

  def SetOptimization( self, enabled ):
    PHASE_CYCLES_NUMBER = 5
    CYCLE_INTERVAL = 8.0
    SETPOINT_AMPLITUDE = math.pi / 4
    SETPOINT_AMPLITUDE_ANGLE = SETPOINT_AMPLITUDE * 180 / math.pi
    PHASE_INTERVAL = PHASE_CYCLES_NUMBER * CYCLE_INTERVAL
    PHASES_STIFFNESS_LIST = [     0,    30,    60,   60,   30,    0,    0,   10,   20 ]
    PHASES_DIRECTION_LIST = [     1,     1,     1,    1,    1,    1,   -1,   -1,   -1 ]
    PHASES_ACTIVE_LIST =    [ False, False, False, True, True, True, True, True, True ]
    TOTAL_SAMPLING_INTERVAL = len(PHASES_STIFFNESS_LIST) * PHASE_INTERVAL

    self.isSampling = enabled
    self.samplingTime = 0.0

    setpointSlider = self.ids[ 'setpoint_slider' ]
    stiffnessSlider = self.ids[ 'stiffness_slider' ]
    activeLED = self.ids[ 'indication_led' ]
    def UpdateSetpoint( delta ):
      setpointPhase = int( self.samplingTime / PHASE_INTERVAL )
      if setpointPhase >= len(PHASES_STIFFNESS_LIST):
        self.ids[ 'sampling_button' ].state = 'normal'
        return False
      self.samplingTime += delta
      setpointDirection = PHASES_DIRECTION_LIST[ setpointPhase ]
      activeLED.color = [ 0, 1, 0, 1 ] if PHASES_ACTIVE_LIST[ setpointPhase ] else [ 1, 0, 0, 1 ]
      setpoint = math.sin( 2 * math.pi * self.samplingTime / CYCLE_INTERVAL )
      setpointSlider.value = setpoint * SETPOINT_AMPLITUDE_ANGLE - SETPOINT_AMPLITUDE_ANGLE
      self.setpoints[ DOF_POSITION ] = setpoint * SETPOINT_AMPLITUDE * setpointDirection - SETPOINT_AMPLITUDE
      targetStiffness = PHASES_STIFFNESS_LIST[ setpointPhase ]
      stiffnessSlider.value = stiffnessSlider.value * 0.9 + targetStiffness * 0.1
      self.setpoints[ DOF_STIFFNESS ] = stiffnessSlider.value

    if enabled:
      self._SendCommand( OPTIMIZE )
      self.samplingEvent = Clock.schedule_interval( UpdateSetpoint, self.UPDATE_INTERVAL )
    else:
      self.samplingTime = TOTAL_SAMPLING_INTERVAL
      setpointSlider.value = 0.0
      stiffnessSlider.value = 0.0
      activeLED.color = [ 1, 0, 0, 1 ]
      self._SendCommand( OPERATE if self.robotEnabled else PASSIVATE )
      self.samplingEvent.cancel()

class RobRehabApp( App ):
  def build( self ):
    self.title = 'RobRehab GUI'
    self.icon = 'rerob_icon.png'
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
