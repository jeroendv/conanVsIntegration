from conan_vs_integration import *
import argparse
import subprocess


"""Install conan dependencies for a given VsConanProject based on the active IDE settings.

Visual Studio IDE settings like Platform, Toolset, Configuration, VisualStudioVersion
are translated into their respective Conan settings.
"""


def parse_cli_args():
    """parse the script input arguments"""
    parser = argparse.ArgumentParser(description="install conan dependencies for a given project")

    parser.add_argument("-v", "--verbose",
                    help="increase output verbosity",
                    action="store_true")

    parser.add_argument("-d", "--debug",
                    help="enable debug output",
                    action="store_true")
                   

    parser.add_argument("-N", "--dry-run",
                        help="Do not perform any actions, only simulate them.")
    
    parser.add_argument("--Platform")
    parser.add_argument("--Toolset")
    parser.add_argument("--Configuration")
    parser.add_argument("--VisualStudioVersion")

    args = parser.parse_args()

    if args.debug:
        DebugLog.enabled = True

    with DebugLogScopedPush(Path(__file__).name + " cli arguments:"):
        DebugLog.print(str(args))

    # register custom exception handler
    h = MsBuildExceptionHandle(args.debug)
    sys.excepthook = h.exception_handler
    
    return args


class ConanInstallChecksum:
    """Track checksums of all conan autogenerated install files for a 'VsConanProject'
    
    Used to identify if a 'conan install ./' was an effective No-Op.
    If so then the checksums before and after will match.
    """
    def __init__(self, vsConanProject):
        self.vsConanProject = vsConanProject
        self.fileHashes = {}
        for e in self.vsConanProject.path().iterdir():
            if self._isConanInstallFile(e):
                self.fileHashes[e] = filehash(e)
    
    def verify(self):
        """Verify conan install file checksums

        returns [] when successfull or a list of string descriptors if not.
        """
        conanFiles = [f for f in self.vsConanProject.path().iterdir() if self._isConanInstallFile(f)]

        # verify conan install file count
        if (len(conanFiles) > len(self.fileHashes)):
            conanFiles = conanFiles - self.fileHashes.keys()
            newFiles  = [f.name for f in conanFiles]
            return ["there are new conan instal files: " + " ".join(newFiles)]
        elif (len(conanFiles) < len(self.fileHashes)):
            removedFiles = [f.name for f in self.fileHashes.keys() - set(conanFiles)]
            return ["Conan install files were removed: " + " ".join(removedFiles)]

        # verify each file's hash
        for (p, h) in self.fileHashes.items():
            if (not p.exists() or not p.is_file()):
                return ["{file} no longer exists".format(
                         file = p.name)]
            
            currentHash = filehash(p)
            if (currentHash != h):
                return ["{file} has changed".format(
                         file = p.name)]
        
        return None

    def _isConanInstallFile(self, path):
        """Is pathlib.Path a conan auto generated install file"""
        return path.match('conanbuildinfo*')




def main():
    args = parse_cli_args()

    vsConanProject = VsConanProject(os.getcwd())
    conanInstallChecksum = ConanInstallChecksum(vsConanProject)

    # run conan install 
    cmd = ['conan', 'install', './']
    cmd += ['--file', 'conanfile.txt']
    cmd += ['-s', processPlatform(args)]
    cmd += ['-s', processConfiguration(args)]
    cmd += ['-s', processVisualStudioVersion(args)]
    cmd += ['-s', processToolset(args)]
    cmd += ['--generator', 'visual_studio_toolset_multi']
    cmd += ['--update']
    cmd += ['--build=missing']
    
    DebugLog.print("conan cli command: " + " ".join(cmd))
    subprocess.check_call(cmd)

    errors = conanInstallChecksum.verify()
    if (errors is not None):
        # the checksums failed, conan installed something  or a pacakge changed, or ...
        MsBuild.Error("conan installed or updated missing packages. restart build is required!")
        for e in errors:
            sys.stderr.write("\t" + e)
       
        # i.e. the project state was changed and the build must be restarted
        # so exit process indicating failure
        sys.exit(1)

    # the install was a noop, everyting was already installed
    # exit process indicating success
    assert(errors is None)
    sys.exit(0)



def processPlatform(args):
    if (args.Platform == "Win32"):
        return "arch=x86"
    elif(args.Platform == "x64"):
        return "arch=x86_64"
    else:
        raise Exception("unknown platform '%s', it can not be mapped to a conan.arch setting" % args.Platform)

def processVisualStudioVersion(args):

    # http://marcofoco.com/microsoft-visual-c-version-map/
    # map a VisualStudio version to a conan settings.compiler.version
    versionMap ={
        "10.0": "10", # Visual Studio 2010
        "11.0": "11", # Visual Studio 2012
        "12.0": "12", # Visual Studio 2013
        "14.0": "14", # Visual Studio 2015
        "15.0": "15"  # Visual Studio 2017
    }

    if (args.VisualStudioVersion not in versionMap):
        raise Exception("unknown VisualStudioVersion '%s', it can not be mapped to a conan.compiler.version setting" % args.VisualStudioVersion)


    return "compiler.version=%s" % versionMap[args.VisualStudioVersion]
    
    


def processConfiguration(args):
    return "build_type=" + args.Configuration

def processToolset(args):
    return "compiler.toolset="+args.Toolset


