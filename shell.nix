{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.setuptools
    pkgs.python3Packages.wheel
    pkgs.python3Packages.pytest
    pkgs.python3Packages.pytest-qt
    pkgs.python3Packages.black
    pkgs.python3Packages.jsonschema
    pkgs.mkdocs
    pkgs.mkdocs-material
    pkgs.mkdocs-plugins.mkdocstrings
    pkgs.qt5.qtbase
    pkgs.qt5.qtsvg
    pkgs.qt5.qttools
    pkgs.qt5.qtwebkit
    pkgs.qt5.qtlocation
    pkgs.qt5.qtquickcontrols2
    pkgs.qgis
    pkgs.nodejs
    pkgs.vscode
    pkgs.git
  ];

  vscodeExtensions = with pkgs.vscode-extensions; [
    ms-python.python
    ms-python.vscode-pylance
    ms-toolsai.jupyter
  ];

  shellHook = ''
    export PYTHONPATH=$PYTHONPATH:./GEEST
    echo "Development environment for GEEST is set up."
  '';
}

