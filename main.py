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

  ROBOT = 0
  JOINT = 1
  AXIS = 2
  deviceIDs = ( [], [], [] )
  currentDeviceIndexes = [ None for i in range( len(deviceIDs) ) ]
  NULL_ID = '<Select>'

  axisMeasures = [ 0.0 for var in range( AXIS_VARS_NUMBER ) ]
  setpoints = [ 0.0 for var in range( AXIS_VARS_NUMBER ) ]
  jointMeasures = [ 0.0 for var in range( JOINT_VARS_NUMBER ) ]

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
    # or Widget.__init__( **kwargs ) ?

    self.configStorage = JsonStore( 'config.json' )
    if self.configStorage.exists( 'server' ): self.ids[ 'address_input' ].text = self.configStorage.get( 'server' )[ 'address' ]
    if self.configStorage.exists( 'user' ): self.ids[ 'user_name_input' ].text = self.configStorage.get( 'user' )[ 'name' ]

    self.deviceSelectors = ( self.ids[ 'robot_selector' ], self.ids[ 'joint_selector' ], self.ids[ 'axis_selector' ] )
    self.deviceEntries = [ DropDown() for selector in self.deviceSelectors ]
    for index in range( len(self.deviceEntries) ):
      def SelectEntry( instance, name, index=index ):
        self.SetDevice( index, name )
      self.deviceEntries[ index ].bind( on_select=SelectEntry )
      self.deviceSelectors[ index ].bind( on_release=self.deviceEntries[ index ].open )

    dataGraph = self.ids[ 'data_graph' ]

    axisGraph = Graph( xlabel='Last Samples', ylabel='Axis', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25, y_grid_label=True,
                       x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=0, xmax=len(self.INITIAL_VALUES) - 1, ymin=-1.5, ymax=1.5 )
    axisPositionPlot = SmoothLinePlot( color=[ 1, 1, 0, 1 ] )
    axisGraph.add_plot( axisPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisPositionPlot, self.INITIAL_VALUES[:], self.axisMeasures, AXIS_POSITION ) )
    axisVelocityPlot = SmoothLinePlot( color=[ 0, 1, 0, 1 ] )
    axisGraph.add_plot( axisVelocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( axisVelocityPlot, self.INITIAL_VALUES[:], self.axisMeasures, AXIS_VELOCITY ) )
    refPositionPlot = SmoothLinePlot( color=[ 0.5, 0.5, 0, 1 ] )
    axisGraph.add_plot( refPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refPositionPlot, self.INITIAL_VALUES[:], self.setpoints, AXIS_POSITION ) )
    refVelocityPlot = SmoothLinePlot( color=[ 0, 0.5, 0, 1 ] )
    axisGraph.add_plot( refVelocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refVelocityPlot, self.INITIAL_VALUES[:], self.setpoints, AXIS_VELOCITY ) )
    dataGraph.add_widget( axisGraph )

    jointGraph = Graph( xlabel='Last Samples', ylabel='Joint', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25, y_grid_label=True,
                        x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=0, xmax=len(self.INITIAL_VALUES) - 1, ymin=-1.5, ymax=1.5 )
    jointForcePlot = SmoothLinePlot( color=[ 1, 0, 0, 1 ] )
    axisGraph.add_plot( jointForcePlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( jointForcePlot, self.INITIAL_VALUES[:], self.jointMeasures, JOINT_FORCE ) )
    dataGraph.add_widget( jointGraph )

    Clock.schedule_interval( self.GraphUpdate, self.UPDATE_INTERVAL )
    Clock.schedule_interval( self.NetworkUpdate, self.UPDATE_INTERVAL )

  def ConnectClient( self, serverAddress ):
    self.deviceIDs = ( [], [], [] )
    serverType, serverHost = serverAddress.split( '://' )
    if serverAddress != self.currentServerAddress:
      if serverType == 'ip': self.connection = ipclient.Connection()
      else: self.connection = None
      if self.connection is not None:
        self.configStorage.put( 'server', address=serverAddress )
        print( 'connecting to host: ' + serverHost )
        self.connection.Connect( serverHost )
        self.currentServerAddress = serverAddress
    if self.connection is not None: self.deviceIDs = self.connection.RefreshInfo()

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
    self.ids[ 'measure_slider' ].value = self.axisMeasures[ AXIS_POSITION ]

  def NetworkUpdate( self, dt ):
    SETPOINTS_MASK = int( '00010011', base=2 )
    currentAxisIndex = self.currentDeviceIndexes[ self.AXIS ]
    currentJointIndex = self.currentDeviceIndexes[ self.JOINT ]
    if self.connection is not None and currentAxisIndex is not None:
      self.connection.SendAxisSetpoints( currentAxisIndex, SETPOINTS_MASK, self.setpoints )
      self.connection.ReceiveAxisMeasures( currentAxisIndex, self.axisMeasures )
      #print( 'Axis ' + str(currentAxisIndex) + ' measures: ' + str(self.axisMeasures) )
      self.connection.ReceiveJointMeasures( currentJointIndex, self.jointMeasures )

  def SetUserName( self, name ):
    if self.connection is not None: self.connection.SetUser( name )
    self.configStorage.put( 'user', name=name )

  def SetDevice( self, type, name ):
    self.deviceSelectors[ type ].text = name
    deviceIDs = self.deviceIDs[ type ]
    self.currentDeviceIndexes[ type ] = deviceIDs.index( name ) if ( name in deviceIDs ) else None

  def SetSetpoints( self ):
    self.setpoints[ AXIS_POSITION ] = self.ids[ 'setpoint_slider' ].value * math.pi / 180
    self.setpoints[ AXIS_STIFFNESS ] = self.ids[ 'stiffness_slider' ].value

  def _SendCommand( self, commandKey ):
    currentRobotIndex = self.currentDeviceIndexes[ self.ROBOT ]
    if self.connection is not None and currentRobotIndex is not None:
      self.connection.SendCommand( currentRobotIndex, commandKey )

  def SetEnable( self, enabled ):
    if enabled: self._SendCommand( ENABLE )
    else: self._SendCommand( DISABLE )

  def SetOffset( self, enabled ):
    if enabled: self._SendCommand( OFFSET )
    else: self._SendCommand( OPERATE )

  def SetCalibration( self, enabled ):
    self.isCalibrating = enabled
    calibrationLed = self.ids[ 'calibration_led' ]

    def TurnLedOn( *args ):
      calibrationLed.color = [ 0, 1, 0, 1 ]
      Clock.schedule_once( TurnLedOff, 5.0 )
    def TurnLedOff( *args ):
      calibrationLed.color = [ 1, 0, 0, 1 ]
      if self.isCalibrating: Clock.schedule_once( TurnLedOn, 3.0 )

    if enabled:
      self._SendCommand( CALIBRATE )
      TurnLedOn()
    else:
      self._SendCommand( OPERATE )
      TurnLedOff()

  def SetOptimization( self, enabled ):
    PHASE_CYCLES_NUMBER = 5
    CYCLE_INTERVAL = 2.0
    PHASE_INTERVAL = PHASE_CYCLES_NUMBER * CYCLE_INTERVAL
    PHASES_STIFFNESS_LIST = [ 0, 30, 60, 90, 90, 60, 30, 0 ]
    TOTAL_SAMPLING_INTERVAL = len(PHASES_STIFFNESS_LIST) * PHASE_INTERVAL

    self.isSampling = enabled
    self.samplingTime = 0.0

    setpointSlider = self.ids[ 'setpoint_slider' ]
    stiffnessSlider = self.ids[ 'stiffness_slider' ]
    def UpdateSetpoint( delta ):
      if self.samplingTime >= TOTAL_SAMPLING_INTERVAL:
        self.ids[ 'sampling_button' ].state = 'normal'
        return False
      self.samplingTime += delta
      setpointPhase = int( self.samplingTime / PHASE_INTERVAL )
      setpointDirection = 1.0 if setpointPhase < len(PHASES_STIFFNESS_LIST) / 2 else -1.0
      setpointSlider.value = math.sin( 2 * math.pi * self.samplingTime / CYCLE_INTERVAL ) * 0.1 * math.pi * 180
      self.setpoints[ AXIS_POSITION ] *= setpointDirection
      targetStiffness = PHASES_STIFFNESS_LIST[ setpointPhase ] if setpointPhase < len(PHASES_STIFFNESS_LIST) else 0.0
      stiffnessSlider.value = stiffnessSlider.value * 0.95 + targetStiffness * 0.05

    if enabled:
      self._SendCommand( OPTIMIZE )
      Clock.schedule_interval( UpdateSetpoint, self.UPDATE_INTERVAL )
    else:
      self.samplingTime = TOTAL_SAMPLING_INTERVAL
      setpointSlider.value = 0.0
      stiffnessSlider.value = 0.0
      self._SendCommand( OPERATE )

class RobRehabApp( App ):
  def build( self ):
    self.title = 'RobRehab GUI'
    self.icon = 'rerob_icon.png'
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
