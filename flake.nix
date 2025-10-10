{
  description = "A Python Dev Shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:

    flake-utils.lib.eachDefaultSystem (
      system:

      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        commands = import ./commands.nix { inherit pkgs; };
      in
      {
        packages.${system} = {
          default = pkgs.writeShellScriptBin "run" ''
            nix develop -c -- codium .
          '';
        };

        devShells.default = pkgs.mkShell rec {
          name = "PythonDevShell";
          buildInputs = with pkgs; [
            commands
            (pkgs.python3.withPackages (python-pkgs: [
              python-pkgs.pyserial
              python-pkgs.pyqt5
              python-pkgs.requests
              python-pkgs.tkinter
              python-pkgs.pyinstaller
            ]))
            qt5.qtbase
            qt5.qtwayland
            wine
            bashInteractive
            (vscode-with-extensions.override {
              vscode = pkgs.vscode;
              vscodeExtensions =
                with pkgs.vscode-extensions;
                [
                  jnoortheen.nix-ide
                  mhutchie.git-graph
                  vscode-extensions.eamodio.gitlens
                  github.copilot
                  github.copilot-chat
                  ms-python.python
                  ms-toolsai.jupyter
                  ms-python.debugpy
                ]
                ++ pkgs.vscode-utils.extensionsFromVscodeMarketplace [
                  # {
                  #   name = "csharp";
                  #   publisher = "ms-dotnettools";
                  #   version = "2.30.28";
                  #   sha256 = "sha256-+loUatN8evbHWTTVEmuo9Ups6Z1AfqzCyTWWxAY2DY8=";
                  # }
                ];
            })
          ];

          shellHook = ''
            ${commands.set.welcome}
          '';
        };
      }

    );
}
