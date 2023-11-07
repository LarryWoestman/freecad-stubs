import inspect
from xml.etree import ElementTree as ET

from freecad_stub_gen.cpp_code.converters import toBool
from freecad_stub_gen.generators.common.doc_string import (
    formatDocstring,
    getDocFromNode,
)
from freecad_stub_gen.generators.common.names import (
    getClassName,
    getClassWithModulesFromNode,
    getFatherClassWithModules,
    getModuleName,
)
from freecad_stub_gen.generators.from_xml.dynamic_property import (
    XmlDynamicPropertyGenerator,
)
from freecad_stub_gen.generators.from_xml.method import XmlMethodGenerator
from freecad_stub_gen.generators.from_xml.static_property import XmlPropertyGenerator
from freecad_stub_gen.importable_map import importableMap
from freecad_stub_gen.python_code import indent
from freecad_stub_gen.python_code.module_container import Module


class FreecadStubGeneratorFromXML(
    XmlPropertyGenerator, XmlDynamicPropertyGenerator, XmlMethodGenerator
):
    """
    Generate class defined in xml file.
    Argument types are extracted from code.
    """

    def getStub(self, mod: Module, moduleName, submodule=''):
        header = f'# {self.baseGenFilePath.name}\n'

        tree = ET.parse(self.baseGenFilePath)
        for child in tree.getroot():
            if child.tag == 'PythonExport':
                self.currentNode = child
                content, classNameWithModules = self._getClassContent()

                modName = getModuleName(classNameWithModules, required=True)
                if submodule:
                    modName = f'{modName}.{submodule}'

                curMod = mod[modName]
                curMod.update(Module(header + content + '\n', self.requiredImports))
                self.requiredImports.clear()

    def _getClassContent(self):
        self.classNameWithModules = getClassWithModulesFromNode(self.currentNode)
        className = getClassName(self.classNameWithModules)
        baseClasses = ', '.join(self.genBaseClasses())
        classStr = f"class {className}({baseClasses}):\n"

        doc = getDocFromNode(self.currentNode)
        if importableMap.isImportable(self.classNameWithModules):
            doc = "This class can be imported.\n" + (doc or '')
        if doc:
            classStr += indent(formatDocstring(doc))
            classStr += '\n'
        classStr += indent(self.genInit())

        if specialCaseCode := self.getCodeForSpecialCase(className):
            classStr += indent(specialCaseCode)

        for attributeNode in sorted(
            self.currentNode.findall('Attribute'), key=self._nodeSort
        ):
            classStr += indent(self.getAttributes(attributeNode))
        for dynamicProperty in sorted(self.genDynamicProperties()):
            classStr += indent(dynamicProperty)

        for methodNode in sorted(
            self.currentNode.findall('Methode'), key=self._nodeSort
        ):
            classStr += indent(self.genMethod(methodNode))

        if toBool(self.currentNode.attrib.get('RichCompare', False)):
            classStr += indent(self.genRichCompare())
        if toBool(self.currentNode.attrib.get('NumberProtocol', False)):
            classStr += indent(self.genNumberProtocol(className))

        return classStr, self.classNameWithModules

    @staticmethod
    def _nodeSort(node: ET.Element):
        return node.attrib['Name']

    def genBaseClasses(self):
        """Only one class is available in xml as a father."""
        fatherModuleAndClass = getFatherClassWithModules(self.currentNode)
        self.requiredImports.add(getModuleName(fatherModuleAndClass, required=True))
        yield fatherModuleAndClass

        if self.classNameWithModules == 'FreeCAD.DocumentObjectGroup':
            yield 'FreeCAD.GroupExtension'

    def getCodeForSpecialCase(self, className: str) -> str:
        ret = ''
        if className == 'DocumentObject':
            ret += self.getProperty(
                'Proxy',
                'FreeCADTemplates.templates.ProxyPython',
                'FreeCADTemplates.templates.ProxyPython',
                readOnly=False,
            )
            self.requiredImports.add('FreeCADTemplates.templates')

        elif className == 'ViewProviderDocumentObject':
            ret += self.getProperty(
                'Proxy',
                'FreeCADTemplates.templates.ViewProviderPython',
                'FreeCADTemplates.templates.ViewProviderPython',
                readOnly=False,
            )
            self.requiredImports.add('FreeCADTemplates.templates')

        elif className == 'GroupExtension':
            ret += self.getProperty(
                'Group', 'list[DocumentObject]', 'list[DocumentObject]', readOnly=False
            )

        elif className == 'WorkbenchC':
            ret += workbenchBody + '\n\n'

        return ret


workbenchBody = inspect.cleandoc(
    """
    MenuText: str = ''
    ToolTip: str = ''
    Icon: str = None  # path to the icon

    def Initialize(self):
        raise NotImplementedError

    def Activated(self): ...

    def Deactivated(self): ...

    def ContextMenu(self, recipient): ...

    def reloadActive(self): ...

    def GetClassName(self):
        return 'Gui::PythonWorkbench'
"""
)
