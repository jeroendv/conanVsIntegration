import unittest
from pathlib import Path

from conan_vs_integration import *
import os
import shutil

import xml.etree.ElementTree as ET


class chdir():
    def __init__(self, newPath):
        self.newPath = newPath
    
    def __enter__(self):

        if (not Path(self.newPath).is_dir()):
            raise Exception("Can not change to a directory that does not exist.")

        self.oldPath = os.getcwd()
        os.chdir(self.newPath)
        return Path()

    def __exit__(self, type, value, tb):
        os.chdir(self.oldPath)


class Test_Integrate:

    testFilesPre = Path(r"conan_vs_integration\test\TestFiles\VsProjectIntegration.pre")
    testFilesVerified = testFilesPre.with_name("VsProjectIntegration.verified")


    def setUp(self, tmpdir):
        print(str(tmpdir))
        from distutils.dir_util import copy_tree
        copy_tree(self.testFilesPre, str(tmpdir))

    def test_creationOfFiles(self, tmpdir):
        """Verify  that that appropriate files are created
        """
        self.setUp(tmpdir)
        with chdir(Path(tmpdir) / Path("Vs2017Project")) as p:
            vsProjectPath = p.absolute()

            # Test pre-conditions
            assert not Path("conanfile.txt").is_file(), \
                "before integration there should not be a 'conanfile.txt'"
            assert not Path("Conan.targets").is_file(), \
                "before integration there should not be a 'Conan.targets'"

            # test
            Integrate(VsProject(vsProjectPath))

            # test post-conditions
            # verify that requried files were created
            assert Path("conanfile.txt").is_file(), \
                "after integration a 'conanfile.txt' file should be present"
            assert Path("Conan.targets").is_file(), \
                "after integration 'Conan.targets' file should be present"
        
    def test_TargetsIntegration(self, tmpdir):
        """Verify that the 'conan.targets' is properly imported in project file
        """
        self.setUp(tmpdir)
        with chdir(Path(tmpdir) / Path("Vs2017Project")) as p:
            # test
            Integrate(VsProject(p.absolute()))


            # test post-conditions
            # search for the following node under projet file xml root 
            #       <Import Project="Conan.targets" />
            projTree = ET.parse(Path("VS2017Project.vcxproj"))
            root = projTree.getroot()
            ns = {'default': 'http://schemas.microsoft.com/developer/msbuild/2003'}

            for c in root.findall("default:Import", ns):
                print(c.tag, c.attrib)
                if ('Project' in c.attrib 
                    and c.get('Project') == 'Conan.targets'):
                    # node found :-)
                    return
        
            assert False, "no import node found that imports conan.targets"

    def test_conanFileIntegration(self, tmpdir):
        """Verify that the 'conafile.txt' is properly imported in project file
        """
        self.setUp(tmpdir)
        with chdir(Path(tmpdir) / Path("Vs2017Project")) as p:
            # test pre-conditions
            pass

            # test
            Integrate(VsProject(p.absolute()))


            # test post-conditions
            # search for the following node under the project file xml root 
            #       <ItemGroup>
            #         <Text Include="conanfile.txt" />
            #       </ItemGroup>
            # to the project file
            projTree = ET.parse(Path("VS2017Project.vcxproj"))
            root = projTree.getroot()
            ns = {'default': 'http://schemas.microsoft.com/developer/msbuild/2003'}

            for c in root.findall("default:ItemGroup/default:Text", ns):
                print(c.tag, c.attrib)
                if ('Include' in c.attrib 
                    and c.attrib['Include'] == 'conanfile.txt'):
                    # node found :-)              
                    return 
        
            assert False, "conanfile.txt include is missing from *.vcxproj file"


if __name__ == '__main__':
    import pytest
    pytest.main()