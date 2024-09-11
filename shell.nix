with import <nixpkgs> { };
let
  # For packages pinned to a specific version
  pinnedHash = "nixos-24.05";
  pinnedPkgs = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/${pinnedHash}.tar.gz") { };
  pythonPackages = python3Packages;
in pkgs.mkShell rec {
  name = "impurePythonEnv";
  venvDir = "./.venv";
  buildInputs = [
    # A Python interpreter including the 'venv' module is required to bootstrap
    # the environment.
    pythonPackages.python
    python3Packages.pip
    python3Packages.setuptools
    python3Packages.wheel
    python3Packages.pytest
    python3Packages.pytest-qt
    python3Packages.black
    python3Packages.jsonschema

    # This executes some shell code to initialize a venv in $venvDir before
    # dropping into the shell
    pythonPackages.venvShellHook
    pinnedPkgs.virtualenv
    # Those are dependencies that we would like to use from nixpkgs, which will
    # add them to PYTHONPATH and thus make them accessible from within the venv.
    pythonPackages.debugpy
    pythonPackages.numpy
    pythonPackages.pip
    pinnedPkgs.vim
    git
    qgis
    qt5.qtbase
    qt5.qtsvg
    qt5.qttools
    #qt5.qtwebkit
    qt5.qtlocation
    qt5.qtquickcontrols2
    vscode
    # Would be nice if this worked, we could replace the same logic in the QGIS start script
    #qgis.override { extraPythonPackages = ps: [ ps.numpy ps.future ps.geopandas ps.rasterio ];}
    gum # UX for TUIs
    skate # Distributed key/value store
    glow # terminal markdown viewer
  ];
  # Run this command, only after creating the virtual environment
  PROJECT_ROOT = builtins.getEnv "PWD";

  postVenvCreation = ''
    unset SOURCE_DATE_EPOCH
    pip install -r requirements-dev.txt
    echo "-----------------------"
    echo "🌈 Your Dev Environment is prepared."
    echo "Run qgis from the command line"
    echo "for a qgis environment with"
    echo "geopandas and rasterio, start QGIS"
    echo "like this:"
    echo ""
    echo "./start_qgis.sh"
    echo ""
    echo "📒 Note:"
    echo "-----------------------"
    echo "We provide a ready to use"
    echo "VSCode environment which you"
    echo "can start like this:"
    echo ""
    echo "./vscode.sh"
    echo "-----------------------"
  '';

  # Now we can execute any commands within the virtual environment.
  # This is optional and can be left out to run pip manually.
  postShellHook = ''
    # allow pip to install wheels
    unset SOURCE_DATE_EPOCH
  '';


}
