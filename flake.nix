{
  description = "Python development environment with Nix flakes";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        python = pkgs.python312;  # Or pkgs.python310, etc.

        pythonPackages = python.withPackages (ps: with ps; [
          requests
          more-itertools
          tqdm
          # Add more as needed
        ]);
      in {
        devShells.default = pkgs.mkShell {
          packages = [ pythonPackages ];

          shellHook = ''
            echo "🐍 Python development environment activated"
            echo "Python: $(which python)"
            python --version
          '';
        };
      });
}
