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
from kivy.uix.label import Label
from kivy.clock import Clock

from kivy.storage.jsonstore import JsonStore

import math
import json
import os

from definitions import *
import ipclient


class RobRehabGUI( Widget ):
  connection = None
  currentServerAddress = None

  UPDATE_INTERVAL = 2 * MESSAGE_TIMEOUT

  setpointsUpdated = True

  isCalibrating = False
  isOperating = False
  setpointUpdateEvent = None

  robotIDs = []
  axisIDs = []
  currentAxisIndex = None
  NULL_ID = '<Select>'
  DEFAULT_MOTION = 'no_setpoint'
  MOTIONS_DIR = 'setpoint_motions'

  measures = [ 0.0 for var in range( DOF_VARS_NUMBER ) ]
  setpoints = [ 0.0 for var in range( DOF_VARS_NUMBER ) ]

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
    self.operationToggle = self.ids[ 'operation_button' ]
    
    self.measureSlider = self.ids[ 'measure_slider' ]
    self.setpointSlider = self.ids[ 'setpoint_slider' ]
    self.forceSlider = self.ids[ 'force_slider' ]
    self.inertiaSlider = self.ids[ 'inertia_slider' ]
    self.stiffnessSlider = self.ids[ 'stiffness_slider' ]
    self.dampingSlider = self.ids[ 'damping_slider' ]
    
    self.motionSelector = self.ids[ 'motion_selector' ]
    self.motionEntries = DropDown()
    self.motionEntries.bind( on_select=lambda instance, name: self.SetMotion( name ) )
    self.motionSelector.bind( on_release=self.motionEntries.open )
    setpointMotions = []
    for fileName in os.listdir( self.MOTIONS_DIR ):
      if fileName.endswith( '.txt' ):
          setpointMotions.append( os.path.splitext( fileName )[ 0 ] )
    self._UpdateSelectorEntries( self.motionSelector, self.motionEntries, setpointMotions )
    self.SetMotion( self.DEFAULT_MOTION )
    
    self.setpointUpdateEvent = None
    
    dataGraph = self.ids[ 'data_graph' ]

    measure_range = self.measureSlider.range
    GRAPH_PROPERTIES = { 'x_ticks_minor':5, 'x_ticks_major':25, 'y_ticks_minor':0.25, 'y_ticks_major':0.5, 'y_grid_label':True, 'x_grid_label':True,
                         'padding':5, 'x_grid':True, 'y_grid':True, 'xmin':0, 'xmax':len(self.INITIAL_VALUES) - 1,
                         'background_color':[ 1, 1, 1, 1 ], 'tick_color':[ 0, 0, 0, 1 ], 'border_color':[ 0, 0, 0, 1 ], 'label_options':{ 'color': [ 0, 0, 0, 1 ], 'bold':True } }

    axisPositionGraph = Graph( ylabel='Position/Setpoint', ymin=measure_range[ 0 ], ymax=measure_range[ 1 ], **GRAPH_PROPERTIES )
    positionPlot = SmoothLinePlot( color=[ 0, 0, 1, 1 ] )
    axisPositionGraph.add_plot( positionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( positionPlot, self.INITIAL_VALUES[:], self.measures, DOF_POSITION ) )
    velocityPlot = SmoothLinePlot( color=[ 0, 1, 0, 1 ] )
    axisPositionGraph.add_plot( velocityPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( velocityPlot, self.INITIAL_VALUES[:], self.measures, DOF_VELOCITY ) )
    accelerationPlot = SmoothLinePlot( color=[ 1, 1, 0, 1 ] )
    axisPositionGraph.add_plot( accelerationPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( accelerationPlot, self.INITIAL_VALUES[:], self.measures, DOF_ACCELERATION ) )
    refPositionPlot = SmoothLinePlot( color=[ 0, 0, 0.5, 1 ] )
    axisPositionGraph.add_plot( refPositionPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refPositionPlot, self.INITIAL_VALUES[:], self.setpoints, DOF_POSITION ) )
    dataGraph.add_widget( axisPositionGraph )

    dataGraph.add_widget( Label( size_hint_y=0.05 ) )
    
    force_range = self.forceSlider.range
    axisForceGraph = Graph( ylabel='Force/Impedance', ymin=force_range[ 0 ], ymax=force_range[ 1 ], **GRAPH_PROPERTIES )
    forcePlot = SmoothLinePlot( color=[ 1, 0, 0, 1 ] )
    axisForceGraph.add_plot( forcePlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( forcePlot, self.INITIAL_VALUES[:], self.measures, DOF_FORCE ) )
    dampingPlot = SmoothLinePlot( color=[ 0, 0, 1, 1 ] )
    axisForceGraph.add_plot( dampingPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( dampingPlot, self.INITIAL_VALUES[:], self.measures, DOF_DAMPING ) )
    inertiaPlot = SmoothLinePlot( color=[ 0, 1, 0, 1 ] )
    axisForceGraph.add_plot( inertiaPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( inertiaPlot, self.INITIAL_VALUES[:], self.measures, DOF_INERTIA ) )
    stiffnessPlot = SmoothLinePlot( color=[ 1, 1, 0, 1 ] )
    axisForceGraph.add_plot( stiffnessPlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( stiffnessPlot, self.INITIAL_VALUES[:], self.measures, DOF_STIFFNESS ) )
    refForcePlot = SmoothLinePlot( color=[ 0.5, 0, 0, 1 ] )
    axisForceGraph.add_plot( refForcePlot )
    self.dataPlots.append( RobRehabGUI.DataPlot( refForcePlot, self.INITIAL_VALUES[:], self.setpoints, DOF_FORCE ) )
    dataGraph.add_widget( axisForceGraph )

    dataGraph.add_widget( Label( text='Last Samples', size_hint_y=0.1 ) )

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
    self.measureSlider.value = self.measures[ DOF_POSITION ]
    if self.isCalibrating:
      self.inertiaSlider.value = self.measures[ DOF_INERTIA ]
      self.stiffnessSlider.value = self.measures[ DOF_STIFFNESS ]
      self.dampingSlider.value = self.measures[ DOF_DAMPING ]

  def DataUpdate( self, dt ):
    if self.connection is not None and self.currentAxisIndex is not None:
      if self.setpointsUpdated:
        self.connection.SendAxisSetpoints( self.currentAxisIndex, self.setpoints )
        self.setpointsUpdated = False
      self.connection.ReceiveAxisMeasures( self.currentAxisIndex, self.measures )
      #print( 'DataUpdate: received axis measures: ' + str( self.measures ) )
  
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
    self.setpoints[ DOF_POSITION ] = self.setpointSlider.value
    self.setpoints[ DOF_FORCE ] = self.forceSlider.value
    if not self.isCalibrating:
      self.setpoints[ DOF_INERTIA ] = self.inertiaSlider.value
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
      self.operationToggle.state = 'normal'

  def SetOffset( self, enabled ):
    if enabled: self._SendCommand( OFFSET )
    else:
      self._SendCommand( OPERATE if self.isOperating else PASSIVATE )
      self.setpointSlider.value = 0
      self.SetSetpoints()

  def SetMotion( self, fileName ):
    import numpy
    #from scipy import signal
    if fileName == self.DEFAULT_MOTION: self.setpointMotion = None
    else:
      try: 
        self.setpointMotion = numpy.loadtxt( self.MOTIONS_DIR + '/' + fileName + '.txt' )
        self.setpointMotion = numpy.reshape( self.setpointMotion, numpy.size( self.setpointMotion ) )
        #self.setpointMotion = signal.resample( self.setpointMotion, int(len(self.setpointMotion) / 2) )
      except Exception as e:
        print( e )
        self.setpointMotion = None
    self.motionSelector.text = fileName
  
  def _RunSetpointsMotion( self, enabled ):
    measure_range = self.measureSlider.range
    setpointAmplitide = abs( measure_range[ 0 ] - measure_range[ 1 ] ) / 4

    self.operationTime = 0.0
    self.curveStep = 0

    def UpdateSetpoint( delta ):
      setpoint = float( self.setpointMotion[ self.curveStep % len(self.setpointMotion) ] )
      self.curveStep += 1
      self.setpointSlider.value = setpoint * setpointAmplitide
    
    if enabled and self.setpointMotion is not None:
      self.setpointUpdateEvent = Clock.schedule_interval( UpdateSetpoint, self.UPDATE_INTERVAL * 2 )
    else:
      self.setpointSlider.value = 0.0
      self.stiffnessSlider.value = 0.0
      self.dampingSlider.value = 0.0
      if self.setpointUpdateEvent is not None: 
        self.setpointUpdateEvent.cancel()
        self.setpointUpdateEvent = None
  
  def SetCalibration( self, enabled ):
    self.isCalibrating = enabled
    if enabled: self._SendCommand( CALIBRATE )
    else: self._SendCommand( OPERATE if self.isOperating else PASSIVATE )
    self._RunSetpointsMotion( enabled )
  
  def SetOperation( self, enabled ):
    self.isOperating = enabled
    if enabled: self._SendCommand( OPERATE )
    else: self._SendCommand( PASSIVATE )
    self._RunSetpointsMotion( enabled )

class RobRehabApp( App ):
  def build( self ):
    self.title = 'RobRehab GUI'
    self.icon = 'rerob_icon.png'
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
