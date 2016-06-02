import kivy
kivy.require('1.9.1')

from kivy.garden.graph import Graph, MeshLinePlot

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock

from random import randrange

class RobRehabGUI( Widget ):
  
  def __init__(self, **kwargs):
    super( RobRehabGUI, self ).__init__( **kwargs )  
    # or Widget.__init__( **kwargs ) ?
    self.dataGraph = self.ids[ 'data_graph' ]
    self.axisGraph = Graph( xlabel='Time', ylabel='Axis', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=5,
                            y_grid_label=True, x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-10, ymax=10 )
    self.axisPlot = MeshLinePlot( color=[ 1, 0, 0, 1 ] )
    self.axisGraph.add_plot( self.axisPlot )
    self.dataGraph.add_widget( self.axisGraph )
    self.jointGraph = Graph( xlabel='Time', ylabel='Joint', x_ticks_minor=5, x_ticks_major=25, y_ticks_major=1,
                            y_grid_label=True, x_grid_label=True, padding=5, x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-2, ymax=2 )
    self.jointPlot = MeshLinePlot( color=[ 0, 1, 0, 1 ] )
    self.jointGraph.add_plot( self.jointPlot )
    self.dataGraph.add_widget( self.jointGraph )
    
    Clock.schedule_interval( self.GraphUpdate, 0.005 )
    
  def GraphUpdate( self, *args ):
    
    self.axisPlot.points = [ (sample, randrange( -1000, 1000 ) / 100.0 ) for sample in range( 100 ) ]    
    
    self.jointPlot.points = [ (sample, randrange( -200, 200 ) / 100.0 ) for sample in range( 100 ) ]
    

class RobRehabApp( App ):
  def build( self ):
    return RobRehabGUI()

if __name__ == '__main__':
  RobRehabApp().run()
