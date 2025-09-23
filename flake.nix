# SPDX-FileCopyrightText: Tim Sutton
# SPDX-License-Identifier: MIT
{
  description = "NixOS developer environment for QGIS plugins.";
  inputs.qgis-upstream.url = "github:qgis/qgis";
  inputs.geospatial.url = "github:imincik/geospatial-nix.repo";
  inputs.nixpkgs.follows = "geospatial/nixpkgs";
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs =
    {
      self,
      qgis-upstream,
      geospatial,
      nixpkgs,
    }:
    let
      system = "x86_64-linux";
      profileName = "PLANET";
      pkgs = import nixpkgs {
        inherit system;
        config = {
          allowUnfree = true;
        };
      };

      extraPythonPackages = ps: [
        ps.pyqtwebengine
        ps.jsonschema
        ps.debugpy
        ps.psutil
      ];
      qgisWithExtras = geospatial.packages.${system}.qgis.override {
        inherit extraPythonPackages;
      };
      qgisLtrWithExtras = geospatial.packages.${system}.qgis-ltr.override {
        inherit extraPythonPackages;
      };
      qgisMasterWithExtras = qgis-upstream.packages.${system}.qgis.override {
        inherit extraPythonPackages;
      };
      postgresWithPostGIS = pkgs.postgresql.withPackages (ps: [ ps.postgis ]);
    in
    {
      packages.${system} = {
        default = qgisWithExtras;
        qgis = qgisWithExtras;
        qgis-ltr = qgisLtrWithExtras;
        qgis-master = qgisMasterWithExtras;
        postgres = postgresWithPostGIS;
      };

      apps.${system} = {
        qgis = {
          type = "app";
          program = "${qgisWithExtras}/bin/qgis";
          args = [
            "--profile"
            "${profileName}"
          ];
        };
        qgis-ltr = {
          type = "app";
          program = "${qgisLtrWithExtras}/bin/qgis";
          args = [
            "--profile"
            "${profileName}"
          ];
        };
        qgis-master = {
          type = "app";
          program = "${qgisMasterWithExtras}/bin/qgis";
          args = [
            "--profile"
            "${profileName}"
          ];
        };
        qgis_process = {
          type = "app";
          program = "${qgisWithExtras}/bin/qgis_process";
          args = [
            "--profile"
            "${profileName}"
          ];
        };

      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.actionlint # for checking gh actions
          pkgs.bandit
          pkgs.bearer
          pkgs.chafa
          pkgs.codeql
          pkgs.ffmpeg
          pkgs.gdb
          pkgs.git
          pkgs.glogg
          pkgs.glow # terminal markdown viewer
          pkgs.gource # Software version control visualization
          pkgs.gum # UX for TUIs
          pkgs.isort
          pkgs.jq
          pkgs.libsForQt5.kcachegrind
          pkgs.luaPackages.luacheck
          pkgs.markdownlint-cli
          pkgs.neovim
          pkgs.nixfmt-rfc-style
          pkgs.nodejs_20 # needed for copilot in neovim
          pkgs.nodePackages.cspell
          pkgs.pre-commit
          pkgs.privoxy
          pkgs.pyprof2calltree # needed to covert cprofile call trees into a format kcachegrind can read
          pkgs.python3
          pkgs.qgis
          pkgs.qt5.full # so we get designer
          pkgs.qt5.qtbase
          pkgs.qt5.qtlocation
          pkgs.qt5.qtquickcontrols2
          pkgs.qt5.qtsvg
          pkgs.qt5.qttools
          pkgs.rpl
          pkgs.shellcheck
          pkgs.shfmt
          pkgs.stylua
          pkgs.virtualenv
          pkgs.vscode
          pkgs.yamlfmt
          pkgs.yamllint
          postgresWithPostGIS
          pkgs.nodePackages.cspell
          (pkgs.python3.withPackages (ps: [
            ps.black
            ps.click # needed by black
            ps.debugpy
            ps.flake8
            ps.gdal
            ps.httpx
            ps.jsonschema
            ps.mypy
            ps.numpy
            ps.odfpy
            ps.pandas
            ps.paver # For autocompletion in vscode
            ps.pip
            ps.psutil
            ps.pyqt5-stubs
            ps.pytest
            ps.pytest-qt
            ps.python
            ps.setuptools
            ps.snakeviz # For visualising cprofiler outputs
            ps.toml
            ps.typer
            ps.wheel
            # Add these for SQL linting/formatting:
            ps.sqlfmt
            ps.pip
            ps.setuptools
            ps.wheel
            ps.pytest
            ps.pytest-qt
            ps.black
            ps.click # needed by black
            ps.flake8
            ps.mypy
            ps.jsonschema
            ps.pandas
            ps.odfpy
            ps.psutil
            ps.httpx
            ps.toml
            # For autocompletion in vscode
            ps.pyqt5-stubs

            # This executes some shell code to initialize a venv in $venvDir before
            # dropping into the shell
            ps.venvShellHook
            ps.virtualenv
            # Those are dependencies that we would like to use from nixpkgs, which will
            # add them to PYTHONPATH and thus make them accessible from within the venv.
            ps.pyqtwebengine
          ]))

        ];
        shellHook = ''
          unset SOURCE_DATE_EPOCH

          # Create a virtual environment in .venv if it doesn't exist
           if [ ! -d ".venv" ]; then
            python -m venv .venv
          fi

          # Activate the virtual environment
          source .venv/bin/activate

          # Upgrade pip and install packages from requirements.txt if it exists
          pip install --upgrade pip > /dev/null
          if [ -f requirements.txt ]; then
            echo "Installing Python requirements from requirements.txt..."
            pip install -r requirements.txt > .pip-install.log 2>&1
            if [ $? -ne 0 ]; then
              echo "❌ Pip install failed. See .pip-install.log for details."
            fi
          else
            echo "No requirements.txt found, skipping pip install."
          fi
          if [ -f requirements-dev.txt ]; then
            echo "Installing Python requirements from requirements-dev.txt..."
            pip install -r requirements-dev.txt > .pip-install.log 2>&1
            if [ $? -ne 0 ]; then
              echo "❌ Pip install failed. See .pip-install.log for details."
            fi
          else
            echo "No requirements-dev.txt found, skipping pip install."
          fi

          echo "Setting up and running pre-commit hooks..."
          echo "-------------------------------------"
          pre-commit clean > /dev/null
          pre-commit install --install-hooks > /dev/null
          pre-commit run --all-files || true

          export PATH="$(pwd)/.nvim:$PATH"
          echo ""
          echo "-----------------------"
          echo "🌈 Your Dev Environment is prepared."
          echo "To run QGIS with your profile, use one of these commands:"
          echo ""
          echo "  scripts/run-qgis.sh"
          echo "  scripts/run-qgis-ltr.sh"
          echo "  scripts/run-qgis-master.sh"
          echo ""
          echo "📒 Note:"
          echo "-----------------------"
          echo "We provide a ready-to-use"
          echo "VSCode environment which you"
          echo "can start like this:"
          echo ""
          echo "./scripts/vscode.sh"
          echo ""
          echo "We also provide a ready to use neovim setup:"
          echo ""
          echo "🎯 You can start Neovim with GEEST configuration:"
          echo "📝 'vim' (which is an alias to) -> ./.nvim/vim"
          echo ""
        '';
      };
    };
}
