import xml.etree.ElementTree as ET
from freecad_stub_gen.module_map import moduleNamespace
import logging

logger = logging.getLogger(__name__)


def genBaseClasses(currentNode: ET.Element):
    bases = []
    if genClassName(currentNode) == 'Workbench':
        bases.append('FreeCADGui.Workbench')

    fatherClass = genFatherClass(currentNode)
    bases.append(fatherClass)
    return tuple(bases)


def genFatherClass(currentNode: ET.Element) -> str:
    fatherNamespace: str = currentNode.attrib['FatherNamespace']
    fatherName: str = currentNode.attrib['Father']

    if len(moduleNamespace.stemToPaths[fatherName]) == 1:
        return genTypeForStem(fatherName, fatherNamespace)
    else:
        fatherTwin = fatherName.removesuffix('Py')
        fatherModule = moduleNamespace.convertNamespaceToModule(fatherNamespace)
        name = f'{fatherModule}.{fatherTwin}'
        return name


def genTypeForStem(stem: str, namespace: str = None):
    if namespace is None:
        namespace = moduleNamespace.getNamespaceForStem(stem)

    pathType = moduleNamespace.stemToPaths[stem][0]
    root = ET.parse(pathType).getroot()
    exportElement = root.find('PythonExport')
    assert exportElement
    twin = genClassName(exportElement)

    if '.' in twin:
        return twin
    else:
        module = moduleNamespace.convertNamespaceToModule(namespace)
        return f'{module}.{twin}'


def genClassName(currentNode: ET.Element) -> str:
    """Based on
    https://github.com/FreeCAD/FreeCAD/blob/8ac722c1e89ef530564293efd30987db09017e12/src/Tools/generateTemplates/templateClassPyExport.py#L279
    """
    if not (name := currentNode.attrib.get('PythonName')):
        name = currentNode.attrib['Twin']

    return name


def getSimpleClassName(currentNode: ET.Element) -> str:
    className = genClassName(currentNode)
    return className[className.rfind('.') + 1:]
