import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import math
from Endoscopy import EndoscopyComputePath

#
# CurveMaker
#

class CurveMaker:
  def __init__(self, parent):
    parent.title = "Curve Maker"
    parent.categories = ["Informatics"]
    parent.dependencies = []
    parent.contributors = ["Junichi Tokuda (BWH), Laurent Chauvin (BWH)"]
    parent.helpText = """
    This module generates a 3D curve model that connects fiducials listed in a given markup node. 
    """
    parent.acknowledgementText = """
    This work was supported by National Center for Image Guided Therapy (P41EB015898). The module is based on a template developed by Jean-Christophe Fillion-Robin, Kitware Inc. and Steve Pieper, Isomics, Inc. partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.
    self.parent = parent


#
# CurveMakerWidget
#

class CurveMakerWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()
    self.logic = CurveMakerLogic()
    self.tag = 0

  def setup(self):
    # Instantiate and connect widgets ...

    ####################
    # For debugging
    #
    # Reload and Test area
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)
    
    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "CurveMaker Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)
    #
    ####################

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Source points (vtkMRMLMarkupsFiducialNode)
    #
    self.SourceSelector = slicer.qMRMLNodeComboBox()
    self.SourceSelector.nodeTypes = ( ("vtkMRMLMarkupsFiducialNode"), "" )
    self.SourceSelector.addEnabled = True
    self.SourceSelector.removeEnabled = False
    self.SourceSelector.noneEnabled = True
    self.SourceSelector.showHidden = False
    self.SourceSelector.renameEnabled = True
    self.SourceSelector.showChildNodeTypes = False
    self.SourceSelector.setMRMLScene( slicer.mrmlScene )
    self.SourceSelector.setToolTip( "Pick up a Markups node listing fiducials." )
    parametersFormLayout.addRow("Source points: ", self.SourceSelector)

    #
    # Target point (vtkMRMLMarkupsFiducialNode)
    #
    self.DestinationSelector = slicer.qMRMLNodeComboBox()
    self.DestinationSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.DestinationSelector.addEnabled = True
    self.DestinationSelector.removeEnabled = False
    self.DestinationSelector.noneEnabled = True
    self.DestinationSelector.showHidden = False
    self.DestinationSelector.renameEnabled = True
    self.DestinationSelector.selectNodeUponCreation = True
    self.DestinationSelector.showChildNodeTypes = False
    self.DestinationSelector.setMRMLScene( slicer.mrmlScene )
    self.DestinationSelector.setToolTip( "Pick up or create a Model node." )
    parametersFormLayout.addRow("Curve model: ", self.DestinationSelector)


    #
    # Radius for the tube
    #
    self.RadiusSliderWidget = ctk.ctkSliderWidget()
    self.RadiusSliderWidget.singleStep = 1.0
    self.RadiusSliderWidget.minimum = 1.0
    self.RadiusSliderWidget.maximum = 50.0
    self.RadiusSliderWidget.value = 5.0
    self.RadiusSliderWidget.setToolTip("Set the raidus of the tube.")
    parametersFormLayout.addRow("Radius: ", self.RadiusSliderWidget)

    #
    # Radio button to select interpolation method
    #
    self.InterpolationLayout = qt.QHBoxLayout()
    self.InterpolationNone = qt.QRadioButton("None")
    self.InterpolationNone.connect('clicked(bool)', self.onSelectInterpolationNone)
    self.InterpolationCardinalSpline = qt.QRadioButton("Cardinal Spline")
    self.InterpolationCardinalSpline.connect('clicked(bool)', self.onSelectInterpolationCardinalSpline)
    self.InterpolationHermiteSpline = qt.QRadioButton("Hermite Spline (for Endoscopy)")
    self.InterpolationHermiteSpline.connect('clicked(bool)', self.onSelectInterpolationHermiteSpline)
    self.InterpolationLayout.addWidget(self.InterpolationNone)
    self.InterpolationLayout.addWidget(self.InterpolationCardinalSpline)
    self.InterpolationLayout.addWidget(self.InterpolationHermiteSpline)
    
    self.InterpolationGroup = qt.QButtonGroup()
    self.InterpolationGroup.addButton(self.InterpolationNone)
    self.InterpolationGroup.addButton(self.InterpolationCardinalSpline)
    self.InterpolationGroup.addButton(self.InterpolationHermiteSpline)

    ## default interpolation method
    self.InterpolationCardinalSpline.setChecked(True)
    self.onSelectInterpolationCardinalSpline(True)

    parametersFormLayout.addRow("Interpolation: ", self.InterpolationLayout)

    #
    # Radio button for ring mode
    #
    self.RingLayout = qt.QHBoxLayout()
    self.RingOff = qt.QRadioButton("Off")
    self.RingOff.connect('clicked(bool)', self.onRingOff)
    self.RingOn = qt.QRadioButton("On")
    self.RingOn.connect('clicked(bool)', self.onRingOn)
    self.RingLayout.addWidget(self.RingOff)
    self.RingLayout.addWidget(self.RingOn)
    
    self.RingGroup = qt.QButtonGroup()
    self.RingGroup.addButton(self.RingOff)
    self.RingGroup.addButton(self.RingOn)

    ## default ring mode
    self.RingOff.setChecked(True)
    self.onRingOff(True)

    parametersFormLayout.addRow("Ring mode: ", self.RingLayout)
    
    #
    # Check box to start curve visualization
    #
    self.EnableCheckBox = qt.QCheckBox()
    self.EnableCheckBox.checked = 0
    self.EnableCheckBox.setToolTip("If checked, the CurveMaker module keeps updating the model as the points are updated.")
    parametersFormLayout.addRow("Enable", self.EnableCheckBox)

    # Connections
    self.EnableCheckBox.connect('toggled(bool)', self.onEnable)
    self.SourceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSourceSelected)
    self.DestinationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onDestinationSelected)
    self.RadiusSliderWidget.connect("valueChanged(double)", self.onTubeUpdated)

    # Add vertical spacer
    self.layout.addStretch(1)
    
  def cleanup(self):
    pass

  def onEnable(self, state):
    self.logic.enableAutomaticUpdate(state)

  def onSourceSelected(self):
    # Remove observer if previous node exists
    if self.logic.SourceNode and self.tag:
      self.logic.SourceNode.RemoveObserver(self.tag)

    # Update selected node, add observer, and update control points
    if self.SourceSelector.currentNode():
      self.logic.SourceNode = self.SourceSelector.currentNode()

      # Check if model has already been generated with for this fiducial list
      tubeModelID = self.logic.SourceNode.GetAttribute('CurveMaker.CurveModel')
      self.DestinationSelector.setCurrentNodeID(tubeModelID)

      self.tag = self.logic.SourceNode.AddObserver('ModifiedEvent', self.logic.controlPointsUpdated)

    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('CurveMaker.CurveModel',self.logic.DestinationNode.GetID())
      #self.logic.generateControlPolyData()
      self.logic.updateCurve()

  def onDestinationSelected(self):
    # Update destination node
    if self.DestinationSelector.currentNode():
      self.logic.DestinationNode = self.DestinationSelector.currentNode()

    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('CurveMaker.CurveModel',self.logic.DestinationNode.GetID())
      #self.logic.generateControlPolyData()
      self.logic.updateCurve()

  def onTubeUpdated(self):
    self.logic.setTubeRadius(self.RadiusSliderWidget.value)

  def onReload(self,moduleName="CurveMaker"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

  def onSelectInterpolationNone(self, s):
    self.logic.setInterpolationMethod(0)

  def onSelectInterpolationCardinalSpline(self, s):
    self.logic.setInterpolationMethod(1)

  def onSelectInterpolationHermiteSpline(self, s):
    self.logic.setInterpolationMethod(2)

  def onRingOff(self, s):
    self.logic.setRing(0)

  def onRingOn(self, s):
    self.logic.setRing(1)

#
# CurveMakerLogic
#

class CurveMakerLogic:

  def __init__(self):
    self.SourceNode = None
    self.DestinationNode = None
    self.TubeRadius = 5.0

    self.AutomaticUpdate = False
    self.NumberOfIntermediatePoints = 20
    self.ModelColor = [0.0, 0.0, 1.0]

    self.ControlPoints = None
    
    # Interpolation method:
    #  0: None
    #  1: Cardinal Spline (VTK default)
    #  2: Hermite Spline (Endoscopy module default)
    self.InterpolationMethod = 0

    self.RingMode = 0

  def setNumberOfIntermediatePoints(self,npts):
    if npts > 0:
      self.NumberOfIntermediatePoints = npts
    self.updateCurve()

  def setTubeRadius(self, radius):
    self.TubeRadius = radius
    self.updateCurve()

  def setInterpolationMethod(self, method):
    if method > 3 or method < 0:
      self.InterpolationMethod = 0
    else:
      self.InterpolationMethod = method
    self.updateCurve()

  def setRing(self, switch):
    self.RingMode = switch
    self.updateCurve()
    
  def enableAutomaticUpdate(self, auto):
    self.AutomaticUpdate = auto
    self.updateCurve()

  def controlPointsUpdated(self,caller,event):
    if caller.IsA('vtkMRMLMarkupsFiducialNode') and event == 'ModifiedEvent':
      self.updateCurve()

  def nodeToPath(self, node, poly):
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    nOfControlPoints = self.SourceNode.GetNumberOfFiducials()
    pos = [0.0, 0.0, 0.0]

    points.SetNumberOfPoints(nOfControlPoints)
    for i in range(nOfControlPoints):
      self.SourceNode.GetNthFiducialPosition(i,pos)
      points.SetPoint(i,pos)

    cellArray.InsertNextCell(nOfControlPoints)
    for i in range(nOfControlPoints):
      cellArray.InsertCellPoint(i)
  
    poly.Initialize()
    poly.SetPoints(points)
    poly.SetLines(cellArray)

  def pathToPoly(self, path, poly):
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    points = vtk.vtkPoints()
    poly.SetPoints(points)

    lines = vtk.vtkCellArray()
    poly.SetLines(lines)

    linesIDArray = lines.GetData()
    linesIDArray.Reset()
    linesIDArray.InsertNextTuple1(0)
    
    polygons = vtk.vtkCellArray()
    poly.SetPolys( polygons )
    idArray = polygons.GetData()
    idArray.Reset()
    idArray.InsertNextTuple1(0)
    
    for point in path:
      pointIndex = points.InsertNextPoint(*point)
      linesIDArray.InsertNextTuple1(pointIndex)
      linesIDArray.SetTuple1( 0, linesIDArray.GetNumberOfTuples() - 1 )
      lines.SetNumberOfCells(1)

  def nodeToClosedCardinalSpline(self, sourceNode, outputPoly):
    
    nOfControlPoints = sourceNode.GetNumberOfFiducials()
    pos = [0.0, 0.0, 0.0]

    # One spline for each direction.
    aSplineX = vtk.vtkCardinalSpline()
    aSplineY = vtk.vtkCardinalSpline()
    aSplineZ = vtk.vtkCardinalSpline()
    
    aSplineX.ClosedOn()
    aSplineY.ClosedOn()
    aSplineZ.ClosedOn()

    for i in range(0, nOfControlPoints):
      sourceNode.GetNthFiducialPosition(i, pos)
      aSplineX.AddPoint(i, pos[0])
      aSplineY.AddPoint(i, pos[1])
      aSplineZ.AddPoint(i, pos[2])
    
    # Interpolate x, y and z by using the three spline filters and
    # create new points
    nInterpolatedPoints = 400
    points = vtk.vtkPoints()
    r = [0.0, 0.0]
    aSplineX.GetParametricRange(r)
    t = r[0]
    p = 0
    tStep = (nOfControlPoints-1.0)/(nInterpolatedPoints-1.0)
    while t < r[1]+1.0:
      points.InsertPoint(p, aSplineX.Evaluate(t), aSplineY.Evaluate(t), aSplineZ.Evaluate(t))
      t = t + tStep
      p = p + 1
    # Make sure to close the loop
    points.InsertPoint(p, aSplineX.Evaluate(r[1]+1.0), aSplineY.Evaluate(r[1]+1.0), aSplineZ.Evaluate(r[1]+1.0))
    
    nOutputPoints = p+1
    lines = vtk.vtkCellArray()
    lines.InsertNextCell(nOutputPoints)
    for i in range(0, nOutputPoints):
      lines.InsertCellPoint(i)
        
    outputPoly.SetPoints(points)
    outputPoly.SetLines(lines)

    
  def updateCurve(self):

    if self.AutomaticUpdate == False:
      return

    if self.SourceNode and self.DestinationNode:

      if self.ControlPoints == None:
        self.ControlPoints = vtk.vtkPolyData()

      if self.DestinationNode.GetDisplayNodeID() == None:
        modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
        modelDisplayNode.SetColor(self.ModelColor)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        self.DestinationNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

      if self.InterpolationMethod == 0:

        self.nodeToPath(self.SourceNode, self.ControlPoints, 0)

        append = vtk.vtkAppendPolyData()

        points = self.ControlPoints.GetPoints()
        point0 = [0, 0, 0]
        point1 = [0, 0, 0]

        nPoints = points.GetNumberOfPoints()

        for i in range(0, nPoints-1):
          
          points.GetPoint(i, point0)
          points.GetPoint(i+1, point1)
          
          p = vtk.vtkPoints()
          p.SetNumberOfPoints(2)
          p.SetPoint(0, point0)
          p.SetPoint(1, point1)
          
          ca = vtk.vtkCellArray()
          ca.InsertNextCell(2)
          ca.InsertCellPoint(0)
          ca.InsertCellPoint(1)

          pd = vtk.vtkPolyData()
          pd.Initialize()
          pd.SetPoints(p)
          pd.SetLines(ca)
          
          tubeFilter = vtk.vtkTubeFilter()
          tubeFilter.SetInputData(pd)
          tubeFilter.SetRadius(self.TubeRadius)
          tubeFilter.SetNumberOfSides(20)
          tubeFilter.CappingOn()
          tubeFilter.Update()
        
          if vtk.VTK_MAJOR_VERSION <= 5:
            append.AddInput(tubeFilter.GetOutput());
          else:
            append.AddInputData(tubeFilter.GetOutput());

        append.Update();
        self.DestinationNode.SetAndObservePolyData(append.GetOutput())

      elif self.InterpolationMethod == 1: # Cardinal Spline

        tubeFilter = vtk.vtkTubeFilter()
        
        if self.RingMode > 0:
          curvePoly = vtk.vtkPolyData()
          self.nodeToClosedCardinalSpline(self.SourceNode, curvePoly)
          tubeFilter.SetInputData(curvePoly)
        else:
          self.nodeToPath(self.SourceNode, self.ControlPoints)
          splineFilter = vtk.vtkSplineFilter()
          spline = vtk.vtkCardinalSpline()
          spline.ClosedOff()

          splineFilter.SetSpline(spline)
          if vtk.VTK_MAJOR_VERSION <= 5:
            splineFilter.SetInput(self.ControlPoints)
          else:
            splineFilter.SetInputData(self.ControlPoints)

          #nInterpolatedPoints = self.NumberOfIntermediatePoints*(self.ControlPoints.GetPoints().GetNumberOfPoints()-1)        
          #splineFilter.SetSubdivideToSpecified();
          #splineFilter.SetNumberOfSubdivisions(nInterpolatedPoints)
          splineFilter.Update()

          #print splineFilter.GetSpline()
          tubeFilter.SetInputConnection(splineFilter.GetOutputPort())
          
        tubeFilter.SetRadius(self.TubeRadius)
        tubeFilter.SetNumberOfSides(20)
        tubeFilter.CappingOn()
        tubeFilter.Update()

        self.DestinationNode.SetAndObservePolyData(tubeFilter.GetOutput())

      elif self.InterpolationMethod == 2: # Hermite Spline
        
        result = EndoscopyComputePath(self.SourceNode)
        self.pathToPoly(result.path, self.ControlPoints)

        tubeFilter = vtk.vtkTubeFilter()
        tubeFilter.SetInputData(self.ControlPoints)
        tubeFilter.SetRadius(self.TubeRadius)
        tubeFilter.SetNumberOfSides(20)
        tubeFilter.CappingOn()
        tubeFilter.Update()
        self.DestinationNode.SetAndObservePolyData(tubeFilter.GetOutput())

      self.DestinationNode.Modified()
      
      if self.DestinationNode.GetScene() == None:
        slicer.mrmlScene.AddNode(self.DestinationNode)
        
