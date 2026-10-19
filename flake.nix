# SPDX-FileCopyrightText: Tim Sutton
# SPDX-License-Identifier: MIT
{
  description = "NixOS developer environment for QGIS plugins.";
  # QGIS comes straight from nixpkgs: `qgis` tracks the latest release line
  # (4.x) and `qgis-ltr` the long-term release (3.44.x).
  # Pinned to the 2026-06-15 nixos-unstable revision — the newest revision on
  # which hydra built (and cached) qgis 4.0.3 and qgis-ltr 3.44.11; later
  # revisions bump gdal to 3.13 which breaks the pdal build, so QGIS is
  # uncached there and would compile from source on every machine.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/b4f4a5cf27a0eb848c6212be746a0a718f3bb019";

  outputs =
    {
      self,
      nixpkgs,
    }:
    let
      system = "x86_64-linux";
      profileName = "GEOE3";
      pkgs = import nixpkgs {
        inherit system;
        config = {
          allowUnfree = true;
        };
      };

      extraPythonPackages = ps: [
        ps.jsonschema
        ps.debugpy
        ps.psutil
        ps.h3
        ps.pyarrow
      ];
      # QGIS 4.x is Qt6/PyQt6; QGIS 3.44 LTR is Qt5/PyQt5 — each needs the
      # matching WebEngine binding, so it is added per variant here rather
      # than in the shared list above.
      qgisWithExtras = pkgs.qgis.override {
        extraPythonPackages = ps: (extraPythonPackages ps) ++ [ ps.pyqt6-webengine ];
      };
      qgisLtrWithExtras = pkgs.qgis-ltr.override {
        extraPythonPackages = ps: (extraPythonPackages ps) ++ [ ps.pyqtwebengine ];
      };
      postgresWithPostGIS = pkgs.postgresql.withPackages (ps: [ ps.postgis ]);
      # Wrappers around scripts/run-docker-tests.sh (all logic lives in the
      # dotfile script; these only bake in the QGIS major version argument).
      mkDockerTestApp =
        variant:
        let
          wrapper = pkgs.writeShellApplication {
            name = "geoe3-docker-tests-${variant}";
            runtimeInputs = [
              pkgs.docker
              pkgs.git
            ];
            text = ''exec "$PWD/scripts/run-docker-tests.sh" ${variant} "$@"'';
          };
        in
        {
          type = "app";
          program = "${wrapper}/bin/geoe3-docker-tests-${variant}";
        };
    in
    {
      packages.${system} = {
        default = qgisWithExtras;
        qgis = qgisWithExtras;
        qgis-ltr = qgisLtrWithExtras;
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
        qgis_process = {
          type = "app";
          program = "${qgisWithExtras}/bin/qgis_process";
          args = [
            "--profile"
            "${profileName}"
          ];
        };
        # Test suite in the official QGIS docker images (see scripts/run-docker-tests.sh)
        test-qgis3 = mkDockerTestApp "3"; # QGIS 3.34 LTR (Qt5)
        test-qgis4 = mkDockerTestApp "4"; # QGIS 4.x master (Qt6)
        test-qgis = mkDockerTestApp "all"; # both

      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [

          qgisWithExtras
          pkgs.actionlint # for checking gh actions
          pkgs.bandit
          pkgs.bearer
          pkgs.chafa
          pkgs.nixfmt-rfc-style
          pkgs.codeql
          pkgs.ffmpeg
          pkgs.gdb
          pkgs.git
          pkgs.minio-client # for grabbing ookla data
          pkgs.glogg
          pkgs.glow # terminal markdown viewer
          pkgs.gource # Software version control visualization
          pkgs.gum # UX for TUIs
          pkgs.jq
          pkgs.kdePackages.kcachegrind
          pkgs.luaPackages.luacheck
          pkgs.markdownlint-cli
          pkgs.nixfmt-rfc-style
          pkgs.pre-commit
          pkgs.nixfmt-rfc-style
          pkgs.privoxy
          pkgs.pyprof2calltree # needed to covert cprofile call trees into a format kcachegrind can read
          # SRS / document build chain (srs/build.sh)
          pkgs.plantuml # UML diagrams -> SVG/PNG
          pkgs.libreoffice # docx -> pdf conversion
          pkgs.lato # Kartoza document typeface
          # Python development essentials
          pkgs.pyright
          # Qt 6 tooling to match QGIS 4.x (mixing Qt5 and Qt6 packages in one
          # shell is rejected by the nixpkgs Qt hook). Designer/linguist come
          # from qttools; quickcontrols2 now lives inside qtdeclarative.
          pkgs.kdePackages.qtbase
          pkgs.kdePackages.qtdeclarative
          pkgs.kdePackages.qtlocation
          pkgs.kdePackages.qtpositioning
          pkgs.kdePackages.qtsvg
          pkgs.kdePackages.qttools
          pkgs.rpl
          pkgs.shellcheck
          pkgs.shfmt
          pkgs.stylua
          pkgs.tailspin
          pkgs.vscode
          pkgs.yamlfmt
          pkgs.yamllint
          postgresWithPostGIS
          pkgs.cspell
          (pkgs.python3.withPackages (ps: [
            # Add these for SQL linting/formatting:
            ps.black
            ps.click # needed by black
            ps.debugpy
            ps.flake8
            ps.flake8-docstrings # flake8 plugin: pulls in pydocstyle checks
            ps.gdal
            ps.h3
            ps.httpx
            ps.isort
            ps.jsonschema
            ps.matplotlib
            ps.mypy
            ps.numpy
            ps.odfpy
            ps.pandas
            ps.paver
            ps.pillow # SRS cover compositing and image sizing
            ps.pip
            ps.pre-commit-hooks # provides end-of-file-fixer, trailing-whitespace-fixer, check-yaml, check-json CLIs
            ps.psutil
            ps.pyarrow # GDAL/OGR bulk Arrow-batch writes (Layer.WriteArrowBatch/GetArrowStream)
            ps.pydocstyle
            ps.python-docx # SRS written directly into the Word template
            ps.pytest
            ps.pytest-qt
            ps.python
            ps.rich
            ps.setuptools
            ps.snakeviz # For visualising cprofiler outputs
            ps.sqlfmt
            ps.toml
            ps.typer
            ps.wheel
            # For autocompletion in vscode

            # This executes some shell code to initialize a venv in $venvDir before
            # dropping into the shell
            ps.venvShellHook
            ps.virtualenv
            # Those are dependencies that we would like to use from nixpkgs, which will
            # add them to PYTHONPATH and thus make them accessible from within the venv.
            # PyQt6 to match QGIS 4.x (Qt6).
            ps.pyqt6
            ps.pyqt6-webengine
          ]))

        ];
        shellHook = ''
            unset SOURCE_DATE_EPOCH

            # Recreate the .venv whenever the nix python it was built from
            # changes: a stale venv points into a store path that no longer
            # matches and pip then tries to write into the read-only store.
            PY_INTERP="$(command -v python3)"
            if [ -d ".venv" ] && [ "$(cat .venv/.nix-python 2>/dev/null)" != "$PY_INTERP" ]; then
              echo "Python toolchain changed — recreating .venv"
              rm -rf .venv
            fi

            # Create a virtual environment in .venv if it doesn't exist
             if [ ! -d ".venv" ]; then
              python -m venv .venv
              echo "$PY_INTERP" > .venv/.nix-python
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

            # Reinstall the git hook every shell entry: its shebang bakes in
            # nix store paths (bash, pre-commit) that go stale whenever the
            # pinned nixpkgs revision changes. Run `scripts/checks.sh` for a
            # full `--all-files` pass — that's too slow to run on every entry.
            pre-commit install --install-hooks > /dev/null

          # Add PyQt and QGIS to python path for neovim
          pythonWithPackages="${
            pkgs.python3.withPackages (ps: [
              ps.pyqt6-webengine
            ])
          }"
          export PYTHONPATH="$pythonWithPackages/lib/python*/site-packages:${qgisWithExtras}/share/qgis/python:$PYTHONPATH"

          # Banner + full lifecycle command reference (logic lives in the
          # dotfile, not inline here — see scripts/dev-help.sh).
          bash "$PWD/scripts/dev-help.sh"
        '';
      };
    };
}
