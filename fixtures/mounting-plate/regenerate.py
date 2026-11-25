"""Regenerate the pilot meshes from the pinned OpenCascade solid generator."""

from pathlib import Path
import runpy

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Message import Message_ProgressRange
from OCP.RWGltf import RWGltf_CafWriter
from OCP.RWMesh import RWMesh_CoordinateSystem_Yup, RWMesh_CoordinateSystem_Zup
from OCP.StlAPI import StlAPI_Writer
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import IndexedDataMap_TCollection_AsciiString_TCollection_AsciiString

import mounting_plate


ROOT = Path(__file__).resolve().parent


def write_glb(solid, path):
    BRepMesh_IncrementalMesh(solid, 0.02, False, 0.05)
    XCAFApp_Application.GetApplication_s()
    document = TDocStd_Document(TCollection_ExtendedString("BinXCAF"))
    XCAFDoc_DocumentTool.SetLengthUnit_s(document, 0.001)
    XCAFDoc_DocumentTool.ShapeTool_s(document.Main()).AddShape(solid, False)

    writer = RWGltf_CafWriter(TCollection_AsciiString(str(path)), True)
    coordinates = writer.ChangeCoordinateSystemConverter()
    coordinates.SetInputCoordinateSystem(RWMesh_CoordinateSystem_Zup)
    coordinates.SetOutputCoordinateSystem(RWMesh_CoordinateSystem_Yup)
    coordinates.SetInputLengthUnit(0.001)
    coordinates.SetOutputLengthUnit(1.0)
    metadata = IndexedDataMap_TCollection_AsciiString_TCollection_AsciiString()
    if not writer.Perform(document, metadata, Message_ProgressRange()):
        raise RuntimeError(f"Could not write {path}")


def main():
    # The pinned generator writes STEP and STL. Rebuild the BRep for the GLB exporter.
    runpy.run_path(str(ROOT / "mounting_plate.py"), run_name="__main__")
    write_glb(mounting_plate.gen_step(), ROOT / "mounting_plate.glb")

    controls = ROOT / "controls"
    controls.mkdir(exist_ok=True)
    nominal_length = mounting_plate.LENGTH_MM
    mounting_plate.LENGTH_MM += 1
    wide = mounting_plate.gen_step()
    mounting_plate.LENGTH_MM = nominal_length
    BRepMesh_IncrementalMesh(wide, 0.02, False, 0.05)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(wide, str(controls / "wide.stl")):
        raise RuntimeError("Could not write wide STL")

    mounting_plate.THICKNESS_MM += 1
    write_glb(mounting_plate.gen_step(), controls / "thick.glb")

    (controls / "broken.stl").write_bytes(b"invalid STL\n")
    (controls / "broken.glb").write_bytes(b"glTF")
    (controls / "broken.json").write_bytes(b'{"expected_mm":{"x":64}}\n')


if __name__ == "__main__":
    main()
