import kivy
kivy.require('1.9.1')

from kivy.garden.graph import Graph, MeshLinePlot

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.clock import Clock

from random import randrange

class RobRehabGUI( Widget ):

  def __init__( self, **kwargs ):
    super( RobRehabGUI, self ).__init__( **kwargs )
    # or Widget.__init__( **kwargs ) ?
    self.jointDropDown = DropDown()
    jointButton = Button( text='Entry' )
    jointButton.bind( on_release=lambda button: self.jointDropDown.select( button.text ) )
    self.jointDropDown.add_widget( jointButton )
    self.ids[ 'joint_selector' ].bind( on_release=self.jointDropDown.open )
    self.jointDropDown.bind( on_select=lambda instance, value: self.SetUserName( value ) )

    self.dataGraph = self.ids[ 'data_graph' ]
    self.axisGraph = Graph( xlabel='Time', ylabel='Axis', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25,
                            y_grid_label=True, x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-1.5, ymax=1.5 )
    self.axisPlot = MeshLinePlot( color=[ 1, 0, 0, 1 ] )
    self.axisGraph.add_plot( self.axisPlot )
    self.dataGraph.add_widget( self.axisGraph )
    self.jointGraph = Graph( xlabel='Time', ylabel='Joint', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=0.25,
                            y_grid_label=True, x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-1.5, ymax=1.5 )
    self.jointPlot = MeshLinePlot( color=[ 0, 1, 0, 1 ] )
    self.jointGraph.add_plot( self.jointPlot )
    self.dataGraph.add_widget( self.jointGraph )

    Clock.schedule_interval( self.GraphUpdate, 0.02 )

  def GraphUpdate( self, *args ):
    self.axisPlot.points = [ ( sample, randrange( -150, 150 ) / 100.0 ) for sample in range( 100 ) ]
    self.jointPlot.points = [ ( sample, randrange( -150, 150 ) / 100.0 ) for sample in range( 100 ) ]

  def SetUserName( self, value ):
      print( 'set user name ' + value )

class RobRehabApp( App ):
  def build( self ):
    self.title = 'RobRehab GUI'
    self.icon = 'rerob_icon.png'
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
