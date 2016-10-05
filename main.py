import kivy
kivy.require( '1.9.1' )

from kivy.garden.graph import Graph, MeshLinePlot

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.clock import Clock

from random import randrange

from definitions import *
import ipclient

class RobRehabGUI( Widget ):
  connection = None

  ROBOT = 0
  JOINT = 1
  AXIS = 2
  deviceIDs = ( [], [], [] )
  currentDeviceIndexes = [ None for i in range( len(deviceIDs) ) ]
  NULL_ID = '<Select>'

  setpoints = [ 0.0 for var in range( AXIS_VARS_NUMBER ) ]

  def __init__( self, **kwargs ):
    super( RobRehabGUI, self ).__init__( **kwargs )
    # or Widget.__init__( **kwargs ) ?

    self.deviceSelectors = ( self.ids[ 'robot_selector' ], self.ids[ 'joint_selector' ], self.ids[ 'axis_selector' ] )
    self.deviceEntries = ( self.ids[ 'robots_list' ], self.ids[ 'joints_list' ], self.ids[ 'axes_list' ] )

    dataGraph = self.ids[ 'data_graph' ]
    axisGraph = Graph( xlabel='Time', ylabel='Axis', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25,
                       y_grid_label=True, x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-1.5, ymax=1.5 )
    self.axisPlot = MeshLinePlot( color=[ 1, 0, 0, 1 ] )
    axisGraph.add_plot( self.axisPlot )
    dataGraph.add_widget( axisGraph )
    jointGraph = Graph( xlabel='Time', ylabel='Joint', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25,
                        y_grid_label=True, x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-1.5, ymax=1.5 )
    self.jointPlot = MeshLinePlot( color=[ 0, 1, 0, 1 ] )
    jointGraph.add_plot( self.jointPlot )
    dataGraph.add_widget( jointGraph )

    Clock.schedule_interval( self.GraphUpdate, 0.02 )
    Clock.schedule_interval( self.NetworkUpdate, 0.02 )

  def ConnectClient( self, serverAddress ):
    self.connection = None
    self.deviceIDs = ( [], [], [] )
    serverType, serverHost = serverAddress.split( '://' )
    print( 'acquired %s server host: %s' % ( serverType, serverHost ) )
    if serverType == 'ip': self.connection = ipclient.Connection()
    if self.connection is not None:
      self.connection.Connect( serverHost )
      self.deviceIDs = self.connection.RefreshInfo()

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

  def GraphUpdate( self, *args ):
    self.axisPlot.points = [ ( sample, randrange( -150, 150 ) / 100.0 ) for sample in range( 100 ) ]
    self.jointPlot.points = [ ( sample, randrange( -150, 150 ) / 100.0 ) for sample in range( 100 ) ]

  def NetworkUpdate( self, *args ):
    SETPOINTS_MASK = int( '00010011', 2 )
    currentAxisIndex = self.currentDeviceIndexes[ self.AXIS ]
    if self.connection is not None and currentAxisIndex is not None:
      self.connection.SendAxisSetpoints( currentAxisIndex, SETPOINTS_MASK, self.setpoints )

  def SetUserName( self, name ):
    print( 'set user name ' + name )

  def SetDevice( self, type, name ):
    self.deviceSelectors[ type ].text = name
    deviceIDs = self.deviceIDs[ type ]
    self.currentDeviceIndexes[ type ] = deviceIDs.index( name ) if ( name in deviceIDs ) else None
    print( 'current type %d device index: %d' % ( type, self.currentDeviceIndexes[ type ] ) )

  def SendCommand( self, commandKey ):
    currentRobotIndex = self.currentDeviceIndexes[ self.ROBOT ]
    if self.connection is not None and currentRobotIndex is not None:
      self.connection.SendCommand( currentRobotIndex, commandKey ) 

  def SendSetpoints( self ):
    self.setpoints[ POSITION ] = self.ids[ 'setpoint_slider' ].value
    self.setpoints[ STIFFNESS ] = self.ids[ 'stiffness_slider' ].value
    print( 'set setpoint position = %.3f and stiffness = %.3f' % ( self.setpoints[ POSITION ], self.setpoints[ STIFFNESS ] ) )

class RobRehabApp( App ):
  def build( self ):
    self.title = 'RobRehab GUI'
    self.icon = 'rerob_icon.png'
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
